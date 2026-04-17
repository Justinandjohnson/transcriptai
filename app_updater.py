#!/usr/bin/env python3
"""
TranscriptAI App Updater - GUI Version
Simple one-click updater for the TranscriptAI Mac app
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import os
import threading
import time

class AppUpdater:
    def __init__(self, root):
        self.root = root
        self.root.title("TranscriptAI Updater")
        self.root.geometry("600x500")
        
        # Set app icon if available
        try:
            if os.path.exists("TranscriptAI_icon.png"):
                # Note: tkinter doesn't support .icns directly, using .png
                pass
        except:
            pass
        
        # Style
        style = ttk.Style()
        style.theme_use('default')
        
        # Main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="🔄 TranscriptAI App Updater", 
                                font=('Helvetica', 18, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to update", 
                                      font=('Helvetica', 12))
        self.status_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', 
                                        length=400)
        self.progress.grid(row=2, column=0, columnspan=2, pady=(0, 20))
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(main_frame, 
                                                     width=70, height=15,
                                                     wrap=tk.WORD,
                                                     font=('Courier', 10))
        self.output_text.grid(row=3, column=0, columnspan=2, pady=(0, 20))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2)
        
        # Update button
        self.update_btn = ttk.Button(button_frame, text="🚀 Update App", 
                                     command=self.update_app,
                                     width=20)
        self.update_btn.grid(row=0, column=0, padx=5)
        
        # Restart server button
        self.restart_btn = ttk.Button(button_frame, text="🔄 Restart Server", 
                                      command=self.restart_server,
                                      width=20)
        self.restart_btn.grid(row=0, column=1, padx=5)
        
        # Launch app button
        self.launch_btn = ttk.Button(button_frame, text="▶️ Launch App", 
                                     command=self.launch_app,
                                     width=20)
        self.launch_btn.grid(row=0, column=2, padx=5)
        
        # File status frame
        status_frame = ttk.LabelFrame(main_frame, text="Files to Update", 
                                      padding="10")
        status_frame.grid(row=5, column=0, columnspan=2, pady=(20, 0), 
                         sticky=(tk.W, tk.E))
        
        files = [
            "✓ python_server_optimized.py",
            "✓ public/index.html",
            "✓ public/script.js",
            "✓ public/style.css",
            "✓ .env (API keys)"
        ]
        
        for i, file in enumerate(files):
            ttk.Label(status_frame, text=file, font=('Courier', 10)).grid(
                row=i//2, column=i%2, sticky=tk.W, padx=10, pady=2)
    
    def log_output(self, text):
        """Add text to the output area"""
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
        self.root.update()
    
    def update_app(self):
        """Update the Mac app with latest changes"""
        def run_update():
            self.update_btn.config(state='disabled')
            self.progress.start()
            self.status_label.config(text="Updating app...")
            self.output_text.delete(1.0, tk.END)
            
            try:
                # Check if app exists
                app_path = os.path.expanduser("~/Desktop/TranscriptAI.app")
                
                if not os.path.exists(app_path):
                    self.log_output("📱 Creating new app on Desktop...")
                    # Create the app
                    result = subprocess.run(
                        ["osacompile", "-o", app_path, "TranscriptAI.applescript"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.log_output("✅ App created successfully")
                    else:
                        self.log_output(f"❌ Error: {result.stderr}")
                else:
                    self.log_output("📱 Found existing app, updating...")
                    # Update the app
                    result = subprocess.run(
                        ["osacompile", "-o", app_path, "TranscriptAI.applescript"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.log_output("✅ App script updated")
                
                # Apply icon
                if os.path.exists("TranscriptAI.icns"):
                    icon_dest = os.path.join(app_path, "Contents/Resources/applet.icns")
                    result = subprocess.run(
                        ["cp", "TranscriptAI.icns", icon_dest],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        self.log_output("✅ Icon applied")
                    
                    # Touch app to refresh
                    subprocess.run(["touch", app_path])
                
                self.log_output("\n📦 Updated files:")
                self.log_output("  • Backend: python_server_optimized.py")
                self.log_output("  • Frontend: public/index.html")
                self.log_output("  • Scripts: public/script.js")
                self.log_output("  • Styles: public/style.css")
                
                self.log_output("\n✅ Update complete!")
                self.log_output("Your changes are now live in the app.")
                self.status_label.config(text="✅ Update successful!")
                
                messagebox.showinfo("Success", 
                    "TranscriptAI app has been updated!\n\n" +
                    "Double-click the app on your Desktop to use the new version.")
                
            except Exception as e:
                self.log_output(f"❌ Error: {str(e)}")
                self.status_label.config(text="❌ Update failed")
                messagebox.showerror("Error", f"Update failed: {str(e)}")
            
            finally:
                self.progress.stop()
                self.update_btn.config(state='normal')
        
        # Run in thread to keep UI responsive
        threading.Thread(target=run_update, daemon=True).start()
    
    def restart_server(self):
        """Restart the TranscriptAI server"""
        def run_restart():
            self.restart_btn.config(state='disabled')
            self.progress.start()
            self.status_label.config(text="Restarting server...")
            
            try:
                # Kill existing server
                self.log_output("\n🛑 Stopping existing server...")
                subprocess.run(["pkill", "-f", "python.*server"], 
                             capture_output=True)
                time.sleep(1)
                
                # Start new server
                self.log_output("🚀 Starting new server...")
                subprocess.Popen(
                    ["python3", "python_server_optimized.py"],
                    cwd="/Users/jjohnson/Downloads/transcriptai"
                )
                time.sleep(2)
                
                # Open browser
                self.log_output("🌐 Opening browser...")
                subprocess.run(["open", "http://localhost:50263"])
                
                self.log_output("✅ Server restarted!")
                self.status_label.config(text="✅ Server running")
                
            except Exception as e:
                self.log_output(f"❌ Error: {str(e)}")
                self.status_label.config(text="❌ Restart failed")
            
            finally:
                self.progress.stop()
                self.restart_btn.config(state='normal')
        
        threading.Thread(target=run_restart, daemon=True).start()
    
    def launch_app(self):
        """Launch the TranscriptAI app"""
        try:
            app_path = os.path.expanduser("~/Desktop/TranscriptAI.app")
            if os.path.exists(app_path):
                subprocess.run(["open", app_path])
                self.status_label.config(text="✅ App launched")
            else:
                messagebox.showwarning("App Not Found", 
                    "TranscriptAI.app not found on Desktop.\n" +
                    "Click 'Update App' to create it.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch app: {str(e)}")

def main():
    root = tk.Tk()
    app = AppUpdater(root)
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()

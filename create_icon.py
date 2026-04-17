#!/usr/bin/env python3
"""
Create a custom icon for TranscriptAI app
"""

import os
from PIL import Image, ImageDraw, ImageFont
import subprocess

def create_icon():
    # Create a 1024x1024 image for the icon
    size = 1024
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw background gradient circle
    center = size // 2
    radius = size // 2 - 50
    
    # Create gradient effect with multiple circles
    for i in range(radius, 0, -5):
        alpha = int(255 * (i / radius))
        color = (102, 126, 234, alpha)  # Purple-blue gradient
        draw.ellipse([center - i, center - i, center + i, center + i], 
                     fill=color, outline=None)
    
    # Draw inner circle with darker color
    inner_radius = radius - 100
    draw.ellipse([center - inner_radius, center - inner_radius, 
                  center + inner_radius, center + inner_radius],
                 fill=(45, 45, 68, 255), outline=(102, 126, 234, 255), width=10)
    
    # Draw microphone symbol
    mic_width = 120
    mic_height = 200
    mic_x = center - mic_width // 2
    mic_y = center - mic_height // 2 - 50
    
    # Microphone body
    draw.rounded_rectangle([mic_x, mic_y, mic_x + mic_width, mic_y + mic_height],
                           radius=60, fill=(255, 79, 163, 255), outline=(255, 255, 255, 255), width=8)
    
    # Microphone stand
    stand_width = 200
    stand_x = center - stand_width // 2
    stand_y = mic_y + mic_height - 20
    
    # Stand arc
    draw.arc([stand_x, stand_y, stand_x + stand_width, stand_y + 150],
             start=0, end=180, fill=(255, 255, 255, 255), width=12)
    
    # Stand base
    base_y = stand_y + 150
    draw.line([center, base_y - 75, center, base_y + 20], 
              fill=(255, 255, 255, 255), width=12)
    draw.line([center - 60, base_y + 20, center + 60, base_y + 20],
              fill=(255, 255, 255, 255), width=12)
    
    # Add "AI" text
    try:
        # Try to use a system font
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 180)
    except:
        font = ImageFont.load_default()
    
    text = "AI"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = center - text_width // 2
    text_y = center + 180
    
    # Draw text with glow effect
    for offset in range(5, 0, -1):
        alpha = 50 * (6 - offset)
        draw.text((text_x - offset, text_y - offset), text, 
                 fill=(102, 126, 234, alpha), font=font)
        draw.text((text_x + offset, text_y + offset), text, 
                 fill=(102, 126, 234, alpha), font=font)
    
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
    
    # Save the icon
    icon_path = "TranscriptAI_icon.png"
    img.save(icon_path, "PNG")
    print(f"Icon created: {icon_path}")
    
    # Create .icns file for macOS
    try:
        # Create iconset directory
        iconset_dir = "TranscriptAI.iconset"
        os.makedirs(iconset_dir, exist_ok=True)
        
        # Generate different sizes
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        for size in sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(f"{iconset_dir}/icon_{size}x{size}.png")
            
            # Also create @2x versions for Retina displays
            if size <= 512:
                resized_2x = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
                resized_2x.save(f"{iconset_dir}/icon_{size}x{size}@2x.png")
        
        # Convert to .icns
        subprocess.run(["iconutil", "-c", "icns", iconset_dir], check=True)
        print("Created TranscriptAI.icns")
        
        # Clean up iconset directory
        subprocess.run(["rm", "-rf", iconset_dir], check=True)
        
        return True
    except Exception as e:
        print(f"Could not create .icns file: {e}")
        return False

if __name__ == "__main__":
    # Check if Pillow is installed
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Installing Pillow...")
        subprocess.run(["pip3", "install", "Pillow"], check=True)
        from PIL import Image, ImageDraw, ImageFont
    
    create_icon()

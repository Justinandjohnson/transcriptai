# TranscriptAI Mac App

## 🎙️ About
TranscriptAI is a powerful audio transcription app that converts audio files to text with AI-powered analysis, providing comprehensive notes, summaries, and action items.

## 🚀 Installation & Setup

### Prerequisites
- macOS
- Python 3 installed
- OpenAI API key (set in `.env` file)

### Quick Start
1. **The Mac App is already on your Desktop!**
   - Look for the **TranscriptAI** app with a custom microphone icon
   - Double-click to launch

2. **What happens when you launch:**
   - The app will start the transcription server
   - Terminal window will open (minimizes automatically)
   - Your browser will open to the TranscriptAI interface
   - You'll see a notification when it's ready

## 📱 How to Use

1. **Launch the App:**
   - Double-click the TranscriptAI app on your Desktop
   - Wait for the browser to open automatically

2. **Upload Audio:**
   - Drag and drop audio files onto the upload zone
   - Or click to browse and select files
   - Supported formats: MP4, M4A, WAV, MP3

3. **Get Results:**
   - **Transcription**: Full text of the audio
   - **Smart Notes**: Key points, decisions, and important facts
   - **Summary**: Comprehensive overview of the conversation
   - **Action Items**: All tasks with WHO and WHEN details

4. **Stop the App:**
   - Close the Terminal window
   - Or press Ctrl+C in the Terminal

## 🎯 Features

- **Ultra-Fast Processing**: Parallel chunk processing for 3-4x speed improvement
- **Combined Analysis**: Transcription and GPT analysis in one request
- **Smart Recognition**: Identifies all important conversation points
- **Detailed Action Items**: Captures tasks with assignees and deadlines
- **History Tracking**: Saves all transcriptions for future reference
- **Beautiful UI**: Modern, animated interface with progress tracking

## 🛠️ Technical Details

- **Backend**: Python with Flask, OpenAI Whisper API
- **Frontend**: HTML5, CSS3, JavaScript with animations
- **Processing**: Multi-threaded parallel chunk processing
- **Port**: 50263 (automatically configured)

## 📝 Alternative Launch Methods

### Command Line:
```bash
cd /Users/jjohnson/Downloads/transcriptai
python3 python_server_optimized.py
```
Then open http://localhost:50263 in your browser

### Using the .command file:
```bash
./start_transcription_app.command
```

## 🔄 Pushing Updates to the App

When you make changes to the code, you have **3 easy ways** to update the app:

### Method 1: GUI Updater (Easiest)
```bash
python3 app_updater.py
```
This opens a graphical interface where you can:
- Click "Update App" to push all changes
- Restart the server with new code
- Launch the app directly

### Method 2: Command Line Script
```bash
./update_app.sh
```
This script will:
- Update the app with your latest changes
- Reapply the custom icon
- Optionally restart the server

### Method 3: Manual Update
```bash
# Recompile the app
osacompile -o ~/Desktop/TranscriptAI.app TranscriptAI.applescript

# Reapply the icon
cp TranscriptAI.icns ~/Desktop/TranscriptAI.app/Contents/Resources/applet.icns
touch ~/Desktop/TranscriptAI.app
```

### What Gets Updated
When you push updates, these files are automatically included:
- `python_server_optimized.py` - Backend changes
- `public/index.html` - UI structure
- `public/script.js` - Frontend logic
- `public/style.css` - Styling changes
- `.env` - Configuration changes

**Note:** After making changes to any of these files, just run one of the update methods above, and your app will use the new code next time you launch it!

## 🔧 Troubleshooting

1. **App won't open:**
   - Right-click the app and select "Open" (first time only)
   - Go to System Preferences > Security & Privacy if blocked

2. **Server won't start:**
   - Check if Python 3 is installed: `python3 --version`
   - Ensure `.env` file has your OpenAI API key
   - Check if port 50263 is available

3. **Missing dependencies:**
   The app will automatically install required packages:
   - flask, flask-cors
   - openai
   - ffmpeg-python
   - pydub
   - python-dotenv

4. **Updates not applying:**
   - Make sure to close the app/server before updating
   - Use the GUI updater for automatic server restart
   - Check the output for any error messages

## 📄 License
Private use only

## 👨‍💻 Developer
Created with AI assistance for fast, accurate audio transcription and analysis.

---

**Enjoy using TranscriptAI!** 🎉

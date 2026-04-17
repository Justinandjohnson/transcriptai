#!/bin/bash

# TranscriptAI Launcher Script
# This script starts the transcription server and opens the browser

echo "🎙️ Starting TranscriptAI..."
echo "================================"

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    read -p "Press any key to exit..."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import flask" 2>/dev/null || {
    echo "Installing Flask..."
    pip3 install flask flask-cors
}
python3 -c "import openai" 2>/dev/null || {
    echo "Installing OpenAI..."
    pip3 install openai
}
python3 -c "import ffmpeg" 2>/dev/null || {
    echo "Installing ffmpeg-python..."
    pip3 install ffmpeg-python
}
python3 -c "import pydub" 2>/dev/null || {
    echo "Installing pydub..."
    pip3 install pydub
}
python3 -c "import dotenv" 2>/dev/null || {
    echo "Installing python-dotenv..."
    pip3 install python-dotenv
}

# Kill any existing Python servers
echo "🔄 Stopping any existing servers..."
pkill -f "python.*server" 2>/dev/null

# Start the server
echo "🚀 Starting transcription server..."
python3 python_server_optimized.py &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Open the browser
echo "🌐 Opening browser..."
open http://localhost:50263

echo ""
echo "✅ TranscriptAI is running!"
echo "================================"
echo "📍 Access at: http://localhost:50263"
echo ""
echo "To stop the server, close this window or press Ctrl+C"
echo ""

# Keep the script running and handle shutdown
trap "echo ''; echo '🛑 Shutting down server...'; kill $SERVER_PID 2>/dev/null; exit" INT TERM

# Wait for the server process
wait $SERVER_PID

#!/bin/bash

# TranscriptAI App Update Script
# This script updates the Mac app with any changes you've made to the code

echo "🔄 TranscriptAI App Updater"
echo "============================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if the app exists on Desktop
if [ ! -d ~/Desktop/TranscriptAI.app ]; then
    echo -e "${YELLOW}⚠️  TranscriptAI.app not found on Desktop${NC}"
    echo "Creating new app..."
    osacompile -o ~/Desktop/TranscriptAI.app TranscriptAI.applescript
    
    # Apply icon if it exists
    if [ -f TranscriptAI.icns ]; then
        cp TranscriptAI.icns ~/Desktop/TranscriptAI.app/Contents/Resources/applet.icns
        touch ~/Desktop/TranscriptAI.app
        echo -e "${GREEN}✅ Created new app with icon${NC}"
    else
        echo -e "${GREEN}✅ Created new app${NC}"
    fi
else
    echo -e "${BLUE}📱 Found existing TranscriptAI.app${NC}"
fi

# Update the AppleScript if changed
echo ""
echo "Updating app script..."
osacompile -o ~/Desktop/TranscriptAI.app TranscriptAI.applescript 2>/dev/null

# Reapply the custom icon
if [ -f TranscriptAI.icns ]; then
    cp TranscriptAI.icns ~/Desktop/TranscriptAI.app/Contents/Resources/applet.icns
    echo -e "${GREEN}✅ Updated app icon${NC}"
fi

# Touch the app to refresh Finder
touch ~/Desktop/TranscriptAI.app

# Show what files are included in the update
echo ""
echo -e "${BLUE}📦 App will use these files:${NC}"
echo "  • python_server_optimized.py (backend)"
echo "  • public/index.html (frontend)"
echo "  • public/script.js (frontend logic)"
echo "  • public/style.css (styling)"
echo "  • .env (API keys)"

# Check if server is running and offer to restart
if pgrep -f "python.*server" > /dev/null; then
    echo ""
    echo -e "${YELLOW}⚠️  Server is currently running${NC}"
    read -p "Do you want to restart the server now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping current server..."
        pkill -f "python.*server"
        sleep 1
        echo "Starting updated server..."
        cd /Users/jjohnson/Downloads/transcriptai
        python3 python_server_optimized.py &
        sleep 2
        open http://localhost:50263
        echo -e "${GREEN}✅ Server restarted with updates${NC}"
    fi
else
    echo ""
    echo -e "${GREEN}✅ Updates will be applied next time you launch the app${NC}"
fi

echo ""
echo "================================"
echo -e "${GREEN}✅ App update complete!${NC}"
echo ""
echo "Your changes are now live in the TranscriptAI app."
echo "Just double-click the app on your Desktop to use the updated version."
echo ""

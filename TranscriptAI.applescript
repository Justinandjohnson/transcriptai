-- TranscriptAI Mac Application
-- This script creates a clickable Mac app to launch the transcription service

on run
    set appPath to POSIX path of (path to me)
    set appDir to do shell script "dirname " & quoted form of appPath
    set projectDir to "/Users/jjohnson/Downloads/transcriptai"
    
    -- Show starting notification
    display notification "Starting TranscriptAI server..." with title "TranscriptAI" subtitle "Please wait..."
    
    -- Kill any existing Python servers
    try
        do shell script "pkill -f 'python.*server' 2>/dev/null"
    end try
    
    -- Start the server in Terminal
    tell application "Terminal"
        -- Create new window
        do script "cd " & quoted form of projectDir & " && echo '🎙️ TranscriptAI Starting...' && echo '================================' && python3 python_server_optimized.py"
        
        -- Set window properties
        set current settings of first window to settings set "Pro"
        set the custom title of first window to "TranscriptAI Server"
        
        -- Minimize Terminal window after 2 seconds
        delay 2
        set miniaturized of first window to true
    end tell
    
    -- Wait for server to start
    delay 2
    
    -- Open browser
    do shell script "open http://localhost:50263"
    
    -- Show success notification
    display notification "TranscriptAI is ready!" with title "TranscriptAI" subtitle "Access at http://localhost:50263" sound name "Glass"
    
end run

on quit
    -- Clean shutdown when app is quit
    try
        do shell script "pkill -f 'python.*server' 2>/dev/null"
        display notification "TranscriptAI stopped" with title "TranscriptAI"
    end try
    continue quit
end quit

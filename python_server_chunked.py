#!/usr/bin/env python3
import os
import sys
import tempfile
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import ffmpeg
from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment
import threading
import queue

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder="public", static_url_path="")
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

client = OpenAI(api_key=OPENAI_API_KEY)

# Serve index.html and static files
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    try:
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            index_path = os.path.join(app.static_folder, "index.html")
            if not os.path.exists(index_path):
                return "Frontend index.html not found in 'public' folder. Please ensure your frontend files are in the /public directory.", 404
            return send_from_directory(app.static_folder, "index.html")
    except Exception as e:
        return f"Error loading frontend: {str(e)}", 500

def split_audio_file(file_path, chunk_duration_ms=600000):  # 10 minutes chunks
    """Split audio file into chunks of specified duration"""
    try:
        # Load the audio file
        audio = AudioSegment.from_file(file_path)
        
        # Calculate number of chunks
        total_duration = len(audio)
        chunks = []
        
        for i in range(0, total_duration, chunk_duration_ms):
            chunk = audio[i:i + chunk_duration_ms]
            
            # Save chunk to temporary file
            chunk_path = f"{file_path}_chunk_{i//chunk_duration_ms}.mp3"
            chunk.export(chunk_path, format="mp3", bitrate="128k", parameters=["-ar", "16000"])
            chunks.append(chunk_path)
            
        return chunks
    except Exception as e:
        print(f"Error splitting audio: {str(e)}")
        return None

def transcribe_chunk(chunk_path):
    """Transcribe a single audio chunk"""
    try:
        with open(chunk_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en",
                temperature=0,
                response_format="text"
            )
        return transcription if isinstance(transcription, str) else transcription
    except Exception as e:
        print(f"Error transcribing chunk: {str(e)}")
        return ""

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Save uploaded file to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_in:
        file.save(temp_in.name)
        temp_in_path = temp_in.name

    # Check file size
    file_size_mb = os.path.getsize(temp_in_path) / (1024 * 1024)
    print(f"File size: {file_size_mb:.2f} MB")

    # Convert to mp3 for compatibility
    temp_out_path = temp_in_path + "_converted.mp3"
    try:
        # More aggressive compression for large files
        if file_size_mb > 20:
            # For files > 20MB, use more aggressive compression
            ffmpeg.input(temp_in_path).output(
                temp_out_path, 
                format="mp3",
                acodec="libmp3lame",
                audio_bitrate="64k",  # Lower bitrate for very large files
                ar="16000",  # Lower sample rate
                ac=1  # Convert to mono
            ).run(quiet=True, overwrite_output=True)
        else:
            # Standard compression for smaller files
            ffmpeg.input(temp_in_path).output(
                temp_out_path, 
                format="mp3",
                acodec="libmp3lame",
                audio_bitrate="128k",
                ar="16000"
            ).run(quiet=True, overwrite_output=True)
    except ffmpeg.Error as e:
        cleanup_files([temp_in_path])
        return jsonify({"error": f"FFmpeg error: {str(e)}"}), 500

    # Check converted file size
    converted_size_mb = os.path.getsize(temp_out_path) / (1024 * 1024)
    print(f"Converted file size: {converted_size_mb:.2f} MB")

    transcription_text = ""
    
    # If file is still > 24MB after conversion, split it
    if converted_size_mb > 24:
        print("File too large, splitting into chunks...")
        chunks = split_audio_file(temp_out_path)
        
        if chunks:
            # Transcribe each chunk
            transcriptions = []
            for i, chunk_path in enumerate(chunks):
                print(f"Transcribing chunk {i+1}/{len(chunks)}...")
                chunk_text = transcribe_chunk(chunk_path)
                if chunk_text:
                    transcriptions.append(chunk_text)
                # Clean up chunk file
                cleanup_files([chunk_path])
            
            transcription_text = " ".join(transcriptions)
        else:
            cleanup_files([temp_in_path, temp_out_path])
            return jsonify({"error": "Failed to split audio file"}), 500
    else:
        # File is small enough, transcribe directly
        try:
            print("Transcribing audio file...")
            with open(temp_out_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    temperature=0,
                    response_format="text"
                )
            transcription_text = transcription if isinstance(transcription, str) else transcription
        except Exception as e:
            cleanup_files([temp_in_path, temp_out_path])
            return jsonify({"error": f"OpenAI API error: {str(e)}"}), 500

    # Cleanup
    cleanup_files([temp_in_path, temp_out_path])

    if not transcription_text:
        return jsonify({"error": "Transcription failed"}), 500

    # Return transcription
    return jsonify({"text": transcription_text})

@app.route("/generate-sections", methods=["POST"])
def generate_sections():
    try:
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400
        
        transcription_text = data["text"]
        
        # Use GPT-4 for better analysis with a much more detailed prompt
        prompt = f"""You are an expert analyst tasked with extracting comprehensive insights from a transcription. Analyze the following transcription thoroughly and provide:

1. **DETAILED NOTES** (array of strings): Extract ALL important points, insights, and key information. Include:
   - Main topics discussed with specific details
   - Important facts, figures, dates, or statistics mentioned
   - Key decisions or conclusions reached
   - Notable quotes or statements
   - Technical details or specifications discussed
   - Problems or challenges identified
   - Solutions or approaches proposed
   - Relationships between different topics
   - Context and background information provided
   - Any assumptions or hypotheses mentioned
   - Important names, places, or organizations referenced

2. **COMPREHENSIVE SUMMARY** (single string): Provide an in-depth summary that:
   - Captures the overall purpose and context of the conversation
   - Explains the main themes and how they connect
   - Highlights the most critical information
   - Describes the flow and progression of ideas
   - Notes any consensus or disagreements
   - Identifies the key takeaways
   - Provides context for why this discussion matters
   - Should be at least 3-5 sentences but can be longer if needed

3. **ACTIONABLE ITEMS** (array of strings): Identify ALL action items including:
   - Explicit tasks that need to be completed
   - Follow-up items mentioned
   - Decisions that need to be made
   - Information that needs to be gathered or researched
   - People who need to be contacted or consulted
   - Documents that need to be created or reviewed
   - Meetings that need to be scheduled
   - Deadlines or timeframes mentioned
   - Implicit next steps based on the discussion
   - Questions that need to be answered
   - Issues that need to be resolved
   - Processes that need to be implemented or changed
   - Each action item should be specific and include WHO should do it (if mentioned) and WHEN (if a timeframe was discussed)

Be thorough and extract as much valuable information as possible. Don't summarize too much - provide detailed, actionable insights. If the transcription mentions something even potentially important, include it.

Transcription:
{transcription_text}

Format your response as JSON with three keys: "notes" (array of detailed strings), "summary" (comprehensive string), and "action" (array of specific action items)."""

        response = client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4 for better analysis
            messages=[
                {"role": "system", "content": "You are an expert analyst specializing in extracting comprehensive insights from conversations and meetings. You excel at identifying both explicit and implicit information, understanding context, and recognizing actionable items. Always provide thorough, detailed analysis and respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more focused analysis
            max_tokens=4000,  # Increased token limit for more detailed responses
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = response.choices[0].message.content
        import json
        try:
            sections = json.loads(result)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            sections = {
                "notes": ["Unable to parse detailed notes - please review transcription manually"],
                "summary": "Summary generation failed - transcription may need manual review",
                "action": ["Review transcription manually for action items"]
            }
        
        # Ensure all required keys are present with correct types
        if "notes" not in sections or not isinstance(sections["notes"], list):
            sections["notes"] = ["No specific notes identified"]
        if "summary" not in sections or not isinstance(sections["summary"], str):
            sections["summary"] = "No summary available"
        if "action" not in sections or not isinstance(sections["action"], list):
            sections["action"] = ["No action items identified"]
        
        # Additional processing to ensure quality
        # Remove any empty strings from arrays
        sections["notes"] = [note for note in sections["notes"] if note and note.strip()]
        sections["action"] = [action for action in sections["action"] if action and action.strip()]
        
        # If arrays are empty after filtering, add helpful defaults
        if not sections["notes"]:
            sections["notes"] = ["No significant notes extracted from this transcription"]
        if not sections["action"]:
            sections["action"] = ["No specific action items identified in this transcription"]
        if not sections["summary"] or sections["summary"].strip() == "":
            sections["summary"] = "Unable to generate summary from the provided transcription"
            
        return jsonify(sections)
        
    except Exception as e:
        return jsonify({"error": f"Error generating sections: {str(e)}"}), 500

def cleanup_files(paths):
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass

if __name__ == "__main__":
    import socket

    def get_free_port(default_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", default_port))
                return default_port
            except OSError:
                # Bind to any free port
                s.bind(("", 0))
                return s.getsockname()[1]

    # Use the same port as the current server
    env_port = int(os.getenv("PORT", 50263))
    port = get_free_port(env_port)
    
    print(f"Starting improved Python transcription server on port {port}...")
    print("Features:")
    print("- Automatic audio chunking for files > 24MB")
    print("- Better compression for large files")
    print("- Improved error handling")
    
    app.run(host="0.0.0.0", port=port, debug=False)

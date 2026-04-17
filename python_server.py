#!/usr/bin/env python3
import os
import sys
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import ffmpeg
from openai import OpenAI
from dotenv import load_dotenv

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

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Save uploaded file to temp
    with tempfile.NamedTemporaryFile(delete=False) as temp_in:
        file.save(temp_in.name)
        temp_in_path = temp_in.name

    # Convert to mp3 for compatibility with faster settings
    temp_out_path = temp_in_path + ".mp3"
    try:
        ffmpeg.input(temp_in_path).output(
            temp_out_path, 
            format="mp3",
            acodec="libmp3lame",
            audio_bitrate="128k",  # Lower bitrate for faster conversion
            ar="16000"  # Lower sample rate for faster processing
        ).run(quiet=True, overwrite_output=True)
    except ffmpeg.Error as e:
        cleanup_files([temp_in_path])
        return jsonify({"error": f"FFmpeg error: {str(e)}"}), 500

    # Send to OpenAI API with optimized model
    try:
        with open(temp_out_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",  # Use standard whisper model for better compatibility
                file=audio_file,
                language="en",
                temperature=0,
                response_format="text"  # Faster response format
            )
    except Exception as e:
        cleanup_files([temp_in_path, temp_out_path])
        return jsonify({"error": f"OpenAI API error: {str(e)}"}), 500

    # Cleanup
    cleanup_files([temp_in_path, temp_out_path])

    # Return transcription immediately
    result_text = transcription if isinstance(transcription, str) else transcription.text
    return jsonify({"text": result_text})

@app.route("/generate-sections", methods=["POST"])
def generate_sections():
    try:
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400
        
        transcription_text = data["text"]
        
        # Use GPT to generate the three sections
        prompt = f"""Based on the following transcription, please generate:
1. Key notes and important points
2. A concise summary
3. Action items or next steps

Transcription:
{transcription_text}

Please format your response as JSON with three keys: "notes", "summary", and "action"."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using a faster model for quick responses
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes transcriptions and extracts key information. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
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
                "notes": "Key points from the transcription",
                "summary": "Summary of the transcription",
                "action": "Follow up on discussed items"
            }
        
        # Ensure all required keys are present
        if "notes" not in sections:
            sections["notes"] = "No specific notes identified"
        if "summary" not in sections:
            sections["summary"] = "No summary available"
        if "action" not in sections:
            sections["action"] = "No action items identified"
            
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


    # Force Flask to bind to port 8003 for frontend compatibility
    env_port = int(os.getenv("PORT", 8003))
    port = get_free_port(env_port)
    if port != env_port:
        print(f"Warning: Port {env_port} in use, using {port} instead.")
    else:
        print(f"Using fixed port {port} for frontend/backend integration.")

    # If a different port is used, update the JS frontend to match
    index_js_path = os.path.join(app.static_folder, "script.js")
    if os.path.exists(index_js_path):
        try:
            with open(index_js_path, "r+", encoding="utf-8") as f:
                js_content = f.read()
                import re
                new_content = re.sub(
                    r'(const\s+backendUrl\s*=\s*")[^"]+(")',
                    rf'\1http://localhost:{port}/transcribe\2',
                    js_content
                )
                if new_content != js_content:
                    f.seek(0)
                    f.write(new_content)
                    f.truncate()
                    print(f"Updated frontend backendUrl to use port {port}")
        except Exception as e:
            print(f"Failed to update frontend backendUrl: {e}")

    print(f"Starting Python transcription server on port {port}...")
    # Ensure we allow serving index.html and static assets
    # Avoid duplicate route definition — already defined above

    app.run(host="0.0.0.0", port=port)

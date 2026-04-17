#!/usr/bin/env python3
import base64
import os
import shutil
import tempfile
import concurrent.futures
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import ffmpeg
from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment
import json

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder="public", static_url_path="")
CORS(app)

AI_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

USE_OPENROUTER = bool(os.getenv("OPENROUTER_API_KEY"))
TRANSCRIPTION_MODEL = os.getenv(
    "TRANSCRIPTION_MODEL",
    "openai/gpt-audio-mini" if USE_OPENROUTER else "whisper-1",
)
ANALYSIS_MODEL = os.getenv(
    "ANALYSIS_MODEL",
    "openai/gpt-4.1-mini" if USE_OPENROUTER else "gpt-4o-mini",
)


def get_client():
    if not AI_API_KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY or OPENAI_API_KEY environment variable")

    client_kwargs = {"api_key": AI_API_KEY}
    if USE_OPENROUTER:
        client_kwargs["base_url"] = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        client_kwargs["default_headers"] = {
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://transcriptai.local"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "TranscriptAI"),
        }

    return OpenAI(**client_kwargs)

# Resolve an ffmpeg binary that works on local machines and Render.
def resolve_ffmpeg_binary():
    candidates = [os.getenv("FFMPEG_BINARY"), shutil.which("ffmpeg")]

    try:
        import imageio_ffmpeg

        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate

    return "ffmpeg"


FFMPEG_BINARY = resolve_ffmpeg_binary()
AudioSegment.converter = FFMPEG_BINARY
AudioSegment.ffmpeg = FFMPEG_BINARY

# Thread pool for parallel processing
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def detect_audio_format(file_path):
    extension = os.path.splitext(file_path)[1].lower().lstrip(".")
    format_map = {
        "mp3": "mp3",
        "wav": "wav",
        "aac": "aac",
        "ogg": "ogg",
        "flac": "flac",
        "m4a": "m4a",
        "aiff": "aiff",
    }
    return format_map.get(extension, "mp3")


def extract_message_text(message):
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()

    parts = []
    for item in content or []:
        if hasattr(item, "text") and item.text:
            parts.append(item.text)
        elif isinstance(item, dict) and item.get("text"):
            parts.append(item["text"])

    return "\n".join(part.strip() for part in parts if part and part.strip()).strip()


def transcribe_audio_with_provider(file_path):
    if not USE_OPENROUTER:
        client = get_client()
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                file=audio_file,
                language="en",
                temperature=0,
                response_format="text",
            )
        return transcription if isinstance(transcription, str) else transcription

    with open(file_path, "rb") as audio_file:
        audio_b64 = base64.b64encode(audio_file.read()).decode("utf-8")

    client = get_client()
    response = client.chat.completions.create(
        model=TRANSCRIPTION_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Transcribe the provided audio accurately. Return only the transcript text with no extra commentary.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please transcribe this audio verbatim."},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_b64,
                            "format": detect_audio_format(file_path),
                        },
                    },
                ],
            },
        ],
        temperature=0,
    )
    return extract_message_text(response.choices[0].message)

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

def split_audio_file_parallel(file_path, chunk_duration_ms=600000):  # 10 minutes chunks
    """Split audio file into chunks with overlap to prevent text loss"""
    try:
        # Load the audio file
        audio = AudioSegment.from_file(file_path)
        
        # Calculate number of chunks with overlap
        total_duration = len(audio)
        overlap_ms = 2000  # 2 second overlap between chunks
        chunks = []
        chunk_info = []
        
        # Calculate chunk positions with overlap
        position = 0
        chunk_index = 0
        while position < total_duration:
            # Start position (with overlap from previous chunk)
            start = max(0, position - overlap_ms if position > 0 else 0)
            # End position
            end = min(position + chunk_duration_ms, total_duration)
            
            chunk_info.append({
                'index': chunk_index,
                'start': start,
                'end': end,
                'is_first': position == 0,
                'is_last': end >= total_duration
            })
            
            position += chunk_duration_ms
            chunk_index += 1
        
        def export_chunk(info):
            chunk = audio[info['start']:info['end']]
            chunk_path = f"{file_path}_chunk_{info['index']:03d}.mp3"
            chunk.export(chunk_path, format="mp3", bitrate="96k", parameters=["-ar", "16000", "-ac", "1"])
            return (info['index'], chunk_path, info)
        
        # Export chunks in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as chunk_executor:
            futures = [chunk_executor.submit(export_chunk, info) for info in chunk_info]
            
            # Collect results maintaining order
            results = []
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        
        # Sort by index to maintain order
        results.sort(key=lambda x: x[0])
        
        # Return paths and info for proper merging
        return [(r[1], r[2]) for r in results]
    except Exception as e:
        print(f"Error splitting audio: {str(e)}")
        return None

def transcribe_chunk(chunk_path):
    """Transcribe a single audio chunk"""
    try:
        return transcribe_audio_with_provider(chunk_path)
    except Exception as e:
        print(f"Error transcribing chunk: {str(e)}")
        return ""

def transcribe_chunks_parallel(chunks_with_info):
    """Transcribe multiple chunks in parallel and merge intelligently"""
    transcriptions = [None] * len(chunks_with_info)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as trans_executor:
        # Submit all transcription tasks
        future_to_index = {}
        for i, (chunk_path, chunk_info) in enumerate(chunks_with_info):
            future = trans_executor.submit(transcribe_chunk, chunk_path)
            future_to_index[future] = (i, chunk_info)
            print(f"Started transcribing chunk {i+1}/{len(chunks_with_info)}...")
        
        # Collect results in order
        for future in concurrent.futures.as_completed(future_to_index):
            index, chunk_info = future_to_index[future]
            result = future.result()
            transcriptions[index] = (result, chunk_info)
            print(f"Completed chunk {index+1}/{len(chunks_with_info)}")
    
    # Merge transcriptions intelligently to avoid duplicates from overlap
    merged_text = []
    for i, (text, info) in enumerate(transcriptions):
        if not text:
            continue
            
        if i == 0:
            # First chunk - use all text
            merged_text.append(text.strip())
        else:
            # For subsequent chunks, try to remove overlap
            # Look for common words at the boundary
            if merged_text and len(text) > 50:
                # Try to find overlap point
                last_words = merged_text[-1].split()[-10:] if merged_text else []
                first_words = text.split()[:20]
                
                # Find where the overlap might be
                overlap_found = False
                for j in range(min(10, len(last_words))):
                    for k in range(min(15, len(first_words) - 5)):
                        if last_words[j:] == first_words[k:k+len(last_words[j:])]:
                            # Found overlap, skip the overlapping part
                            words = text.split()
                            new_text = ' '.join(words[k+len(last_words[j:]):])
                            if new_text:
                                merged_text.append(new_text.strip())
                            overlap_found = True
                            break
                    if overlap_found:
                        break
                
                if not overlap_found:
                    # No clear overlap found, just append with a space
                    merged_text.append(text.strip())
            else:
                merged_text.append(text.strip())
    
    # Join all text with spaces
    final_text = " ".join(merged_text)
    
    # Clean up any double spaces or formatting issues
    final_text = " ".join(final_text.split())
    
    return final_text

@app.route("/transcribe-and-analyze", methods=["POST"])
def transcribe_and_analyze():
    """Combined endpoint that transcribes and analyzes in parallel"""
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

    # Convert to mp3 for compatibility (optimized settings)
    temp_out_path = temp_in_path + "_converted.mp3"
    try:
        # Optimized conversion for speed
        ffmpeg_params = {
            "format": "mp3",
            "acodec": "libmp3lame",
            "audio_bitrate": "96k" if file_size_mb > 15 else "128k",
            "ar": "16000",
            "ac": 1,
            "threads": 0  # Use all available CPU threads
        }
        
        ffmpeg.input(temp_in_path).output(
            temp_out_path, 
            **ffmpeg_params
        ).run(cmd=FFMPEG_BINARY, quiet=True, overwrite_output=True)
    except ffmpeg.Error as e:
        cleanup_files([temp_in_path])
        return jsonify({"error": f"FFmpeg error: {str(e)}"}), 500

    # Check converted file size
    converted_size_mb = os.path.getsize(temp_out_path) / (1024 * 1024)
    print(f"Converted file size: {converted_size_mb:.2f} MB")

    transcription_text = ""
    
    # If file is still > 24MB after conversion, split and process in parallel
    if converted_size_mb > 24:
        print(f"File too large ({converted_size_mb:.1f}MB), splitting into chunks...")
        chunks_with_info = split_audio_file_parallel(temp_out_path)
        
        if chunks_with_info:
            print(f"Created {len(chunks_with_info)} chunks for parallel processing")
            # Transcribe chunks in parallel
            transcription_text = transcribe_chunks_parallel(chunks_with_info)
            
            # Clean up chunk files
            for chunk_path, _ in chunks_with_info:
                cleanup_files([chunk_path])
            
            print(f"Total transcription length: {len(transcription_text)} characters")
        else:
            cleanup_files([temp_in_path, temp_out_path])
            return jsonify({"error": "Failed to split audio file"}), 500
    else:
        # File is small enough, transcribe directly
        try:
            print("Transcribing audio file...")
            transcription_text = transcribe_audio_with_provider(temp_out_path)
        except Exception as e:
            cleanup_files([temp_in_path, temp_out_path])
            provider_name = "OpenRouter" if USE_OPENROUTER else "OpenAI"
            return jsonify({"error": f"{provider_name} API error: {str(e)}"}), 500

    # Cleanup audio files
    cleanup_files([temp_in_path, temp_out_path])

    if not transcription_text:
        return jsonify({"error": "Transcription failed"}), 500

    # Immediately start GPT analysis in parallel
    print("Starting GPT analysis...")
    
    # Enhanced prompt for comprehensive analysis
    prompt = f"""Analyze this transcription thoroughly and provide:

1. NOTES (array): Extract ALL of the following:
   - Key points and main topics discussed
   - Important decisions made
   - Problems or challenges mentioned
   - Solutions or recommendations proposed
   - Facts, data, or statistics shared
   - Important names, dates, or deadlines
   - Technical details or specifications
   - Questions raised or concerns expressed
   - Agreements or disagreements
   - Any other significant information

2. SUMMARY (string): Write a comprehensive 3-5 sentence summary that captures:
   - The main purpose/topic of the conversation
   - Key participants and their roles (if mentioned)
   - Major decisions or conclusions reached
   - Critical information or takeaways
   - Overall outcome or next steps

3. ACTION (array): List ALL action items including:
   - Tasks to be completed (with WHO is responsible if mentioned)
   - Deadlines or timeframes (WHEN if mentioned)
   - Follow-up items needed
   - Decisions that need to be made
   - Things to research or investigate
   - Meetings to schedule
   - Documents to create or review
   - People to contact
   - Any other next steps

Be extremely thorough - capture EVERYTHING important. Miss nothing.

Transcription:
{transcription_text}

Return JSON with keys: "notes" (array of strings), "summary" (string), "action" (array of strings)."""

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert analyst. Extract ALL important information comprehensively. Be thorough and miss nothing. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000,  # Increased to capture more details
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = response.choices[0].message.content
        sections = json.loads(result)
        
        # Ensure all required keys are present
        sections.setdefault("notes", ["No notes identified"])
        sections.setdefault("summary", "No summary available")
        sections.setdefault("action", ["No action items identified"])
        
        # Clean up empty values
        sections["notes"] = [n for n in sections.get("notes", []) if n and n.strip()]
        sections["action"] = [a for a in sections.get("action", []) if a and a.strip()]
        
        if not sections["notes"]:
            sections["notes"] = ["No significant notes extracted"]
        if not sections["action"]:
            sections["action"] = ["No action items identified"]
            
        # Return combined result
        return jsonify({
            "text": transcription_text,
            "sections": sections
        })
        
    except Exception as e:
        # Return transcription even if GPT fails
        return jsonify({
            "text": transcription_text,
            "sections": {
                "notes": ["GPT analysis failed - review transcription manually"],
                "summary": "Unable to generate summary",
                "action": ["Review transcription for action items"]
            }
        })

@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Legacy endpoint for compatibility"""
    result = transcribe_and_analyze()
    data = result[0].get_json()
    if "text" in data:
        return jsonify({"text": data["text"]})
    return result

@app.route("/generate-sections", methods=["POST"])
def generate_sections():
    """Legacy endpoint for compatibility"""
    try:
        client = get_client()
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400
        
        transcription_text = data["text"]
        
        # Fast GPT analysis
        prompt = f"""Analyze and extract:
1. NOTES: Key points and details (array)
2. SUMMARY: 3-5 sentence overview (string)  
3. ACTION: All tasks and next steps (array)

Transcription: {transcription_text}

Return JSON with: notes, summary, action"""

        response = client.chat.completions.create(
            model=ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": "Extract insights. Return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        sections = json.loads(response.choices[0].message.content)
        
        # Ensure required keys
        sections.setdefault("notes", ["No notes identified"])
        sections.setdefault("summary", "No summary available")
        sections.setdefault("action", ["No action items identified"])
        
        return jsonify(sections)
        
    except Exception as e:
        return jsonify({"error": f"Error: {str(e)}"}), 500

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
                s.bind(("", 0))
                return s.getsockname()[1]

    env_port = int(os.getenv("PORT", 50263))
    port = get_free_port(env_port)
    
    print(f"Starting OPTIMIZED transcription server on port {port}...")
    print("Features:")
    print("- Parallel chunk processing")
    print("- Combined transcribe + analyze endpoint")
    print("- Multi-threaded operations")
    print("- Optimized for maximum speed")
    
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

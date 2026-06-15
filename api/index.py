import base64
import concurrent.futures
import json
import os
import shutil
import tempfile

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from pydub import AudioSegment

load_dotenv()

app = Flask(__name__)
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


def get_ffmpeg_binary():
    for candidate in [os.getenv("FFMPEG_BINARY"), shutil.which("ffmpeg")]:
        if candidate and os.path.exists(candidate):
            return candidate
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FFMPEG_BINARY = get_ffmpeg_binary()
AudioSegment.converter = FFMPEG_BINARY
AudioSegment.ffmpeg = FFMPEG_BINARY


def get_client():
    if not AI_API_KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY or OPENAI_API_KEY")
    kwargs = {"api_key": AI_API_KEY}
    if USE_OPENROUTER:
        kwargs["base_url"] = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        kwargs["default_headers"] = {
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://transcriptai-sigma.vercel.app"),
            "X-Title": "TranscriptAI",
        }
    return OpenAI(**kwargs)


def transcribe_file(file_path):
    client = get_client()
    if USE_OPENROUTER:
        with open(file_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        resp = client.chat.completions.create(
            model=TRANSCRIPTION_MODEL,
            messages=[
                {"role": "system", "content": "Transcribe the audio accurately. Return only the transcript."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Please transcribe this audio verbatim."},
                    {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "mp3"}},
                ]},
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content
        return content if isinstance(content, str) else str(content)
    else:
        with open(file_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model=TRANSCRIPTION_MODEL,
                file=f,
                language="en",
                temperature=0,
                response_format="text",
            )
        return result if isinstance(result, str) else result.text


def analyze_text(text):
    client = get_client()
    resp = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        messages=[
            {"role": "system", "content": "You analyze transcriptions. Always respond with valid JSON."},
            {"role": "user", "content": f"""Based on this transcription, generate:
1. Key notes and important points
2. A concise summary
3. Action items or next steps

Transcription:
{text}

Respond as JSON with keys: "notes", "summary", "action"."""},
        ],
        temperature=0.7,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    try:
        sections = json.loads(content)
    except Exception:
        sections = {}
    return {
        "notes": sections.get("notes", "No notes available"),
        "summary": sections.get("summary", "No summary available"),
        "action": sections.get("action", "No action items"),
    }


@app.route("/transcribe-and-analyze", methods=["POST"])
def transcribe_and_analyze():
    if "audio" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["audio"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    suffix = os.path.splitext(file.filename)[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    mp3_path = tmp_path + ".mp3"
    try:
        audio = AudioSegment.from_file(tmp_path)
        audio.export(mp3_path, format="mp3", bitrate="96k", parameters=["-ar", "16000", "-ac", "1"])
        transcript = transcribe_file(mp3_path)

        # Run analysis in parallel with a thread
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            analysis_future = ex.submit(analyze_text, transcript)
            sections = analysis_future.result(timeout=30)

        return jsonify({"text": transcript, **sections})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        for p in [tmp_path, mp3_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass


@app.route("/generate-sections", methods=["POST"])
def generate_sections():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400
    try:
        sections = analyze_text(data["text"])
        return jsonify(sections)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"})

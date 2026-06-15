import json
import os
import tempfile

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI

load_dotenv()

# public/ is one level up from api/
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "..", "public")

app = Flask(__name__, static_folder=PUBLIC_DIR, static_url_path="")
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def get_client():
    key = request.headers.get("X-OpenAI-Key") or OPENAI_API_KEY
    if not key:
        raise RuntimeError("No API key available")
    return OpenAI(api_key=key)


def analyze_text(text):
    client = get_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
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


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


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

    try:
        client = get_client()
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en",
                temperature=0,
                response_format="text",
            )
        transcript = result if isinstance(result, str) else result.text
        sections = analyze_text(transcript)
        return jsonify({"text": transcript, **sections})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@app.route("/generate-sections", methods=["POST"])
def generate_sections():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400
    try:
        return jsonify(analyze_text(data["text"]))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Serve the React/static frontend for everything else
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    full = os.path.join(PUBLIC_DIR, path)
    if path and os.path.exists(full):
        return send_from_directory(PUBLIC_DIR, path)
    return send_from_directory(PUBLIC_DIR, "index.html")

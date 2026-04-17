# TranscriptAI

TranscriptAI is a local and cloud-deployable audio transcription app with AI-generated notes, summaries, and action items.

## Canonical backend

Use `python_server_optimized.py` as the only supported runtime path.

- Frontend: `public/index.html`, `public/script.js`, `public/style.css`
- Backend: `python_server_optimized.py`
- Legacy variants: `server.js`, `python_server.py`, and `python_server_chunked.py`

The legacy servers are kept for reference only. They are not the deployment target.

## Local setup

### Prerequisites

- Python 3.11.x recommended.
- An OpenRouter API key.
- `ffmpeg` is bundled through `imageio-ffmpeg`, so you do not need a separate system install for the default setup.

### Install dependencies

```bash
cd /Users/jjohnson/Downloads/transcriptai
python3.11 -m pip install -r requirements.txt
```

### Configure environment

Create a `.env` file with:

```bash
OPENROUTER_API_KEY=your_openrouter_key_here
TRANSCRIPTION_MODEL=openai/gpt-audio-mini
ANALYSIS_MODEL=openai/gpt-4.1-mini
PORT=50263
```

### Run locally

```bash
python3.11 python_server_optimized.py
```

Open `http://localhost:50263`.

## Tests

The Playwright tests expect the local server on port `50263`.

```bash
npx playwright test
```

If you only want a quick smoke check, open the app and upload `Fairfield Dr 16.m4a`.

## Render deployment

This repo includes a Render blueprint in `render.yaml`.

### Service settings

- Runtime: Python
- Start command: `gunicorn python_server_optimized:app --bind 0.0.0.0:$PORT`
- Build command: `pip install -r requirements.txt`

### Required Render secrets

- `OPENROUTER_API_KEY`
- Optional:
  - `TRANSCRIPTION_MODEL` (defaults to `openai/gpt-audio-mini`)
  - `ANALYSIS_MODEL` (defaults to `openai/gpt-4.1-mini`)
  - `OPENROUTER_SITE_URL`
  - `OPENROUTER_APP_NAME`

### Deploy flow

1. Push the repo to a git host connected to Render.
2. Import the repo into Render using the blueprint in `render.yaml`.
3. Add `OPENROUTER_API_KEY` in the Render dashboard.
4. Deploy the web service.

## Runtime files

- `uploads/` holds temporary uploaded audio and can be cleared safely.
- `test-results/`, `test-debug.png`, and `test-result.png` are generated artifacts and are not part of the app.

## Mac app notes

The desktop launcher and updater scripts already point at `python_server_optimized.py`.

- `start_transcription_app.command`
- `TranscriptAI.applescript`
- `app_updater.py`
- `update_app.sh`

## File map

```text
transcriptai/
├── python_server_optimized.py  # Canonical backend
├── public/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── render.yaml                 # Render blueprint
├── requirements.txt            # Python dependencies
├── TranscriptAI.applescript
├── app_updater.py
├── update_app.sh
└── tests/
```

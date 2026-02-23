```markdown
# Grahakchetna — Grahak Chetna AI News Studio

Grahakchetna is a lightweight Flask-based service that generates short, vertical "news" videos
from a headline and description. It composes the narration via a script-generation API, synthesizes
speech via multiple TTS backends, then renders a vertical MP4 using MoviePy and provided media
assets. Generated videos are tracked in a manifest and can be downloaded or (optionally) posted
to social platforms.

Features
- Generate spoken news scripts using the configured LLM (Groq)
- Multi-backend TTS pipeline: ElevenLabs → Edge TTS → gTTS → pyttsx3
- Compose 1080x1920 vertical videos with background, anchor/logo, ticker and breaking-bar
- Store generated video metadata in `videos/manifest.json`
- Optional Facebook Reel upload flow (3-phase START/UPLOAD/FINISH)
- Basic trend fetching and RSS helpers for topic discovery

Quick start
1. Create a Python virtualenv and install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create a `.env` file with required environment variables for optional features:

```
GROQ_API_KEY=your_groq_api_key
ELEVENLABS_API_KEY=your_elevenlabs_key
PAGE_ID=your_facebook_page_id
PAGE_ACCESS_TOKEN=your_facebook_page_access_token
NEWSAPI_KEY=your_newsapi_key
```

3. Run the app (default port `5002`):

```bash
python app.py
```

Open http://localhost:5002 in a browser.

Files of interest
- `app.py` — Flask app and endpoints (`/generate`, `/generate-and-post`, `/videos`, `/video/<file>`)
- `script_service.py` — prompt builder calling Groq LLM
- `tts_service.py` — TTS orchestration and caching
- `video_service.py` — MoviePy composition and final MP4 output
- `facebook_uploader.py` — helper to upload reels to Facebook Page
- `templates/index.html` — web UI
- `assets/` and `static/` — video/music and UI assets

Notes
- The Facebook upload feature requires valid `PAGE_ID` and `PAGE_ACCESS_TOKEN` environment variables.
- The project expects `assets/bg.mp4`, `assets/music.mp3` and `static/anchor.png`/`static/logo.jpg` to be present for best results.

Security note
-------------

This repository recently had a Google OAuth client secret committed and subsequently removed from history. The file pattern `client_secret_*.json` has been added to `.gitignore`. Rotate any exposed credentials immediately; see `CREDENTIAL_ROTATION.md` for details.

License
This repository contains internal code and assets — follow your project's licensing and distribution rules.
```
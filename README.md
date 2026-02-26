```markdown
# Nexora Media Manager by Grahak Chetna

*Developed by Hardikkumar Gajjar, Aidni Global LLP – Ahmedabad*


Grahakchetna is a lightweight Flask-based service that generates AI-powered news videos in two formats:

1. **Shorts** (1080x1920 vertical) – Quick, engaging news clips for Instagram Reels and TikTok
2. **Long-form** (1920x1080 horizontal) – 8–12 minute YouTube videos with structured narrative

It composes narration via script-generation API, synthesizes speech via multiple TTS backends, then renders videos using MoviePy and provided media assets. Generated videos are tracked in a manifest and can be downloaded or (optionally) posted to social platforms.

## Features

**Core capabilities:**
- Generate spoken news scripts using the configured LLM (Groq)
- Multi-backend TTS pipeline: ElevenLabs → Edge TTS → gTTS → pyttsx3
- Compose videos in two formats:
  - **Shorts**: 1080x1920 vertical format with anchor, logo, ticker, and breaking bar
  - **Long-form**: 1920x1080 horizontal format with section titles, smooth transitions, background music
- Long-form scripts: 1000–1500 words with structured sections (Hook, Background, What Happened, Why It Matters, Future Implications, Closing)
- Store generated video metadata in `videos/manifest.json`
- Optional Facebook Reel upload flow (3-phase START/UPLOAD/FINISH)
- Basic trend fetching and RSS helpers for topic discovery

**Video synthesis:**
- Automatic background video looping/trimming
- Logo and branding overlays
- Lower-third section titles for long-form
- Background music mixing
- Professional title bars and info bars
- Smooth crossfades between sections

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

## API Endpoints

### Short-form videos (1080x1920 vertical)
- `POST /generate` – Generate a vertical news video
  ```json
  {
    "headline": "Breaking news title",
    "description": "Video description",
    "language": "english",
    "voice_provider": "auto",
    "voice_model": "auto",
    "video_length": "full"
  }
  ```
  Returns: `{"status": "success", "video": {...}, "download_url": "..."}`

- `POST /generate-and-post` – Generate video and auto-post to Facebook
  ```json
  {
    "headline": "Breaking news title",
    "description": "Video description",
    "language": "english",
    "auto_post": true
  }
  ```

### Long-form videos (1920x1080 horizontal for YouTube)
- `POST /generate-long` – Generate an 8–12 minute YouTube video
  ```json
  {
    "title": "Why Hungary Blocked EU Sanctions",
    "description": "Hungary blocks EU sanctions package against Russia before war anniversary.",
    "language": "english"
  }
  ```
  Returns:
  ```json
  {
    "status": "success",
    "video_path": "videos/long/long_video_20240224_143022_123.mp4",
    "video_url": "/video/long_video_20240224_143022_123.mp4",
    "script_word_count": 1247,
    "video": {
      "id": "...",
      "filename": "...",
      "size_mb": 245.5,
      ...
    }
  }
  ```

- `GET /test-long` – Test with predefined long-form video
  - Generates a sample video about "Why Hungary Blocked EU Sanctions"
  - Useful for testing and demonstration

### Video Management
- `GET /videos` – List all generated videos with metadata
- `GET /video/<filename>` – Download a specific video
- `DELETE /video/<filename>` – Delete a video and update manifest

## Examples

### Generate a short-form vertical video
```bash
curl -X POST http://localhost:5002/generate \
  -F "headline=Breaking: Major Policy Change" \
  -F "description=Government announces sweeping reforms" \
  -F "language=english"
```

### Generate a long-form YouTube video
```bash
curl -X POST http://localhost:5002/generate-long \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Why Hungary Blocked EU Sanctions",
    "description": "Hungary blocks EU sanctions package against Russia before war anniversary.",
    "language": "english"
  }'
```

### Test long-form generation
```bash
curl http://localhost:5002/test-long
```

## Files & Architecture

- `app.py` — Flask app with all endpoints
- `script_service.py` — Short-form script generation (headline + description)
- `long_script_service.py` — Long-form script generation (1000–1500 words, structured sections)
- `tts_service.py` — TTS orchestration and caching (multi-backend fallback)
- `video_service.py` — Short-form video composition (1080x1920 vertical)
- `long_video_service.py` — Long-form video composition (1920x1080 horizontal)
- `facebook_uploader.py` — Facebook Reel upload helper
- `templates/index.html` — Web UI
- `assets/` — Background video (`bg.mp4`) and music (`music.mp3`)
- `static/` — Logo (`logo.jpg`) and anchor overlay (`anchor.png`)

## Long-form Video Workflow

1. **Script Generation** (`long_script_service.py`)
   - Groq LLM generates 1000–1500 word script
   - Structured sections: Hook → Background → What Happened → Why It Matters → Future → Closing
   - Professional news tone, optimized for retention

2. **TTS Synthesis** (`tts_service.py`)
   - Existing multi-backend TTS pipeline
   - Fallback chain: ElevenLabs → Edge TTS → gTTS → pyttsx3

3. **Video Composition** (`long_video_service.py`)
   - 1920x1080 horizontal format (YouTube optimized)
   - Background video looped/trimmed to audio length
   - Upper title bar with headline
   - Lower-third section markers at strategic points
   - Logo overlay (top-right)
   - Info bar (bottom) with branding
   - Background music mixed at 10% volume
   - 3-second ending screen with thank you message

4. **Manifest & Storage**
   - Video metadata saved to `videos/manifest.json`
   - Videos organized in `videos/` and `videos/long/` directories
   - File size and creation timestamp tracked

## Requirements & Setup

**System dependencies:**
- Python 3.8+
- FFmpeg (for MoviePy video encoding)
  ```bash
  # Ubuntu/Debian
  sudo apt-get install ffmpeg
  
  # macOS
  brew install ffmpeg
  ```

**Python dependencies:**
All required packages are listed in `requirements.txt`. Install with:
```bash
pip install -r requirements.txt
```

**Asset files required:**
- `assets/bg.mp4` – Background video for all video types
- `assets/music.mp3` – Background music (long-form videos use at 10% volume)
- `static/logo.jpg` – Logo/branding overlay
- `static/anchor.png` – Anchor image for short-form videos

**Environment variables** (`.env` file):
```
# Required
GROQ_API_KEY=your_groq_api_key

# Optional (for additional TTS backends)
ELEVENLABS_API_KEY=your_elevenlabs_key

# Optional (for social media posting)
PAGE_ID=your_facebook_page_id
PAGE_ACCESS_TOKEN=your_facebook_page_access_token
NEWSAPI_KEY=your_newsapi_key

# Optional (for WordPress publishing)
WORDPRESS_URL=https://your-wordpress-site.com
WORDPRESS_USERNAME=your_user
WORDPRESS_APP_PASSWORD=your_app_password
```

## Notes

### General
- Video output directories (`videos/` and `videos/long/`) are created automatically on first run.
- All generated videos are tracked in `videos/manifest.json` with metadata (filename, size, creation time, language, etc.)

### Short-form videos
- Output format: 1080×1920 vertical (9:16 aspect ratio)
- Typical duration: 15–60 seconds
- Optimal for: Instagram Reels, TikTok, YouTube Shorts
- Facebook upload feature requires `PAGE_ID` and `PAGE_ACCESS_TOKEN` environment variables
- Uses existing anchor overlay and logo branding

### Long-form videos
- Output format: 1920×1080 horizontal (16:9 aspect ratio)
- Typical duration: 8–12 minutes (~1000–1500 words of narration)
- Optimal for: YouTube standard uploads, documentaries
- Script generation creates structured narrative with 6 key sections
- Background video is automatically looped if shorter than audio duration
- Section markers appear at approximately: 5%, 15%, 35%, 55%, 75%, and 90% points
- Background music is mixed at 10% volume for subtle effect
- Ending screen (3 seconds) with branding is automatically appended

### Troubleshooting
- **Video generation hangs**: Check that `assets/bg.mp4` and `assets/music.mp3` exist
- **TTS errors**: Verify `GROQ_API_KEY` is set and valid; check fallback TTS backends
- **Font rendering issues**: Install additional fonts with `sudo apt-get install fonts-noto`
- **FFmpeg not found**: Install with `apt-get install ffmpeg` (Ubuntu) or `brew install ffmpeg` (macOS)

Security note
-------------

This repository recently had a Google OAuth client secret committed and subsequently removed from history. The file pattern `client_secret_*.json` has been added to `.gitignore`. Rotate any exposed credentials immediately; see `CREDENTIAL_ROTATION.md` for details.

License
This repository contains internal code and assets — follow your project's licensing and distribution rules.

## Recent Changes (Feb 2026)

- UI: extracted an independent RSS manager page at `/rss` and added lightweight per-feature entry pages that open the corresponding UI tab:
  - `/wordpress`, `/facebook`, `/instagram`, `/short_ui`, `/long_ui`, `/videos_ui` (these redirect to the in-app tab views)
- TTS: removed Azure TTS provider; fallback chain is now: `Edge TTS` → `ElevenLabs` → `gTTS` → `pyttsx3`. Set `ELEVENLABS_API_KEY` in `.env` to enable ElevenLabs.
- WordPress uploader: improved SSL handling — on TLS/SSL errors the uploader retries once with verification disabled. When WordPress SSL verification is disabled, the web UI shows a visible warning banner.
- Tests: added `mock_wp.py` to allow local testing of `/wordpress/post` flows without a live WordPress instance.

## How to access per-feature UI pages

- Main UI (all tabs): `/` or `/` (renders `templates/index.html`)
- Short video UI (standalone entry): `/short_ui` (redirects to short tab)
- Long video UI (standalone entry): `/long_ui` (redirects to long tab)
- WordPress UI (standalone entry): `/wordpress` (redirects to WordPress tab)
- Facebook UI (standalone entry): `/facebook` (redirects to Facebook tab)
- Instagram UI (standalone entry): `/instagram` (redirects to Instagram tab)
- Videos library: `/videos_ui` (redirects to videos tab)

These lightweight pages make it easier to open a single feature from bookmarks or external links. They currently redirect to the existing tabbed UI but can be extended to host feature-specific templates in the future.
```
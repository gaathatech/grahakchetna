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

### Backgrounds
- `POST /upload-background` – Upload a custom background image/video. Accepts form-data (`bgName`, `bgFile`, `bgDescription`, `makeDefault`). Returns JSON with `filePath` and metadata.
- `GET /get-backgrounds` – Retrieve list of stored backgrounds with details (path, name, uploadedAt, default flag).

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

**Backend:**
- `app.py` — Flask app with all endpoints
- `script_service.py` — Short-form script generation (headline + description)
- `long_script_service.py` — Long-form script generation (1000–1500 words, structured sections)
- `tts_service.py` — TTS orchestration and caching (multi-backend fallback)
- `video_service.py` — Short-form video composition (1080x1920 vertical) & Long-form composition (1920x1080 horizontal)
- `long_video_service.py` — Long-form video wrapper/orchestration
- `facebook_uploader.py` — Facebook Reel upload helper
- `instagram_uploader.py` — Instagram content upload helper
- `wordpress_uploader.py` — WordPress post publishing helper

**Frontend Templates:**
- `templates/base.html` — Master template with global header, navigation, footer, and company branding
- `templates/index.html` — Short video generation UI
- `templates/long.html` — Long video generation UI (simplified form)
- `templates/layout-guide.html` — Comprehensive layout documentation and reference guide
- `templates/layout-designer.html` — Interactive layout visualization and design tool
- `templates/facebook.html` — Facebook posting interface
- `templates/instagram.html` — Instagram posting interface
- `templates/wordpress.html` — WordPress publishing interface
- `templates/rss.html` — RSS feed manager
- `templates/videos.html` — Video archive and management

**Assets:**
- `assets/bg.mp4` — Background video for all video types
- `assets/music.mp3` — Background music (used in long-form videos at 10% volume)
- `static/logo.jpg` — Logo/branding overlay
- `static/anchor.png` — Anchor image for short-form videos
- `static/newsroom-studio-bg.svg` — Professional newsroom studio background (for branding/reference)

## UI & Templates

### Master Template (`base.html`)
All pages inherit from a unified base template featuring:
- **Global Header** with company branding and logo
- **Main Navigation** with links to all major sections:
  - 📱 Short Video, 🎞️ Long Video, 📝 WordPress, 👍 Facebook, 📸 Instagram
  - 🎥 Videos (archive), 🎨 Layout Designer, 📰 RSS Manager
- **Company Information** prominently displayed:
  - **Grahak Chetna** (primary brand)
  - Developed by **Hardikkumar Gajjar**
  - **Aidni Global LLP**, Ahmedabad
- **Responsive Footer** with company details, features, and support links
- **Safe Area Support** for mobile devices with notches

### Layout Guide & Documentation (`layout-guide.html`)
Comprehensive reference for video layout specifications:
- **Dimension Breakdown:**
  - **SHORT Videos** (1080×1920 vertical):
    - Description box: **500px width × 700px height**
    - Font size: 40px
    - Optimized for Instagram Reels, TikTok, YouTube Shorts
  - **LONG Videos** (1920×1080 horizontal):
    - Description box: **800px width × 600px height** (1.6x proportional scaling)
    - Font size: 40px
    - Optimized for YouTube standard upload
- **Color Palette** with hex codes and usage guidelines
- **Visual Previews** showing layout structure for both formats
- **Design Best Practices** (Do's & Don'ts)
- **Technical Specifications** (codecs, fonts, frame rates)
- **Responsive Considerations** with safe areas for notched devices

### Layout Designer (`layout-designer.html`)
Interactive tool for customizing and previewing video layouts with:
- Real-time layout preview (16:9 aspect ratio)
- Customizable layout presets (Default, Cinema, Split, Focus)
- 📐 Complete documentation and color reference
- 🔄 Professional broadcast-standard design

### Video Generation UI Simplification
**Long Video Page** (`long.html`):
- Streamlined form (headline, description, language, voice provider)
- Removed embedded layout customization controls
- Layout settings now managed via `/layout-designer` page
- Focus on video generation parameters only

## Video Layout Specifications

### Short Videos (1080×1920 Vertical)
| Component | Width | Height | Position | Details |
|-----------|-------|--------|----------|---------|
| Logo | Auto | 100px | Top center | Brand identification |
| Headline Bar | 1080px | 120px | Top section | Scrolling red ticker (50px font) |
| Anchor Image | Auto | 750px | Left side | Centered vertically |
| Description Box | **500px** | **700px** | Right side | White text, scrolls if overflow |
| Breaking Bar | 1080px | 130px | Bottom | Red (130px height, centered) |

### Long Videos (1920×1080 Horizontal)
| Component | Width | Height | Position | Details |
|-----------|-------|--------|----------|---------|
| Logo | Auto | 100px | Top right | Brand identification |
| Headline Bar | 1920px | 120px | Top section | Scrolling red ticker (50px font) |
| Anchor Image | Auto | 750px | Left side | Centered vertically |
| Description Box | **800px** | **600px** | Right side | White text, scrolls if overflow |
| Breaking Bar | 1920px | 130px | Bottom | Red (130px height, centered) |

**Color Scheme:**
- **Headline & Breaking Bars:** #DC143C (Crimson Red)
- **Text & Accents:** #FFFFFF (White) with black shadow
- **Background Overlays:** 60% opacity black for contrast
- **UI Elements:** #66b2ff (Bright Blue) accents

## UI Navigation Structure

**Main Pages & Entry Points:**
- `/` — Main dashboard with tabbed interface (Short Video, Long Video, WordPress, Facebook, Instagram, Videos, Layout Designer, RSS Manager)
- `/layout-guide` — Detailed layout documentation and specifications
- `/layout-designer` — Interactive layout preview and customization tool
- `/videos_ui` — Video archive and management
- `/wordpress`, `/facebook`, `/instagram` — Platform-specific posting interfaces
- `/rss` — RSS feed manager and trend fetcher

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

**UI Enhancements:**
- ✨ **New Base Template** (`base.html`): Unified header, navigation, and footer across all pages with company branding
- 📖 **Layout Guide** (`layout-guide.html`): Comprehensive documentation of video dimensions, colors, and design specifications
- 🎨 **Professional Background**: Added newsroom studio background SVG (`static/newsroom-studio-bg.svg`) for branded aesthetics
- 🧹 **Simplified Long Video Form**: Removed embedded layout customization UI; moved to dedicated Layout Designer page
- 📐 **Text Box Dimensions**:
  - SHORT videos: 500×700px description box (fixed)
  - LONG videos: 800×600px description box (proportional scaling)

**Previous Changes:**
- UI: extracted an independent RSS manager page at `/rss` and added lightweight per-feature entry pages that open the corresponding UI tab:
  - `/wordpress`, `/facebook`, `/instagram`, `/short_ui`, `/long_ui`, `/videos_ui` (these redirect to the in-app tab views)
- TTS: removed Azure TTS provider; fallback chain is now: `Edge TTS` → `ElevenLabs` → `gTTS` → `pyttsx3`. Set `ELEVENLABS_API_KEY` in `.env` to enable ElevenLabs.
- WordPress uploader: improved SSL handling — on TLS/SSL errors the uploader retries once with verification disabled. When WordPress SSL verification is disabled, the web UI shows a visible warning banner.
- Tests: added `mock_wp.py` to allow local testing of `/wordpress/post` flows without a live WordPress instance.

## How to access per-feature UI pages

- **Main Dashboard**: `/` or `/index` (all tabs in tabbed interface)
- **Short Video UI**: `/` (Short Video tab) — 1080×1920 vertical format
- **Long Video UI**: `/long` (Long Video tab) — 1920×1080 horizontal format with simplified form
- **Layout Guide & Documentation**: `/layout-guide` — Detailed specifications and best practices
- **Layout Designer**: `/layout-designer` — Interactive layout preview and customization tool
- **WordPress Publishing**: `/wordpress` — WordPress post/page creation interface
- **Facebook Posting**: `/facebook` — Facebook Reel upload interface
- **Instagram Posting**: `/instagram` — Instagram content posting interface
- **Videos Archive**: `/videos_ui` (Videos tab) — Video library and management

**Mobile & Accessibility:**
- All pages use responsive design with mobile-first approach
- Safe area support for notched devices (iPhone X, etc.)
- Keyboard navigation support
- Dark theme optimized for readability and reduced eye strain

## Company & Attribution

**Grahak Chetna**
- Professional AI-powered news video creation platform
- Developed by **Hardikkumar Gajjar**
- **Aidni Global LLP**, Ahmedabad, India

**Technology Stack:**
- Backend: Flask (Python), MoviePy for video composition
- Frontend: HTML5, CSS3, Vanilla JavaScript (no external JS framework dependencies)
- TTS: Multi-backend pipeline (Edge TTS, ElevenLabs, gTTS, pyttsx3)
- LLM: Groq API for script generation
- Media: FFmpeg for video encoding
```
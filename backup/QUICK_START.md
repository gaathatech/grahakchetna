# 🚀 Quick Start Guide - Grahak Chetna AI News Studio

## System Status
✅ **All systems operational and ready to use**

---

## 📱 Accessing the Application

### Web Interface
```
URL:      http://localhost:5002
Port:     5002
Browser:  Any modern browser (Chrome, Firefox, Safari, Edge)
```

### Start the Application
```bash
cd /workspaces/grahakchetna
python3 app.py
```

The app will:
1. Create necessary directories (videos, output, static)
2. Load the manifest (list of previously generated videos)
3. Start listening on port 5002

---

## 🎬 Creating Your First Video

### Step 1: Open the Web Interface
Visit: `http://localhost:5002`

### Step 2: Fill in the Form
```
Headline:    "Breaking News: Your Title Here"
Description: "Detailed story of what's happening..."
Language:    Select from English, Hindi, or Gujarati
```

### Step 3: Click "Generate Video"
The system will:
1. Generate script from your text (via GROQ)
2. Create voice narration (via Edge TTS)
3. Render video with all elements
4. Save to `/videos` directory
5. Add metadata to manifest

**Time Required:** ~60-90 seconds

### Step 4: Download or Delete
Once complete:
- **Download:** Click "⬇ Download" button to save the MP4 file
- **Delete:** Click "🗑 Delete" if you want to remove it

---

## 📊 Video Management

### View All Videos
Open the right panel on the web interface to see all generated videos with:
- Headline
- Language
- File size
- Creation timestamp
- Action buttons (Download/Delete)

### Download a Video
```bash
# Via Web UI: Click blue download button
# Via CLI: curl -o video.mp4 http://localhost:5002/video/VIDEO_FILENAME
```

### Delete a Video
```bash
# Via Web UI: Click red delete button
# Via API: curl -X DELETE http://localhost:5002/video/VIDEO_FILENAME
```

---

## 🔌 API Endpoints

### Get list of all videos
```bash
curl http://localhost:5002/videos
```

**Response:**
```json
{
  "videos": [
    {
      "id": "20260216_035000_685",
      "filename": "video_20260216_034913_576.mp4",
      "headline": "Breaking News: Title",
      "language": "english",
      "size_mb": 0.49,
      "created_at": "2026-02-16T03:50:00.685442"
    }
  ]
}
```

### Generate a new video
```bash
curl -X POST http://localhost:5002/generate \
  -F "headline=Breaking News: Title" \
  -F "description=Story details here..." \
  -F "language=english"
```

### Download a specific video
```bash
curl -o output.mp4 http://localhost:5002/video/video_20260216_034913_576.mp4
```

### Delete a video
```bash
curl -X DELETE http://localhost:5002/video/video_20260216_034913_576.mp4
```

---

## 🌐 Language Support

| Language | Code | Voice | Quality |
|----------|------|-------|---------|
| English | `english` | en-IN-PrabhatNeural | ⭐⭐⭐⭐⭐ |
| Hindi | `hindi` | hi-IN-SwaraNeural | ⭐⭐⭐⭐⭐ |
| Gujarati | `gujarati` | gu-IN-DhwaniNeural | ⭐⭐⭐⭐⭐ |

---

## 📁 File Structure

```
Generated videos are saved in:
/workspaces/grahakchetna/videos/

├── video_20260216_034913_576.mp4      (English news)
├── video_20260216_035136_430.mp4      (Hindi news)
├── video_20260216_035139_246.mp4      (Gujarati news)
├── manifest.json                       (Metadata)
└── ... (more videos)

Manifest format:
{
  "videos": [
    {
      "id": "unique-id",
      "filename": "video_*.mp4",
      "path": "videos/video_*.mp4",
      "headline": "News headline",
      "description": "News description",
      "language": "english",
      "created_at": "ISO timestamp",
      "size_mb": 0.49
    }
  ]
}
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)
```bash
GROQ_API_KEY=your_groq_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVEN_VOICE_ID=your_voice_id
```

### Required Assets
```
assets/
├── bg.mp4           Background video (1080x1920)
└── music.mp3        Background music

static/
├── anchor.png       News anchor image (750px height)
└── logo.jpg         Brand logo (100px height)
```

---

## 🎨 Customization

### Change Colors
Edit `video_service.py`:
```python
COLOR_ACCENT_RED = (220, 20, 60)      # Primary red
COLOR_ACCENT_DARK_RED = (139, 0, 0)   # Dark red border
```

### Change Text Sizes
In `generate_video()` function:
```python
# Headline text size
fontsize=50

# Description text size
fontsize=40

# Breaking news text size
fontsize=55
```

### Replace Assets
Update these files:
- `assets/bg.mp4` - Background video (must be 1080x1920)
- `assets/music.mp3` - Background music
- `static/anchor.png` - News anchor
- `static/logo.jpg` - Brand logo

---

## 🔧 Troubleshooting

### App won't start
```bash
# Check if port 5002 is in use
lsof -i :5002

# Kill existing process
pkill -f "python3 app.py"

# Restart
python3 app.py
```

### Videos not generating
1. Check `.env` has valid API keys
2. Check network connection
3. Check `assets/bg.mp4` and `assets/music.mp3` exist
4. Check logs: `tail -100 /tmp/app.log`

### Videos taking too long
- Normal generation time: 60-90 seconds
- Check CPU usage: `top`
- Check disk space: `df -h`

---

## 📊 Performance Tips

### For Faster Generation
1. Use shorter descriptions (less TTS processing)
2. Use English over Hindi/Gujarati (faster voice generation)
3. Ensure system has 2GB+ free RAM
4. Close other applications

### For Better Quality
1. Use detailed descriptions
2. Check anchor.png quality
3. Ensure assets/bg.mp4 is high quality
4. Use professional language in headline

---

## 🔐 Notes

### Security
- Videos are stored in `/videos` directory
- Filenames are timestamped (collision-safe)
- No sensitive data in filenames
- Local system only (no cloud storage)

### Storage
- Each video: ~0.4-0.5 MB
- Manifest: < 1 KB per video
- 100 videos ≈ 50 MB storage

---

## 📞 Common Commands

### Start app
```bash
cd /workspaces/grahakchetna
python3 app.py
```

### Stop app
```bash
pkill -f "python3 app.py"
```

### Clear all videos
```bash
rm -rf /workspaces/grahakchetna/videos
mkdir /workspaces/grahakchetna/videos
```

### View app logs
```bash
tail -f /tmp/app.log
```

### Check app status
```bash
curl http://localhost:5002/
```

---

## 📝 Example Workflows

### Workflow 1: Single Video Generation
```bash
1. Visit http://localhost:5002
2. Enter headline and description
3. Click Generate
4. Wait 60-90 seconds
5. Click Download
6. Done!
```

### Workflow 2: Batch Generation (Python Script)
```python
import requests
import time

headlines = [
    "Breaking News: Story 1",
    "Breaking News: Story 2",
]

for headline in headlines:
    data = {
        "headline": headline,
        "description": "Full story details...",
        "language": "english"
    }
    response = requests.post("http://localhost:5002/generate", data=data)
    print(f"Generated: {response.json()}")
    time.sleep(120)  # Wait between generations
```

### Workflow 3: Automated Publishing
```bash
# Generate video
curl -X POST http://localhost:5002/generate \
  -F "headline=Latest News" \
  -F "description=News content..." \
  -F "language=english" > response.json

# Extract URL and download
VIDEO_URL=$(jq -r '.video.download_url' response.json)
curl -o news_video.mp4 "http://localhost:5002${VIDEO_URL}"

# Upload to your platform
# (integrate with YouTube, Instagram, etc.)
```

---

## 🎓 Learning Resources

- **Flask Documentation:** https://flask.palletsprojects.com/
- **MoviePy Docs:** https://zulko.github.io/moviepy/
- **Edge TTS GitHub:** https://github.com/rany2/edge-tts
- **GROQ API:** https://console.groq.com/

---

## ✅ Checklist for production use

- [ ] API keys configured in `.env`
- [ ] Test video generation in all languages
- [ ] Verify assets (bg.mp4, music.mp3, anchor.png, logo.jpg)
- [ ] Set up regular backups of `/videos` directory
- [ ] Monitor disk space
- [ ] Document any customizations
- [ ] Test API endpoints
- [ ] Verify UI on target devices

---

**Last Updated:** February 16, 2026  
**Status:** ✅ Ready for Production  
**Support:** Check IMPLEMENTATION_REPORT.md for detailed documentation


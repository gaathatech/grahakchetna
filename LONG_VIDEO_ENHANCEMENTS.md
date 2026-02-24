# Long-Form Video Enhancements

## 🎬 New Features Added

Grahakchetna now supports enhanced long-form video generation with professional visual elements:

### 1. **Custom Background Video** ✓
- **File**: `long video background.mp4` (5.7 MB)
- **Use**: Replaced standard bg.mp4 with custom professional background
- **Format**: 1920x1080 horizontal (YouTube optimized)
- **Duration**: Auto-looped to match audio duration

### 2. **Green Screen Overlay** ✓
- **Position**: Left side (400x400px)
- **Distance from top**: Below title bar (180px)
- **Support**: Both IMAGE and VIDEO uploads
- **Features**:
  - User can upload custom image (PNG, JPG) or video (MP4, MOV, AVI, MKV)
  - Auto-scales to 400x400 dimensions
  - Placeholder green screen shown if no upload provided
  - Video loops/trims to match narration duration

### 3. **Breaking News Ticker** ✓
- **Position**: Bottom of screen (above info bar)
- **Style**: Dark background with red accent line
- **Text**: Scrolls horizontally from right to left
- **Content**: `🔴 BREAKING NEWS: [Headline] — [Description]`
- **Animation**: Smooth continuous scroll
- **Speed**: Adjusts based on total video duration

### 4. **Side Scrolling Text** ✓
- **Position**: Right side panel (400px wide)
- **Background**: Semi-transparent dark overlay
- **Direction**: Vertical scroll (top to bottom)
- **Content**: Full description text
- **Speed**: Independent scroll duration (12+ seconds)
- **Looping**: Auto-loops if video is longer

---

## 📐 Video Layout

```
┌─────────────────────────────────────────────────────────────┐
│                        TITLE BAR (RED)                       │ 120px
│                 Headline + Logo (top-right)                  │
├────────────┬─────────────────────────────────────┬──────────┤
│   GREEN    │                                     │  SIDE    │
│  SCREEN    │       MAIN BACKGROUND VIDEO        │  TEXT    │
│  OVERLAY   │                                     │ SCROLL   │
│ 400x400px  │                                     │ 400px    │
│            │                                     │          │
├────────────┴─────────────────────────────────────┴──────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │ 70px
│  │ 🔴 BREAKING NEWS: [Ticker scrolling left] ←────  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
├───────────────────────────────────────────────────────────── │
│              Grahak Chetna | [Description...]             │ 100px
└───────────────────────────────────────────────────────────── ┘
```

---

## 🎯 API Usage

### Generate Long Video with Green Screen

#### Method 1: JSON (No Green Screen)
```bash
curl -X POST http://localhost:5002/generate-long \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Breaking: Major Announcement",
    "description": "Details about the breaking story",
    "language": "english"
  }'
```

#### Method 2: Form Data (With Green Screen)
```bash
curl -X POST http://localhost:5002/generate-long \
  -F "title=Breaking: Major Announcement" \
  -F "description=Details about the breaking story" \
  -F "language=english" \
  -F "green_screen=@/path/to/presenter.png"
```

### Response
```json
{
  "status": "success",
  "video_path": "videos/long/long_video_20260224_143022_123.mp4",
  "video_url": "/video/long_video_20260224_143022_123.mp4",
  "script_word_count": 1247,
  "video": {
    "id": "...",
    "filename": "long_video_20260224_143022_123.mp4",
    "size_mb": 245.5,
    "created_at": "2026-02-24T14:30:22.123000"
  }
}
```

---

## 🎨 Customization Options

### Green Screen Media
- **Supported Image Formats**: PNG, JPG, JPEG, GIF, BMP
- **Supported Video Formats**: MP4, MOV, AVI, MKV, WebM
- **Recommended Resolution**: 400x400 or larger (auto-scaled)
- **Suggested Use Cases**:
  - Presenter/anchor image
  - Logo animation
  - Product showcase
  - Studio background

### Ticker Text
- **Source**: Auto-generated from headline + description
- **Format**: `🔴 BREAKING NEWS: [Your Headline] — [Your Description]`
- **Speed**: Adapts to video duration
- **Font Size**: 36pt (adjustable in code)
- **Color**: White text on dark background with red accent

### Side Text
- **Source**: Full description text
- **Scroll Speed**: Adjustable (default 12+ seconds for full scroll)
- **Font Size**: 32pt (adjustable in code)
- **Vertical Position**: Starts below top title bar

---

## 🔧 Technical Details

### File Locations
```
/workspaces/grahakchetna/
├── long video background.mp4          ← Main background (5.7MB)
├── long_video_service.py              ← Enhanced service
├── app.py                              ← Updated endpoints
├── uploads/                            ← User green screen uploads
│   └── gs_TIMESTAMP_filename.*
└── videos/long/                        ← Generated videos
    └── long_video_TIMESTAMP.mp4
```

### Generated Components (Temporary)
- `*_ticker_text.png` - Scrolling ticker text image
- `*_side_text.png` - Scrolling side text image  
- `*_gs_placeholder.png` - Green screen placeholder (if no upload)

All temporary PNG files are auto-cleaned up after video generation.

---

## ⚙️ Configuration

### Environment Variables (Optional)
No new env vars required - uses existing setup:
- `GROQ_API_KEY` - For script generation
- `ELEVENLABS_API_KEY` - For TTS (optional)

### Adjustable Parameters (In Code)

Edit `long_video_service.py`:

```python
# Green screen dimensions
green_screen_width = 400      # pixels
green_screen_height = 400     # pixels
green_screen_x = 40           # left margin
green_screen_y = 180          # top offset

# Ticker settings
TICKER_FONTSIZE = 36          # points
TICKER_BAR_HEIGHT = 70        # pixels
TICKER_SCROLL_DURATION = auto # seconds

# Side text settings
SIDE_TEXT_FONTSIZE = 32       # points
SIDE_PANEL_WIDTH = 400        # pixels
SIDE_SCROLL_DURATION = auto   # seconds
```

---

## 📊 Performance

### Video Generation Time (Estimated)
- Script generation: 10-20 seconds
- TTS audio: 30-60 seconds (depends on script length)
- Video composition: 120-300 seconds (depends on duration & codec)
- **Total**: 5-10 minutes for 8-12 minute video

### File Sizes
- 8-minute video: ~100-150 MB
- 10-minute video: ~150-200 MB
- 12-minute video: ~200-250 MB

### System Requirements
- Min 2GB RAM (4GB+ recommended)
- ~5GB free disk space per video
- CPU: Modern multi-core processor
- FFmpeg: Required for video encoding

---

## ✅ Testing

### Test with Sample Green Screen

```bash
# Create a test image (green screen placeholder)
python3 << 'PYEOF'
from PIL import Image, ImageDraw, ImageFont

# Create 400x400 green image
img = Image.new("RGB", (400, 400), (0, 128, 0))
draw = ImageDraw.Draw(img)
draw.text((50, 180), "TEST GREEN SCREEN", fill=(255, 255, 255))
img.save("test_green_screen.png")
print("✓ test_green_screen.png created")
PYEOF

# Generate video with test green screen
curl -X POST http://localhost:5002/generate-long \
  -F "title=Test Video" \
  -F "description=Testing green screen overlay" \
  -F "green_screen=@test_green_screen.png"
```

---

## 🐛 Troubleshooting

### Issue: Green Screen Not Showing
- **Check**: File exists and is readable
- **Check**: Supported format (PNG, JPG, MP4, MOV, etc.)
- **Solution**: Use placeholder by not uploading - will show green screen guide

### Issue: Ticker Text Cut Off
- **Check**: Font size not too large
- **Solution**: Text auto-adjusts and scrolls continuously

### Issue: Side Text Not Visible
- **Check**: Description not empty
- **Solution**: Text appears on right panel - may need scroll to see

### Issue: Background Video Errors
- **Check**: `long video background.mp4` exists in root directory
- **Solution**: Falls back to `assets/bg.mp4` if not found
- **Note**: Only 120 seconds fallback background

---

## 🚀 Future Enhancements

Potential additions:
- [ ] Multiple green screen positions (left, right, center, picture-in-picture)
- [ ] Custom ticker colors and styles
- [ ] Animated transitions between sections
- [ ] Caption overlay support
- [ ] Multi-language ticker support
- [ ] Custom scroll speeds per text element
- [ ] Watermark overlay
- [ ] Scene detection and auto-positioning

---

## 📝 Examples

### Example 1: Political News
```
Title: "Hungary Blocks EU Sanctions"
Description: "Hungary blocks EU sanctions package against Russia..."
Green Screen: country_flag.png
Result: Flag shown on left, ticker running at bottom, description scrolling right
```

### Example 2: Tech News
```
Title: "New AI Model Released"
Description: "Major breakthrough in artificial intelligence announced..."
Green Screen: company_logo_animation.mp4
Result: Logo animation looping on green screen area
```

### Example 3: Breaking News
```
Title: "Breaking: Market Crashes"
Description: "Stock market experiences significant downturm..."
Green Screen: (auto-placeholder)
Result: Professional news-style video with empty green screen guide (can be keyed out later)
```

---

## 📞 Support

For issues or questions about long-form video enhancements:
1. Check console logs: `app.py` debug output
2. Review `long_video_service.py` for detailed generation steps
3. Verify all asset files exist
4. Ensure sufficient disk space

---

**Version**: 1.0
**Last Updated**: February 24, 2026
**Tested On**: Python 3.9+, MoviePy 1.0.3, Pillow 10.0.0

# 🚀 Long-Form Video Quick Start Guide

## ⚡ 30-Second Setup

Your Grahakchetna system is **fully configured** and ready to generate professional long-form videos!

---

## 📝 Basic Commands

### 1. Generate a Video (Simplest)
```bash
curl -X POST http://localhost:5002/generate-long \
  -H "Content-Type: application/json" \
  -d '{"title": "Breaking: Major Event", "description": "Details here"}'
```

### 2. Generate with Green Screen
```bash
curl -X POST http://localhost:5002/generate-long \
  -F "title=Breaking: Major Event" \
  -F "description=Details here" \
  -F "green_screen=@presenter.png"
```

### 3. Test It Out
```bash
# No parameters needed - uses sample data
curl http://localhost:5002/test-long
```

---

## 🎬 What You Get

**Output**: Professional 1920×1080 video (8-12 minutes)

**Includes**:
- ✅ AI-generated script (1000-1500 words)
- ✅ Narration with background music
- ✅ Breaking news ticker (bottom)
- ✅ Green screen overlay (left side) - if uploaded
- ✅ Scrolling description (right side)
- ✅ Section markers throughout
- ✅ Professional branding and title bars

---

## 🎨 Customization Quick Tips

### Green Screen Options
- **Presenter image**: PNG/JPG (400×400 pixels)
- **Logo animation**: MP4 video
- **Company graphic**: Any image format
- **Auto-placeholder**: Leave empty to use green screen guide

### Video Formats Supported
| Format | Support |
|--------|---------|
| PNG / JPG | ✅ Images |
| MP4 / MOV | ✅ Video |
| AVI / MKV | ✅ Video |
| GIF | ✅ Image |
| Max size | 100 MB |

---

## 📱 Share Your Video

### Facebook Reels
```bash
curl -X POST http://localhost:5002/facebook/post \
  -H "Content-Type: application/json" \
  -d '{"video_path": "videos/long/long_video_[timestamp].mp4"}'
```

### Instagram
```bash
curl -X POST http://localhost:5002/instagram/post \
  -H "Content-Type: application/json" \
  -d '{"video_path": "videos/long/long_video_[timestamp].mp4"}'
```

### WordPress Blog
```bash
curl -X POST http://localhost:5002/wordpress/post \
  -H "Content-Type: application/json" \
  -d '{"video_path": "videos/long/long_video_[timestamp].mp4", "title": "Blog Title"}'
```

---

## 🎯 Common Use Cases

### Breaking News Format
```
Title: "Hungary Blocks EU Sanctions"
Description: "European Union tensions rise as Hungary..."
Green Screen: (empty - placeholder)
Result: Professional news video ready for broadcast
```

### Interview/Commentary
```
Title: "Expert Analysis: Market Trends"
Description: "Expert discusses recent market developments..."
Green Screen: expert_photo.png
Result: Talk show style video with expert image
```

### Product Announcement
```
Title: "Announcing New AI Tool"
Description: "We're excited to introduce our latest product..."
Green Screen: product_demo.mp4
Result: Product showcase with video animation
```

---

## ⏱️ Timing Guide

| Step | Duration |
|------|----------|
| Script generation | 10-20 sec |
| Voice generation | 30-60 sec |
| Video composition | 120-300 sec |
| **TOTAL** | **5-10 minutes** |

💡 **Tip**: Go grab coffee while video renders 😊

---

## 📂 File Locations

```
✅ Output video:    /videos/long/long_video_[timestamp].mp4
✅ Green screen:    /uploads/gs_[timestamp]_[filename]
✅ Metadata:        /videos/manifest.json
✅ Logs:            Console output when running app.py
```

---

## 🔍 Check Your Credentials

```bash
# View which platforms are configured
curl http://localhost:5002/config/credentials
```

**Expected Response**:
```json
{
  "facebook": "✅ Configured",
  "instagram": "✅ Configured", 
  "wordpress": "✅ Configured"
}
```

---

## ❓ Troubleshooting

### Video Not Generated?
1. Check console for errors
2. Verify title and description provided
3. Ensure sufficient disk space (5+ GB)
4. Check `/videos/long/` directory permissions

### Green Screen Not Showing?
1. Upload will be optional - video still generates
2. Check file format (PNG, JPG, MP4, MOV)
3. Verify format matches supported types

### Slow Generation?
1. This is normal - video composition is CPU intensive
2. Larger videos take 5-10+ minutes
3. Monitor CPU usage during generation

### Social Media Upload Failed?
1. Check credentials in `.env`
2. Verify API tokens are valid
3. Test with `/config/credentials` endpoint

---

## 🎮 Full API Reference

### Endpoints Available

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/test-long` | Generate test video |
| POST | `/generate-long` | Generate video |
| GET | `/config/credentials` | Check platforms |
| POST | `/facebook/post` | Post to Facebook |
| POST | `/instagram/post` | Post to Instagram |
| POST | `/wordpress/post` | Post to WordPress |
| GET | `/video/*` | Stream video |

---

## 📊 Default Settings

```python
# Green Screen
Position: Left side, 400×400 pixels
Y-offset: 180 pixels from top
Opacity: Full (100%)

# Ticker
Height: 70 pixels
Speed: Auto-adjust to video duration
Color: Red accent on dark background

# Side Text
Width: 400 pixels
Scroll time: ~12 seconds per scroll
Opacity: 70% semi-transparent

# Background
File: "long video background.mp4"
Fallback: "assets/bg.mp4"
Format: 1920×1080 @ 30fps
```

---

## 💡 Pro Tips

1. **Best Green Screen Size**: 400×400 image = Perfect (auto-scaled)
2. **Best Duration**: 8-12 minutes (AI script optimized for this)
3. **Best For**: News, announcements, educational content
4. **Reuse Content**: Save green screen images for consistency
5. **Batch Generation**: Can queue multiple requests

---

## 🚨 System Requirements

```
✅ CPU:        Modern multi-core processor  
✅ RAM:        4GB minimum, 8GB+ recommended
✅ Storage:    5+ GB free per video
✅ Network:    For social media posting
✅ Python:     3.9+ (already installed)
✅ FFmpeg:     Required (already installed)
```

---

## 🆘 Need Help?

1. Check [FEATURE_SUMMARY.md](FEATURE_SUMMARY.md) for detailed info
2. Review [LONG_VIDEO_ENHANCEMENTS.md](LONG_VIDEO_ENHANCEMENTS.md) for technical details
3. See [README.md](README.md) for full project info
4. Check console output for specific error messages

---

## 🎯 Next Steps

1. **Start Simple**:
   ```bash
   curl http://localhost:5002/test-long
   ```

2. **Try Custom Title**:
   ```bash
   curl -X POST http://localhost:5002/generate-long \
     -H "Content-Type: application/json" \
     -d '{"title": "Your Title Here", "description": "Your story"}'
   ```

3. **Add Green Screen**:
   - Prepare image (presenter, logo, graphic)
   - Use form data method with file upload

4. **Share to Social Media**:
   - Test one platform first (Facebook, Instagram, or WordPress)
   - Monitor upload progress

5. **Batch Automate** (Advanced):
   - Write script to generate multiple videos
   - Schedule posts to platforms
   - Monitor performance metrics

---

**You're all set! 🎬 Start creating professional long-form videos now!**

---

Version: 1.0 | Last Updated: Feb 24, 2026

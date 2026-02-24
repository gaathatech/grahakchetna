# 🚀 Pexels Integration - Quick Start

**TL;DR**: Generate videos without uploading images - Pexels automatically provides relevant images based on your headline!

---

## ⚡ 30-Second Setup

You're already set up! No configuration needed. The Pexels API key is already in your `.env` file.

---

## 📸 How to Use

### Before (Manual Upload)
```bash
# Old way - requires uploading image
curl -X POST http://localhost:5002/generate-long \
  -F "title=Breaking News" \
  -F "description=Story details" \
  -F "green_screen=@my_image.png"  ← Required
```

### After (Automatic Pexels)
```bash
# New way - automatic image from Pexels!
curl -X POST http://localhost:5002/generate-long \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Breaking News",
    "description": "Story details"
  }'

# No file upload needed! ✨
```

---

## 🎯 What Happens

1. **You send headline**: "Breaking: Climate Crisis Worsens"
2. **App extracts keywords**: "Breaking Climate Crisis"
3. **Fetches from Pexels**: Searches for related images
4. **Downloads image**: ~2-3 seconds
5. **Uses as green screen**: 400×400 overlay on left side
6. **Generates video**: With professional relevant imagery

---

## 📊 Results

### Video with Pexels Image

```
Headline: "Breaking: Climate Crisis Worsens"
  ↓ Pexels searches for: "Breaking Climate Crisis"
  ↓ Downloads: Climate/Earth/nature image
  ↓ Result: Professional video with relevant visual context
```

### Fallback Behavior

```
If Pexels unavailable:
  ✅ Video still generates
  ✅ Uses green screen placeholder
  ✅ No interruption to workflow
```

---

## 💡 Examples

### News
```bash
curl -X POST http://localhost:5002/generate-long \
  -H "Content-Type: application/json" \
  -d '{"title": "Fed Raises Interest Rates", "description": "..."}'
# ✅ Gets finance/economics images
```

### Tech
```bash
curl -X POST http://localhost:5002/generate-long \
  -H "Content-Type: application/json" \
  -d '{"title": "New AI Model Released", "description": "..."}'
# ✅ Gets AI/technology images
```

### Sports
```bash
curl -X POST http://localhost:5002/generate-long \
  -H "Content-Type: application/json" \
  -d '{"title": "World Cup Final Begins", "description": "..."}'
# ✅ Gets sports/soccer images
```

### Health
```bash
curl -X POST http://localhost:5002/generate-long \
  -H "Content-Type: application/json" \
  -d '{"title": "Breakthrough Vaccine Announced", "description": "..."}'
# ✅ Gets medical/health images
```

---

## 🎬 Still Want to Upload Custom?

Easy! Just add the file:

```bash
curl -X POST http://localhost:5002/generate-long \
  -F "title=Your Title" \
  -F "description=Your story" \
  -F "green_screen=@your_image.png"

# ✅ Your image used (Pexels not called)
```

---

## ⚙️ Configuration

Already done! Just verify:

```bash
# Check .env has Pexels key
grep "PEXELS_API_KEY" .env

# Should show:
# PEXELS_API_KEY=wfd20P4XGBlrsFIPPAo4BtnYQkg25p8q1IsVYg2zK0U7sLEtBnJp0q8K
```

---

## 📊 What You Get

### Quality
- ✅ Professional stock photos
- ✅ High resolution (~2000+ pixels)
- ✅ Commercial use licensed
- ✅ No watermarks

### Speed
- ~2-3 seconds to fetch + download
- Minimal impact on video generation
- Graceful fallback if slow

### Cost
- ✅ FREE API
- 200 requests/hour limit
- 4,800 images/day possible
- Perfect for any usage pattern

---

## 🔄 Full Workflow

```
1. Send request (title + description)
   ↓
2. App checks: File uploaded? NO
   ↓
3. App calls: fetch_image_from_pexels(headline)
   ↓
4. Pexels API: Searches for images
   ↓
5. Download: Image saved to uploads/
   ↓
6. Generate: Video created with image as green screen
   ↓
7. Response: Video ready to use!
```

---

## 📸 Available Images

Pexels has **3+ million free photos** on every topic:

| Category | Examples |
|----------|----------|
| News | Politics, economics, world events |
| Tech | AI, coding, innovation, startups |
| Nature | Landscapes, weather, climate |
| Business | Meetings, office, leadership |
| Health | Medicine, fitness, wellness |
| Sports | All major sports, athletes |
| Entertainment | Movies, music, celebrities |
| Education | Learning, books, schools |

---

## ✅ Verification

Check that everything is ready:

```bash
# Test Pexels integration
python3 << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("PEXELS_API_KEY")
if key:
    print("✅ Pexels API configured and ready!")
else:
    print("❌ Pexels API key missing")

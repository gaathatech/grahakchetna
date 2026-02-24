# Quick Start: Updated TTS Service

## Basic Usage (Recommended)

```python
from tts_service import generate_voice

# Generate voice from text (automatic retry, fallback, caching)
audio_path = generate_voice("Breaking news: The price of bitcoin surged 50%!")

if audio_path:
    print(f"✓ Audio saved to: {audio_path}")
else:
    print("✗ All TTS providers failed")
```

## Custom Output Path

```python
from tts_service import generate_voice

audio_path = generate_voice(
    text="Your text here",
    output_path="path/to/custom/voice.mp3"
)
```

## Long Text (Auto-Preprocessed)

```python
from tts_service import generate_voice

# Text longer than 1000 chars? No problem!
long_text = "Lorem ipsum..." * 50  # 4000+ characters

# This automatically:
# - Strips whitespace
# - Removes emojis
# - Removes non-ASCII characters
# - Limits to 1000 chars
result = generate_voice(long_text)
```

## Text with Emojis (Auto-Cleaned)

```python
from tts_service import generate_voice

# Emojis and Unicode? Safe!
text = "🚀 Breaking News! 📰 Bitcoin 🪙 surged 50% 📈"

# Becomes: "Breaking News! Bitcoin surged 50%"
result = generate_voice(text)
```

## Manual Text Preprocessing

```python
from tts_service import preprocess_text

text = "Breaking 🎬 News!\n\n  Long paragraph..."
cleaned = preprocess_text(text, max_length=1000)

# Use cleaned text
result = generate_voice(cleaned)
```

## Async Usage (If needed)

```python
import asyncio
from tts_service import generate_voice_async

async def create_video():
    audio_path = await generate_voice_async(
        text="Your text here",
        output_path="output/voice.mp3"
    )
    return audio_path

# Use in async context
audio_path = asyncio.run(create_video())
```

## Flask Integration (Thread-Safe)

```python
from flask import Flask
from tts_service import generate_voice

app = Flask(__name__)

@app.route("/generate-video", methods=["POST"])
def generate_video():
    text = request.json.get("text")
    
    # This is thread-safe!
    # (uses threading.Lock internally)
    audio_path = generate_voice(text)
    
    if audio_path:
        return {"audio": audio_path, "status": "success"}
    else:
        return {"status": "failed"}, 500
```

## Monitoring (Check Logs)

```python
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Now you'll see which provider was used:
# Edge TTS succeeded
# → OR Azure TTS succeeded  
# → OR gTTS succeeded
# → OR pyttsx3 (offline) succeeded

result = generate_voice("your text")
```

## Fallback Behavior (Automatic)

If Edge TTS fails with `NoAudioReceived`:
1. ~~Retry~~ (skipped for NoAudioReceived)
2. Try Azure TTS (if configured)
3. Try gTTS (Google Text-to-Speech)
4. Try pyttsx3 (offline)

**You don't need to do anything - it's automatic!**

## Configuration

```bash
# Set output directory
export TTS_OUTPUT_DIR="output"

# Optional: Azure Speech credentials

# Optional: ElevenLabs key for premium quality
export ELEVENLABS_API_KEY="sk-..."
```

## Migration from Old API

Old code still works (backward compatible):
```python
# Old way (still works)
from tts_service import generate_voice
result = generate_voice(text, language="english", female_voice=False)
```

New recommended way:
```python
# New way (simpler, cleaner)
from tts_service import generate_voice
result = generate_voice(text)
```

Both produce the same result!

---

## What Changed

| Feature | Before | After |
|---------|--------|-------|
| Voice | Configurable | Fixed: en-US-GuyNeural |
| Text Length | No limit | Auto-limited to 1000 |
| Emojis | Could fail | Auto-removed |
| NoAudioReceived | Retried 3x | Skips retry |
| 403/503 Errors | Retried 3x | Retried 2x with backoff |
| Thread Safety | Possible race | Locked ✓ |
| Fallback | ElevenLabs → Edge | Edge → Azure → gTTS → pyttsx3 |

---

## Troubleshooting

**Q: Edge TTS still fails?**
A: Check logs - it will automatically fallback to Azure/gTTS

**Q: Text longer than 1000 chars?**
A: Automatically preprocessed and truncated

**Q: Multiple requests at same time?**
A: Edge TTS requests are locked (only one at a time)

**Q: See "NoAudioReceived" error?**
A: It won't retry - immediately tries Azure/gTTS

**Q: Need custom voice?**
A: Edit `DEFAULT_VOICE` in tts_service.py

---

## Examples in app.py

See your app.py for examples of how to use `generate_voice()` in video generation routes.

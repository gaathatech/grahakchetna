import re
import asyncio
import logging
import os
import random
import hashlib
from typing import Optional
from pathlib import Path

import edge_tts

logger = logging.getLogger(__name__)

# ======================================
# CONFIG
# ======================================

VOICE_MAP = {
    "english": "en-US-GuyNeural",
    "hindi": "hi-IN-MadhurNeural",
    "gujarati": "gu-IN-NiranjanNeural",
}

VOICE_MAP_FEMALE = {
    "english": "en-US-AmberNeural",
    "hindi": "hi-IN-SwaraNeural",
    "gujarati": "gu-IN-DhwaniNeural",
}

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")

DEFAULT_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "output")
CACHE_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "cache")
DEFAULT_OUTPUT_PATH = os.path.join(DEFAULT_OUTPUT_DIR, "voice.mp3")

Path(DEFAULT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

SPEED_RATE = "-10%"  # Faster for exciting, energetic news delivery


# ======================================
# TEXT CLEANING + NEWS FORMATTER
# ======================================

def clean_text(text: str) -> str:
    text = re.sub(r"[^\w\s.,!?'\"-]", "", text)
    return text.strip()[:2000]


def format_news_script(text: str) -> str:
    """
    Adds dramatic pauses and exciting news pacing.
    Enhanced for energetic, breaking news delivery.
    """

    # Minimal pause after commas for faster pacing
    text = text.replace(",", ", ")

    # Strategic pauses for impact
    text = text.replace("! ", "! ... ")
    text = text.replace("? ", "? ... ")
    text = text.replace(". ", ". ")

    return text


# ======================================
# CACHE SYSTEM
# ======================================

def get_cache_path(text: str) -> str:
    hash_id = hashlib.md5(text.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{hash_id}.mp3")


# ======================================
# ELEVENLABS PRIMARY
# ======================================

async def _elevenlabs_tts(text: str, output_path: str):
    try:
        import requests

        if not ELEVEN_API_KEY:
            return False

        voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json"
        }

        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.65,
                "similarity_boost": 0.85,
                "style": 0.95,
                "use_speaker_boost": True
            }
        }

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
        else:
            logger.warning(f"ElevenLabs failed: {response.text}")
            return False

    except Exception as e:
        logger.warning(f"ElevenLabs error: {e}")
        return False


# ======================================
# EDGE SECONDARY
# ======================================

async def _edge_tts(text: str, output_path: str, language: str, female_voice: bool):
    voice_map = VOICE_MAP_FEMALE if female_voice else VOICE_MAP
    voice = voice_map.get(language.lower(), "en-US-GuyNeural")

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=SPEED_RATE,
    )

    await communicate.save(output_path)


# ======================================
# GTTS FALLBACK
# ======================================

async def _gtts_fallback(text: str, output_path: str, language: str):
    try:
        from gtts import gTTS

        lang_code = "en" if language.lower().startswith("eng") else language[:2]

        def _save():
            t = gTTS(text=text, lang=lang_code, slow=False)
            t.save(output_path)

        await asyncio.to_thread(_save)
        return True

    except Exception as e:
        logger.warning(f"gTTS failed: {e}")
        return False


# ======================================
# OFFLINE FALLBACK
# ======================================

async def _offline_fallback(text: str, output_path: str):
    try:
        import pyttsx3

        def _save():
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            engine.save_to_file(text, output_path)
            engine.runAndWait()

        await asyncio.to_thread(_save)
        return True

    except Exception as e:
        logger.warning(f"Offline TTS failed: {e}")
        return False


# ======================================
# MAIN FUNCTION
# ======================================

async def generate_voice_async(
    text: str,
    language: str = "english",
    output_path: Optional[str] = None,
    female_voice: bool = False,
    voice_model: Optional[str] = None,
) -> Optional[str]:

    if output_path is None:
        output_path = DEFAULT_OUTPUT_PATH

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    cleaned = clean_text(text)
    formatted = format_news_script(cleaned)

    if not formatted:
        logger.error("Text empty after cleaning")
        return None

    # ======================
    # CACHE CHECK
    # ======================
    cache_path = get_cache_path(formatted)

    if os.path.exists(cache_path):
        logger.info("Using cached audio")
        os.replace(cache_path, output_path)
        return output_path

    # ======================
    # Provider selection: respect `voice_model` if provided; otherwise use default order
    model = (voice_model or "auto").lower()

    async def _try_eleven():
        logger.info("Trying ElevenLabs")
        success = await _elevenlabs_tts(formatted, output_path)
        if success and os.path.exists(output_path):
            os.replace(output_path, cache_path)
            os.replace(cache_path, output_path)
            logger.info("✓ ElevenLabs success")
            return True
        return False

    async def _try_edge():
        logger.info("Trying Edge TTS")
        for attempt in range(3):
            try:
                await _edge_tts(formatted, output_path, language, female_voice)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    os.replace(output_path, cache_path)
                    os.replace(cache_path, output_path)
                    logger.info("✓ Edge success")
                    return True
            except Exception as e:
                logger.warning(f"Edge failed: {e}")
                backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
                await asyncio.sleep(backoff)
        return False

    async def _try_gtts():
        logger.info("Trying gTTS")
        success = await _gtts_fallback(formatted, output_path, language)
        return bool(success)

    async def _try_offline():
        logger.info("Trying Offline")
        success = await _offline_fallback(formatted, output_path)
        return bool(success)

    # Preferred flow based on selected model
    if model.startswith("eleven"):
        if await _try_eleven():
            return output_path
        # fallback chain
        if await _try_edge():
            return output_path
        if await _try_gtts():
            return output_path
        if await _try_offline():
            return output_path

    elif model.startswith("edge"):
        if await _try_edge():
            return output_path
        if await _try_eleven():
            return output_path
        if await _try_gtts():
            return output_path
        if await _try_offline():
            return output_path

    elif model.startswith("gtts"):
        if await _try_gtts():
            return output_path
        if await _try_edge():
            return output_path
        if await _try_eleven():
            return output_path
        if await _try_offline():
            return output_path

    else:
        # auto/default: Eleven -> Edge -> gTTS -> Offline
        if await _try_eleven():
            return output_path
        if await _try_edge():
            return output_path
        if await _try_gtts():
            return output_path
        if await _try_offline():
            return output_path

    logger.error("All TTS engines failed")
    return None


def generate_voice(
    text: str,
    language: str = "english",
    output_path: Optional[str] = None,
    female_voice: bool = False,
) -> Optional[str]:
    try:
        return asyncio.run(
            generate_voice_async(text, language, output_path, female_voice)
        )
    except RuntimeError:
        # If an event loop is already running (e.g., Flask/Gunicorn), use it
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            generate_voice_async(text, language, output_path, female_voice)
        )

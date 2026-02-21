import re
import asyncio
import logging
import os
import random
import hashlib
import time
from typing import Optional
from pathlib import Path
from collections import deque
from threading import Lock

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
# RATE LIMITING & CONCURRENCY CONTROL
# ======================================

# Limit concurrent edge-tts connections to 1 (prevent WebSocket rate limiting)
_EDGE_TTS_SEMAPHORE = None

def _get_semaphore():
    """Lazily create semaphore to avoid event loop issues at import time."""
    global _EDGE_TTS_SEMAPHORE
    if _EDGE_TTS_SEMAPHORE is None:
        _EDGE_TTS_SEMAPHORE = asyncio.Semaphore(1)
    return _EDGE_TTS_SEMAPHORE

# Throttle timing (minimum seconds between requests)
MIN_REQUEST_INTERVAL = 2.0
LAST_REQUEST_TIME = 0
REQUEST_TIME_LOCK = Lock()


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
# EDGE SECONDARY - WITH RATE LIMITING
# ======================================

async def _enforce_throttle():
    """Enforce minimum interval between requests to avoid rate limiting."""
    global LAST_REQUEST_TIME
    
    with REQUEST_TIME_LOCK:
        now = time.time()
        time_since_last = now - LAST_REQUEST_TIME
        
        if time_since_last < MIN_REQUEST_INTERVAL:
            sleep_time = MIN_REQUEST_INTERVAL - time_since_last
            logger.info(f"Throttling: waiting {sleep_time:.2f}s to avoid rate limit")
            await asyncio.sleep(sleep_time)
        
        LAST_REQUEST_TIME = time.time()


async def _edge_tts_with_retry(
    text: str, 
    output_path: str, 
    language: str, 
    female_voice: bool,
    max_retries: int = 3
):
    """
    Edge TTS with concurrency control and throttling.
    - Only 1 concurrent connection (SEMAPHORE)
    - Minimum interval between requests (THROTTLE)
    - Proper backoff strategy
    - User-Agent rotation
    """
    voice_map = VOICE_MAP_FEMALE if female_voice else VOICE_MAP
    voice = voice_map.get(language.lower(), "en-US-GuyNeural")
    semaphore = _get_semaphore()

    for attempt in range(max_retries):
        try:
            # Enforce rate limiting
            await _enforce_throttle()
            
            # Acquire semaphore (limit concurrent connections)
            async with semaphore:
                logger.info(f"Edge TTS attempt {attempt + 1}/{max_retries} - voice: {voice}")
                
                # Add random delay to prevent thundering herd
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=SPEED_RATE,
                )
                
                await communicate.save(output_path)
                
                # Verify file was created and has content
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    logger.info(f"✓ Edge TTS success on attempt {attempt + 1}")
                    return True
                else:
                    logger.warning(f"Edge TTS created invalid file on attempt {attempt + 1}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    raise Exception("Invalid output file")
                    
        except Exception as e:
            logger.warning(f"Edge TTS attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                backoff = (2 ** attempt) * 1.0 + random.uniform(0.5, 2.0)
                logger.info(f"Backing off for {backoff:.2f}s before retry...")
                await asyncio.sleep(backoff)
            
            if os.path.exists(output_path):
                os.remove(output_path)
    
    return False


async def _edge_tts(text: str, output_path: str, language: str, female_voice: bool):
    """Legacy wrapper for backward compatibility."""
    success = await _edge_tts_with_retry(text, output_path, language, female_voice)
    if not success:
        raise Exception("Edge TTS failed after all retries")


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
    # 1️⃣ ELEVENLABS
    # ======================
    logger.info("Trying ElevenLabs")
    success = await _elevenlabs_tts(formatted, output_path)
    if success and os.path.exists(output_path):
        os.replace(output_path, cache_path)
        os.replace(cache_path, output_path)
        logger.info("✓ ElevenLabs success")
        return output_path

    # ======================
    # 2️⃣ EDGE (with rate limiting)
    # ======================
    logger.info("Trying Edge TTS with concurrency control")
    
    try:
        success = await _edge_tts_with_retry(formatted, output_path, language, female_voice)
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            os.replace(output_path, cache_path)
            os.replace(cache_path, output_path)
            logger.info("✓ Edge success")
            return output_path
    except Exception as e:
        logger.warning(f"Edge TTS failed: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)

    # ======================
    # 3️⃣ gTTS
    # ======================
    logger.info("Trying gTTS")
    success = await _gtts_fallback(formatted, output_path, language)
    if success:
        return output_path

    # ======================
    # 4️⃣ Offline
    # ======================
    logger.info("Trying Offline")
    success = await _offline_fallback(formatted, output_path)
    if success:
        return output_path

    logger.error("All TTS engines failed")
    return None


def _get_or_create_event_loop():
    """
    Get existing event loop or create a new one.
    Handles Flask and other frameworks that may have event loop issues.
    """
    try:
        loop = asyncio.get_running_loop()
        # If we're already in an async context, return None to signal we should use the current loop
        return None
    except RuntimeError:
        pass
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def generate_voice(
    text: str,
    language: str = "english",
    output_path: Optional[str] = None,
    female_voice: bool = False,
) -> Optional[str]:
    """
    Thread-safe wrapper that runs async TTS generation.
    Handles Flask context and event loop management properly.
    """
    try:
        # Check if there's already a running loop (unlikely in Flask request context)
        try:
            asyncio.get_running_loop()
            # If we get here, we're in an async context - this shouldn't happen in Flask
            logger.warning("Already in async context, this may cause issues")
            return asyncio.run(
                generate_voice_async(text, language, output_path, female_voice)
            )
        except RuntimeError:
            # No running loop, proceed normally
            pass
        
        loop = _get_or_create_event_loop()
        if loop is None:
            # Already have a running loop
            return asyncio.run(
                generate_voice_async(text, language, output_path, female_voice)
            )
        
        # Use the event loop we got (or created)
        return loop.run_until_complete(
            generate_voice_async(text, language, output_path, female_voice)
        )
        
    except Exception as e:
        logger.error(f"Failed to generate voice: {e}")
        return None

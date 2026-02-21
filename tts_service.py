import re
import asyncio
import logging
import os
import hashlib
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ======================================
# CONFIG
# ======================================

DEFAULT_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "output")
CACHE_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "cache")
DEFAULT_OUTPUT_PATH = os.path.join(DEFAULT_OUTPUT_DIR, "voice.mp3")

Path(DEFAULT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

SPEED_RATE = "-5%"  # Slight speedup for energetic delivery (was -10%, reduced for natural pacing)


# ======================================
# TEXT CLEANING + NEWS FORMATTER
# ======================================

def clean_text(text: str) -> str:
    text = re.sub(r"[^\w\s.,!?'\"-]", "", text)
    return text.strip()[:2000]


def format_news_script(text: str) -> str:
    """
    Adds natural pauses, emphasis, and emotional pacing for exciting news delivery.
    Makes the speech sound natural and engaging, not robotic.
    """
    
    # Start with natural sentence breaks
    # Short pause after commas
    text = text.replace(",", ", ")
    
    # Longer dramatic pauses for punctuation
    text = text.replace("! ", "!. ")  # Pause for emphasis after exclamation
    text = text.replace("? ", "? ")   # Natural pause after questions
    text = text.replace(". ", ". ")   # Regular pause after periods
    
    # Add breathing room at paragraph breaks or section markers
    text = text.replace("\n\n", ". ")  # Paragraph breaks become pauses
    text = text.replace("\n", " ")     # Line breaks become spaces
    
    # Emphasize key news words with strategic punctuation
    # (Some TTS engines recognize emphasis patterns)
    keywords = ["breaking", "urgent", "just", "now", "today", "alert", "confirmed", "latest"]
    for kw in keywords:
        # Add slight emphasis markup (most TTS ignores, but helps readability)
        text = text.replace(f" {kw} ", f" {kw.upper()} ")
    
    # Add strategic pauses before important details
    text = text.replace("According to ", "According to. ")
    text = text.replace("Authorities ", "Authorities. ")
    text = text.replace("Officials ", "Officials. ")
    text = text.replace("Reports ", "Reports indicate. ")
    
    # Add natural "bridge" phrases for smoother delivery
    text = text.replace("  ", " ")  # Remove double spaces
    
    return text


# ======================================
# CACHE SYSTEM
# ======================================

def get_cache_path(text: str) -> str:
    hash_id = hashlib.md5(text.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{hash_id}.mp3")


# Note: ElevenLabs and Edge TTS removed. Using gTTS and offline fallback only.


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
    voice_provider: Optional[str] = None,
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
    # Simple fallback: gTTS -> Offline
    # ======================
    # Note: ElevenLabs and Edge removed; using only gTTS and offline pyttsx3

    async def _try_gtts():
        logger.info("Trying gTTS")
        success = await _gtts_fallback(formatted, output_path, language)
        if success and os.path.exists(output_path):
            os.replace(output_path, cache_path)
            os.replace(cache_path, output_path)
            logger.info("✓ gTTS success")
            return True
        return False

    async def _try_offline():
        logger.info("Trying Offline (pyttsx3)")
        success = await _offline_fallback(formatted, output_path)
        if success and os.path.exists(output_path):
            os.replace(output_path, cache_path)
            os.replace(cache_path, output_path)
            logger.info("✓ Offline success")
            return True
        return False

    # Simple flow: gTTS -> Offline
    # (ElevenLabs and Edge removed)
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
    voice_model: Optional[str] = None,
    voice_provider: Optional[str] = None,
) -> Optional[str]:
    try:
        return asyncio.run(
            generate_voice_async(text, language, output_path, female_voice, voice_model, voice_provider)
        )
    except RuntimeError:
        # If an event loop is already running (e.g., Flask/Gunicorn), use it
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(
            generate_voice_async(text, language, output_path, female_voice, voice_model, voice_provider)
        )

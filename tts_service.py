import re
import asyncio
import logging
import os
import hashlib
import time
import unicodedata
from typing import Optional, Tuple
from pathlib import Path
from threading import Lock

import edge_tts

logger = logging.getLogger(__name__)

# ======================================
# CONFIG
# ======================================

# Default voice - production tested and reliable
DEFAULT_VOICE = "en-US-AmberNeural"

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
AZURE_API_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")

DEFAULT_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "output")
CACHE_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "cache")
DEFAULT_OUTPUT_PATH = os.path.join(DEFAULT_OUTPUT_DIR, "voice.mp3")

Path(DEFAULT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

SPEED_RATE = "-10%"  # Faster for exciting, energetic news delivery

# ======================================
# THREAD-SAFE LOCKING FOR EDGE TTS
# ======================================

# Ensure only ONE Edge TTS request at a time (prevents parallel calls)
EDGE_TTS_LOCK = Lock()

# For async contexts, we need an asyncio.Lock
_ASYNC_EDGE_TTS_LOCK = None

def _get_async_lock():
    """Get or create asyncio.Lock for async Edge TTS calls."""
    global _ASYNC_EDGE_TTS_LOCK
    if _ASYNC_EDGE_TTS_LOCK is None:
        try:
            loop = asyncio.get_running_loop()
            _ASYNC_EDGE_TTS_LOCK = asyncio.Lock()
        except RuntimeError:
            # No running loop, will be created later
            pass
    return _ASYNC_EDGE_TTS_LOCK


# ======================================
# TEXT PREPROCESSING
# ======================================

def _remove_emojis_and_non_ascii(text: str) -> str:
    """
    Remove emojis and non-ASCII characters while preserving basic punctuation.
    Keeps: letters, numbers, basic punctuation (.,!?'-"), spaces
    """
    cleaned = []
    for char in text:
        # Check if character is ASCII or allowed punctuation
        if ord(char) < 128:  # ASCII range
            cleaned.append(char)
        elif char in ' ':  # Keep spaces for unicode
            cleaned.append(char)
        # Skip emojis and non-ASCII characters
    
    return ''.join(cleaned)


def _collapse_whitespace(text: str) -> str:
    """Collapse multiple spaces, tabs, newlines into single space."""
    # Replace newlines and tabs with spaces
    text = re.sub(r'[\n\r\t]+', ' ', text)
    # Collapse multiple spaces into single space
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def preprocess_text(text: str, max_length: int = 1000) -> str:
    """
    Preprocess text for TTS:
    1. Strip leading/trailing whitespace
    2. Remove emojis and non-ASCII characters
    3. Collapse multiple spaces
    4. Limit to max_length characters
    
    Args:
        text: Raw text input
        max_length: Maximum allowed text length (default 1000)
    
    Returns:
        Cleaned and preprocessed text
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Step 1: Strip whitespace
    text = text.strip()
    
    # Step 2: Remove emojis and non-ASCII characters
    text = _remove_emojis_and_non_ascii(text)
    
    # Step 3: Collapse multiple spaces
    text = _collapse_whitespace(text)
    
    # Step 4: Limit to max_length
    if len(text) > max_length:
        # Truncate at word boundary if possible
        text = text[:max_length]
        # Try to cut at last space to avoid cutting mid-word
        last_space = text.rfind(' ')
        if last_space > max_length * 0.8:  # Only if space is reasonably close
            text = text[:last_space]
    
    return text.strip()


# ======================================
# CACHE SYSTEM
# ======================================

def get_cache_path(text: str) -> str:
    """Generate cache path based on text hash."""
    hash_id = hashlib.md5(text.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{hash_id}.mp3")


# ======================================
# ERROR DETECTION HELPERS
# ======================================

def _is_retryable_error(error: Exception) -> bool:
    """
    Determine if an Edge TTS error is retryable.
    Only retry on specific HTTP errors (403 Forbidden, 503 Service Unavailable).
    Do NOT retry NoAudioReceived - proceed to fallback immediately.
    
    Args:
        error: The exception that occurred
    
    Returns:
        True if error is retryable, False otherwise
    """
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # NoAudioReceived is NOT retryable - skip immediately to fallback
    if "noaudioreceived" in error_str or "no audio received" in error_str:
        logger.warning("NoAudioReceived error detected - skipping retry, jumping to fallback")
        return False
    
    # Only retry on HTTP 403 or 503
    if "403" in error_str or "forbidden" in error_str:
        logger.info("403 Forbidden error detected - will retry")
        return True
    
    if "503" in error_str or "service unavailable" in error_str:
        logger.info("503 Service Unavailable error detected - will retry")
        return True
    
    # All other errors are not retryable
    logger.info(f"Non-retryable error ({error_type}) - proceeding to fallback")
    return False


# ======================================
# AZURE TTS FALLBACK
# ======================================

async def _azure_tts(text: str, output_path: str) -> bool:
    """
    Azure Speech Synthesis fallback.
    
    Args:
        text: Text to synthesize
        output_path: Path to save MP3 file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not AZURE_API_KEY:
            logger.info("Azure TTS: API key not configured, skipping")
            return False
        
        import azure.cognitiveservices.speech as speechsdk
        
        logger.info(f"Trying Azure TTS (region: {AZURE_REGION})")
        
        speech_config = speechsdk.SpeechConfig(
            subscription=AZURE_API_KEY,
            region=AZURE_REGION
        )
        
        # Use same voice family as Edge TTS for consistency
        speech_config.speech_synthesis_voice_name = DEFAULT_VOICE
        
        # Save to file
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        result = synthesizer.speak_text(text)
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info("✓ Azure TTS succeeded")
            return True
        else:
            logger.warning(f"Azure TTS synthesis not completed: {result.reason}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
            
    except ImportError:
        logger.warning("Azure SDK not installed (azure-cognitiveservices-speech)")
        return False
    except Exception as e:
        logger.warning(f"Azure TTS failed: {type(e).__name__}: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False



# ======================================
# ELEVENLABS TTS (PRIMARY FALLBACK)
# ======================================

async def _elevenlabs_tts(text: str, output_path: str) -> bool:
    """
    ElevenLabs API - Premium quality voice.
    Only used as fallback if configured.
    
    Args:
        text: Text to synthesize
        output_path: Path to save MP3 file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not ELEVEN_API_KEY:
            logger.info("ElevenLabs: API key not configured, skipping")
            return False
        
        import requests
        
        logger.info("Trying ElevenLabs TTS")
        
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
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            logger.info("✓ ElevenLabs TTS succeeded")
            return True
        else:
            logger.warning(f"ElevenLabs failed (HTTP {response.status_code}): {response.text}")
            return False
            
    except ImportError:
        logger.warning("requests library not available for ElevenLabs")
        return False
    except Exception as e:
        logger.warning(f"ElevenLabs error: {type(e).__name__}: {e}")
        return False


# ======================================
# EDGE TTS WITH SMART RETRY LOGIC
# ======================================

async def _edge_tts_with_smart_retry(
    text: str,
    output_path: str,
    max_attempts: int = 2
) -> bool:
    """
    Edge TTS with intelligent retry logic:
    - Retries ONLY on 403 (Forbidden) or 503 (Service Unavailable)
    - Does NOT retry on NoAudioReceived error
    - Uses exponential backoff (2 seconds base) for retryable errors
    - Thread-safe: ensures only one Edge TTS request at a time
    
    Args:
        text: Preprocessed text to synthesize
        output_path: Path to save MP3 file
        max_attempts: Maximum retry attempts (default 2)
    
    Returns:
        True if successful, False otherwise (caller should try fallback)
    """
    
    # Acquire async lock to prevent parallel Edge TTS requests
    try:
        loop = asyncio.get_running_loop()
        async_lock = asyncio.Lock()
    except RuntimeError:
        async_lock = None
    
    async def _do_edge_tts():
        try:
            logger.info(f"Edge TTS: Calling Communicate with voice={DEFAULT_VOICE}, text_len={len(text)}")
            
            communicate = edge_tts.Communicate(
                text=text,
                voice=DEFAULT_VOICE,
                rate=SPEED_RATE,
            )
            
            await communicate.save(output_path)
            
            # Verify file was created and has content
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"✓ Edge TTS audio file created successfully ({os.path.getsize(output_path)} bytes)")
                return True
            else:
                logger.warning("Edge TTS created invalid or empty file")
                if os.path.exists(output_path):
                    os.remove(output_path)
                raise Exception("Invalid output file")
                
        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Edge TTS attempt {attempt}/{max_attempts}")
            
            # If we have an async lock, use it
            if async_lock:
                async with async_lock:
                    success = await _do_edge_tts()
            else:
                success = await _do_edge_tts()
            
            if success:
                return True
                
        except Exception as e:
            error_str = str(e)
            logger.warning(f"Edge TTS attempt {attempt} failed: {type(e).__name__}: {error_str}")
            
            # Check if error is retryable
            is_retryable = _is_retryable_error(e)
            
            if not is_retryable:
                # Non-retryable error (including NoAudioReceived) - stop here
                logger.info(f"Non-retryable error detected, stopping Edge TTS attempts")
                return False
            
            # Retryable error - apply exponential backoff if more attempts remain
            if attempt < max_attempts:
                backoff_seconds = (2 ** (attempt - 1)) * 2  # 2, 4, 8, etc.
                logger.info(f"Retryable error - backing off {backoff_seconds}s before retry {attempt + 1}")
                await asyncio.sleep(backoff_seconds)
            else:
                logger.info(f"Maximum Edge TTS attempts reached, proceeding to fallback")
                return False
    
    return False


# ======================================
# GTTS FALLBACK
# ======================================

async def _gtts_tts(text: str, output_path: str, language: str = "en") -> bool:
    """
    gTTS fallback - free, reliable TTS service.
    
    Args:
        text: Text to synthesize
        output_path: Path to save MP3 file
        language: Language code (default "en")
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from gtts import gTTS
        
        logger.info(f"Trying gTTS with language={language}")
        
        def _save():
            tts = gTTS(text=text, lang=language, slow=False)
            tts.save(output_path)
        
        # Run gTTS in thread pool to avoid blocking
        await asyncio.to_thread(_save)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            logger.info(f"✓ gTTS succeeded ({os.path.getsize(output_path)} bytes)")
            return True
        else:
            logger.warning("gTTS created invalid or empty file")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
            
    except ImportError:
        logger.warning("gtts library not installed")
        return False
    except Exception as e:
        logger.warning(f"gTTS failed: {type(e).__name__}: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


# ======================================
# PYTTSX3 OFFLINE FALLBACK
# ======================================

async def _pyttsx3_tts(text: str, output_path: str) -> bool:
    """
    pyttsx3 offline TTS - last resort fallback.
    Works without internet connection.
    
    Args:
        text: Text to synthesize
        output_path: Path to save MP3 file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        import pyttsx3
        
        logger.info("Trying pyttsx3 offline TTS")
        
        def _save():
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)  # Slightly faster speed
            engine.save_to_file(text, output_path)
            engine.runAndWait()
        
        await asyncio.to_thread(_save)
        
        if os.path.exists(output_path):
            logger.info(f"✓ pyttsx3 succeeded ({os.path.getsize(output_path)} bytes)")
            return True
        else:
            logger.warning("pyttsx3 did not create output file")
            return False
            
    except ImportError:
        logger.warning("pyttsx3 library not installed")
        return False
    except Exception as e:
        logger.warning(f"pyttsx3 failed: {type(e).__name__}: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False



# ======================================
# MAIN ASYNC FUNCTION - FALLBACK ORDER
# ======================================

async def generate_voice_async(
    text: str,
    output_path: Optional[str] = None,
) -> Optional[str]:
    """
    Generate voice audio with comprehensive fallback strategy.
    
    Fallback order:
    1. Edge TTS (max 2 attempts, smart retry logic)
    2. Azure TTS (1 attempt, if configured)
    3. gTTS (free service fallback)
    4. pyttsx3 (offline fallback)
    
    Args:
        text: Text to convert to speech
        output_path: Path to save MP3 file (uses default if not specified)
    
    Returns:
        Path to generated audio file, or None if all providers failed
    """
    
    if output_path is None:
        output_path = DEFAULT_OUTPUT_PATH
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # =========================================
    # STEP 1: Preprocess input text
    # =========================================
    logger.info(f"Input text length: {len(text)} characters")
    
    processed_text = preprocess_text(text, max_length=1000)
    
    if not processed_text:
        logger.error("Text empty after preprocessing")
        return None
    
    logger.info(f"Processed text length: {len(processed_text)} characters")
    logger.debug(f"Processed text preview: {processed_text[:100]}...")
    
    # =========================================
    # STEP 2: Check cache
    # =========================================
    cache_path = get_cache_path(processed_text)
    
    if os.path.exists(cache_path):
        logger.info(f"✓ Using cached audio: {cache_path}")
        # Copy cache to output path if different
        if cache_path != output_path:
            os.replace(cache_path, output_path)
        return output_path
    
    # =========================================
    # STEP 3: Try Edge TTS (2 attempts max)
    # =========================================
    logger.info("=" * 50)
    logger.info("Provider 1: Edge TTS")
    logger.info("=" * 50)
    
    success = await _edge_tts_with_smart_retry(processed_text, output_path, max_attempts=2)
    
    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        logger.info("✓✓✓ SUCCESS: Edge TTS ✓✓✓")
        # Cache the result
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        os.replace(output_path, cache_path)
        os.replace(cache_path, output_path)
        return output_path
    
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # =========================================
    # STEP 4: Try Azure TTS (1 attempt)
    # =========================================
    logger.info("=" * 50)
    logger.info("Provider 2: Azure TTS")
    logger.info("=" * 50)
    
    success = await _azure_tts(processed_text, output_path)
    
    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        logger.info("✓✓✓ SUCCESS: Azure TTS ✓✓✓")
        # Cache the result
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        os.replace(output_path, cache_path)
        os.replace(cache_path, output_path)
        return output_path
    
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # =========================================
    # STEP 5: Try gTTS (free fallback)
    # =========================================
    logger.info("=" * 50)
    logger.info("Provider 3: gTTS (Google Text-to-Speech)")
    logger.info("=" * 50)
    
    success = await _gtts_tts(processed_text, output_path, language="en")
    
    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        logger.info("✓✓✓ SUCCESS: gTTS ✓✓✓")
        # Cache the result
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        os.replace(output_path, cache_path)
        os.replace(cache_path, output_path)
        return output_path
    
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # =========================================
    # STEP 6: Try pyttsx3 offline (last resort)
    # =========================================
    logger.info("=" * 50)
    logger.info("Provider 4: pyttsx3 (Offline)")
    logger.info("=" * 50)
    
    success = await _pyttsx3_tts(processed_text, output_path)
    
    if success and os.path.exists(output_path):
        logger.info("✓✓✓ SUCCESS: pyttsx3 (Offline) ✓✓✓")
        # Don't cache offline TTS as formats may vary
        return output_path
    
    # =========================================
    # ALL PROVIDERS FAILED
    # =========================================
    logger.error("✗✗✗ FAILURE: All TTS providers exhausted ✗✗✗")
    
    if os.path.exists(output_path):
        os.remove(output_path)
    
    return None


# ======================================
# SYNCHRONOUS WRAPPER (FLASK COMPATIBILITY)
# ======================================

def _get_or_create_event_loop():
    """
    Safely get or create event loop for Flask/threading context.
    Handles edge cases where event loops exist but are closed.
    """
    try:
        # Check if we're already in an async context
        loop = asyncio.get_running_loop()
        return loop
    except RuntimeError:
        pass
    
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            return loop
    except RuntimeError:
        pass
    
    # Create new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def generate_voice(
    text: str,
    output_path: Optional[str] = None,
    **kwargs
) -> Optional[str]:
    """
    Synchronous wrapper for generate_voice_async.
    Thread-safe for use in Flask and other sync frameworks.
    
    Ensures only ONE Edge TTS request happens at a time using threading.Lock.
    
    Args:
        text: Text to convert to speech
        output_path: Path to save MP3 file (uses default if not specified)
        **kwargs: Ignored parameters for backward compatibility
                 (language, female_voice, voice_model, voice_provider, etc.)
    
    Returns:
        Path to generated audio file, or None if all providers failed
    """
    
    # Log ignored parameters for debugging (production info level)
    if kwargs:
        ignored_params = [f"{k}={v}" for k, v in kwargs.items()]
        logger.info(f"Ignoring parameters (using en-US-AmberNeural): {', '.join(ignored_params)}")
    
    # Thread-safe lock: prevent parallel Edge TTS calls
    with EDGE_TTS_LOCK:
        logger.info("Acquired EDGE_TTS_LOCK - starting TTS generation")
        
        try:
            loop = _get_or_create_event_loop()
            result = loop.run_until_complete(
                generate_voice_async(text, output_path)
            )
            return result
            
        except Exception as e:
            logger.error(f"TTS generation failed: {type(e).__name__}: {e}", exc_info=True)
            return None
        finally:
            logger.info("Released EDGE_TTS_LOCK")


# ======================================
# LEGACY COMPATIBILITY FUNCTIONS
# ======================================

async def generate_voice_async_legacy(
    text: str,
    language: str = "english",
    output_path: Optional[str] = None,
    female_voice: bool = False,
) -> Optional[str]:
    """
    Legacy wrapper for backward compatibility.
    Ignores language and female_voice parameters (now uses en-US-AmberNeural).
    """
    logger.info(f"Legacy function called with language={language}, female_voice={female_voice}")
    logger.info("Using default voice: en-US-AmberNeural")
    return await generate_voice_async(text, output_path)


def generate_voice_legacy(
    text: str,
    language: str = "english",
    output_path: Optional[str] = None,
    female_voice: bool = False,
) -> Optional[str]:
    """
    Legacy wrapper for backward compatibility.
    Ignores language and female_voice parameters (now uses en-US-AmberNeural).
    """
    logger.info(f"Legacy function called with language={language}, female_voice={female_voice}")
    return generate_voice(text, output_path)

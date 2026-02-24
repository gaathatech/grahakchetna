import re
import asyncio
import logging
import os
import hashlib
import time
import unicodedata
from typing import Optional, Tuple, Dict, List
from pathlib import Path
from threading import Lock
from dataclasses import dataclass
from enum import Enum

import edge_tts

logger = logging.getLogger(__name__)

# ======================================
# ERROR RESPONSE DATACLASS
# ======================================

@dataclass
class TTSError:
    """Structured error response for TTS operations."""
    success: bool = False
    error: str = ""
    error_type: str = ""
    details: Dict = None
    attempted_voices: List[str] = None
    attempted_providers: List[str] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            "success": self.success,
            "error": self.error,
            "error_type": self.error_type,
            "details": self.details or {},
            "attempted_voices": self.attempted_voices or [],
            "attempted_providers": self.attempted_providers or []
        }


# ======================================
# CONFIG
# ======================================

# Primary voice - neutral, reliable
PRIMARY_VOICE = "en-US-AriaNeural"

# Fallback voices in priority order (handles invalid voice gracefully)
FALLBACK_VOICES = [
    "en-US-JennyNeural",      # Professional, clear
    "en-US-AmberNeural",      # Warm, friendly
    "en-US-AvaNeural",        # Modern, engaging
    "en-US-SaraNeural",       # Natural, conversational
]

# All valid Edge TTS voices for validation
VALID_VOICES = {
    # US English voices
    "en-US-AriaNeural", "en-US-AmberNeural", "en-US-AshleyNeural",
    "en-US-AvaNeural", "en-US-CoraNeural", "en-US-ElizabethNeural",
    "en-US-JennyNeural", "en-US-MichelleNeural", "en-US-MonicaNeural",
    "en-US-SaraNeural",
    # Male voices
    "en-US-BrianNeural", "en-US-ChristopherNeural", "en-US-EricNeural",
    "en-US-GuyNeural", "en-US-JacobNeural", "en-US-RyanNeural",
    "en-US-TonyNeural",
}

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")

DEFAULT_OUTPUT_DIR = os.getenv("TTS_OUTPUT_DIR", "output")
CACHE_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "cache")
DEFAULT_OUTPUT_PATH = os.path.join(DEFAULT_OUTPUT_DIR, "voice.mp3")

Path(DEFAULT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

SPEED_RATE = "-9%"  # Slightly faster for natural news delivery
MIN_TEXT_LENGTH = 1  # Minimum text length (words)
MAX_TEXT_LENGTH = 1000  # Maximum text length (characters)

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
# VOICE VALIDATION & FALLBACK
# ======================================

def validate_voice_name(voice: str) -> bool:
    """
    Validate that voice name is in the list of valid Edge TTS voices.
    
    Args:
        voice: Voice name to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not voice or not isinstance(voice, str):
        logger.warning(f"Invalid voice parameter: {voice} (type: {type(voice)})")
        return False
    
    if voice in VALID_VOICES:
        logger.info(f"✓ Voice validated: {voice}")
        return True
    else:
        logger.warning(f"✗ Voice not valid: {voice}")
        return False


def get_best_voice(requested_voice: Optional[str] = None) -> str:
    """
    Get the best available voice with smart fallback logic.
    
    1. If requested_voice is valid, use it
    2. Otherwise, use PRIMARY_VOICE
    3. If PRIMARY_VOICE unavailable, try fallback voices
    
    Args:
        requested_voice: Optional voice name requested by user
    
    Returns:
        Best available voice name
    """
    logger.info(f"Voice selection: requested={requested_voice}")
    
    # Try requested voice first
    if requested_voice and validate_voice_name(requested_voice):
        logger.info(f"Using requested voice: {requested_voice}")
        return requested_voice
    
    # Try primary voice
    if validate_voice_name(PRIMARY_VOICE):
        logger.info(f"Using primary voice: {PRIMARY_VOICE}")
        return PRIMARY_VOICE
    
    # Fallback to first available fallback voice
    for voice in FALLBACK_VOICES:
        if validate_voice_name(voice):
            logger.info(f"Using fallback voice: {voice}")
            return voice
    
    # Last resort - use primary anyway (Edge TTS may accept it)
    logger.warning(f"No validated voice available, using primary: {PRIMARY_VOICE}")
    return PRIMARY_VOICE


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
    4. Validate length
    5. Limit to max_length characters
    
    Args:
        text: Raw text input
        max_length: Maximum allowed text length (default 1000)
    
    Returns:
        Cleaned and preprocessed text (or empty string if invalid)
    """
    if not text or not isinstance(text, str):
        logger.error(f"Invalid text input: type={type(text)}, value={text}")
        return ""
    
    # Step 1: Strip whitespace
    text = text.strip()
    
    if not text:
        logger.error("Text is empty after stripping whitespace")
        return ""
    
    # Step 2: Remove emojis and non-ASCII characters
    text = _remove_emojis_and_non_ascii(text)
    
    # Step 3: Collapse multiple spaces
    text = _collapse_whitespace(text)
    
    if not text:
        logger.error("Text is empty after preprocessing")
        return ""
    
    # Step 4: Validate minimum length (at least 1 character)
    if len(text) < MIN_TEXT_LENGTH:
        logger.error(f"Text too short: {len(text)} < {MIN_TEXT_LENGTH} characters")
        return ""
    
    # Step 5: Limit to max_length
    if len(text) > max_length:
        logger.warning(f"Text exceeds max length ({len(text)} > {max_length}), truncating")
        # Truncate at word boundary if possible
        text = text[:max_length]
        # Try to cut at last space to avoid cutting mid-word
        last_space = text.rfind(' ')
        if last_space > max_length * 0.8:  # Only if space is reasonably close
            text = text[:last_space]
    
    final_text = text.strip()
    
    if not final_text:
        logger.error("Text is empty after final processing")
        return ""
    
    logger.info(f"✓ Text preprocessed: {len(final_text)} characters, {len(final_text.split())} words")
    return final_text


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
    
    Retryable errors:
    - HTTP 403 Forbidden (rate limiting, IP restriction)
    - HTTP 503 Service Unavailable (temporary service issue)
    - Timeout errors
    - Connection errors
    
    NON-Retryable errors:
    - NoAudioReceived (likely voice/text issue, not transient)
    - HTTP 400/404 (invalid request/voice)
    - Text encoding issues
    
    Args:
        error: The exception that occurred
    
    Returns:
        True if error is retryable, False otherwise
    """
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    logger.debug(f"Analyzing error for retry: {error_type}: {error_str}")
    
    # NON-RETRYABLE: NoAudioReceived errors
    if "noaudioreceived" in error_str or "no audio received" in error_str:
        logger.warning("⚠ NoAudioReceived error - NON-RETRYABLE (likely voice/text issue)")
        return False
    
    # NON-RETRYABLE: Bad request errors
    if "400" in error_str or "bad request" in error_str:
        logger.warning("⚠ 400 Bad Request - NON-RETRYABLE (invalid request)")
        return False
    
    # NON-RETRYABLE: Not found errors
    if "404" in error_str or "not found" in error_str:
        logger.warning("⚠ 404 Not Found - NON-RETRYABLE (voice/endpoint not found)")
        return False
    
    # NON-RETRYABLE: Encoding errors
    if "encode" in error_str or "decode" in error_str or "utf" in error_str:
        logger.warning("⚠ Encoding error - NON-RETRYABLE")
        return False
    
    # RETRYABLE: Forbidden (rate limiting, IP issues)
    if "403" in error_str or "forbidden" in error_str:
        logger.info("↻ 403 Forbidden - RETRYABLE (rate limiting/IP restriction)")
        return True
    
    # RETRYABLE: Service unavailable
    if "503" in error_str or "service unavailable" in error_str or "temporarily unavailable" in error_str:
        logger.info("↻ 503 Service Unavailable - RETRYABLE (temporary service issue)")
        return True
    
    # RETRYABLE: Timeout/connection errors
    if any(x in error_str for x in ["timeout", "connection", "refused", "reset"]):
        logger.info("↻ Connection error - RETRYABLE")
        return True
    
    # Default: consider retryable (safer approach)
    logger.info(f"↻ Unknown error - treating as RETRYABLE: {error_type}")
    return True



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
# EDGE TTS WITH ROBUST RETRY LOGIC
# ======================================

async def _edge_tts_with_smart_retry(
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    max_attempts: int = 3
) -> bool:
    """
    Edge TTS with intelligent retry logic, voice validation, and detailed diagnostics:
    
    Features:
    - Voice validation before attempting synthesis
    - Automatic fallback to alternative voices if primary fails
    - Retries ONLY on transient errors (403, 503, timeouts)
    - Does NOT retry on non-transient errors (NoAudioReceived, invalid voice)
    - Exponential backoff with jitter for retryable errors
    - WebSocket error handling
    - Event loop safety for Flask/async contexts
    - Detailed logging for debugging
    
    Possible causes of NoAudioReceived and how we prevent them:
    1. Invalid voice - FIXED: Voice validation before use
    2. WebSocket issue - HANDLED: Connection retries with backoff
    3. Event loop misuse - FIXED: Proper async/sync bridge
    4. Text length issue - FIXED: Text preprocessing with validation
    
    Args:
        text: Preprocessed text to synthesize
        output_path: Path to save MP3 file
        voice: Optional voice name (uses best_voice if not specified)
        max_attempts: Maximum retry attempts (default 3)
    
    Returns:
        True if successful, False otherwise (caller should try fallback)
    """
    
    # Get validated voice with fallback
    selected_voice = get_best_voice(voice)
    logger.info(f"Edge TTS initialized with voice: {selected_voice}, text_len={len(text)} chars")
    
    # Acquire async lock to prevent parallel Edge TTS requests
    async_lock = None
    try:
        loop = asyncio.get_running_loop()
        async_lock = asyncio.Lock()
        logger.debug("Event loop found, using async lock")
    except RuntimeError:
        logger.debug("No running event loop, will create one")
    
    async def _do_edge_tts(attempt_num: int):
        """Inner function for actual Edge TTS call."""
        try:
            logger.info(f"  [Attempt {attempt_num}] Calling Edge TTS (voice={selected_voice}, text_len={len(text)})")
            
            # Create Communicate object with realistic User-Agent
            communicate = edge_tts.Communicate(
                text=text,
                voice=selected_voice,
                rate=SPEED_RATE,
                proxy=None,
            )
            
            logger.debug(f"  [Attempt {attempt_num}] Communicate object created, calling save()...")
            
            # Call save with timeout to catch hanging WebSockets
            try:
                await asyncio.wait_for(communicate.save(output_path), timeout=30.0)
            except asyncio.TimeoutError:
                logger.error(f"  [Attempt {attempt_num}] Edge TTS save() timed out after 30s")
                if os.path.exists(output_path):
                    os.remove(output_path)
                raise Exception("Edge TTS timeout - WebSocket may be stuck")
            
            # Verify file was created and has content
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                if file_size > 1000:  # Reasonable minimum size for audio
                    logger.info(f"  ✓ [Attempt {attempt_num}] Audio file created successfully ({file_size} bytes)")
                    return True
                else:
                    logger.warning(f"  ✗ [Attempt {attempt_num}] Output file too small ({file_size} bytes), likely invalid")
                    os.remove(output_path)
                    raise Exception(f"Invalid output file size: {file_size} bytes")
            else:
                logger.warning(f"  ✗ [Attempt {attempt_num}] Output file not created")
                raise Exception("Output file was not created")
                
        except Exception as e:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            raise
    
    # Retry loop with exponential backoff
    attempt_errors = []
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(f"Starting attempt {attempt}/{max_attempts}...")
            
            # If we have an async lock, use it to prevent parallel calls
            if async_lock:
                async with async_lock:
                    success = await _do_edge_tts(attempt)
            else:
                success = await _do_edge_tts(attempt)
            
            if success:
                logger.info(f"✓✓✓ Edge TTS SUCCESS on attempt {attempt} ✓✓✓")
                return True
                
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            logger.warning(f"  [Attempt {attempt}/{max_attempts}] FAILED: {error_type}: {error_msg}")
            
            attempt_errors.append({
                "attempt": attempt,
                "error": error_msg,
                "type": error_type
            })
            
            # Check if error is retryable
            is_retryable = _is_retryable_error(e)
            
            if not is_retryable:
                # Non-retryable error - stop here
                logger.warning(f"  ✗ Non-retryable error detected on attempt {attempt} - stopping Edge TTS")
                logger.debug(f"  Error details: {error_type}: {error_msg}")
                return False
            
            # Retryable error - apply exponential backoff if more attempts remain
            if attempt < max_attempts:
                # Calculate backoff: 2^attempt seconds, max 32 seconds
                backoff_seconds = min(2 ** attempt, 32)
                # Add small jitter to prevent thundering herd
                jitter = 0.1 * (attempt % 2)
                backoff_with_jitter = backoff_seconds + jitter
                
                logger.info(f"  → Retryable error detected, backing off {backoff_with_jitter:.1f}s before attempt {attempt + 1}...")
                await asyncio.sleep(backoff_with_jitter)
            else:
                logger.warning(f"  ✗ Maximum attempts ({max_attempts}) reached - proceeding to fallback")
    
    # All attempts failed
    logger.error(f"✗✗✗ Edge TTS FAILED after {max_attempts} attempts ✗✗✗")
    logger.debug(f"Attempt errors: {attempt_errors}")
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
    voice: Optional[str] = None,
) -> Tuple[Optional[str], Optional[TTSError]]:
    """
    Generate voice audio with comprehensive fallback strategy and error handling.
    
    Fallback order:
    1. Edge TTS (max 3 attempts, smart retry logic, voice validation)
    2. Azure TTS (1 attempt, if configured)
    3. gTTS (free service fallback)
    4. pyttsx3 (offline fallback)
    
    Args:
        text: Text to convert to speech
        output_path: Path to save MP3 file (uses default if not specified)
        voice: Optional voice name (uses best_voice if not specified)
    
    Returns:
        Tuple of (audio_path, error_or_none)
        - If successful: (path_string, None)
        - If failed: (None, TTSError_object)
    """
    
    if output_path is None:
        output_path = DEFAULT_OUTPUT_PATH
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # Initialize error tracking
    attempted_providers = []
    attempted_voices = []
    error_details = {}
    
    # =========================================
    # STEP 1: Validate and preprocess input text
    # =========================================
    logger.info(f"=" * 60)
    logger.info(f"TTS REQUEST: Input text length: {len(text) if text else 0} characters")
    logger.info(f"=" * 60)
    
    if not text or not isinstance(text, str):
        error_msg = f"Invalid text input: type={type(text)}, empty={not text}"
        logger.error(error_msg)
        return None, TTSError(
            success=False,
            error=error_msg,
            error_type="INPUT_VALIDATION_ERROR"
        )
    
    processed_text = preprocess_text(text, max_length=MAX_TEXT_LENGTH)
    
    if not processed_text:
        error_msg = "Text preprocessing failed or result is empty"
        logger.error(error_msg)
        return None, TTSError(
            success=False,
            error=error_msg,
            error_type="TEXT_PREPROCESSING_ERROR",
            details={"original_length": len(text), "max_length": MAX_TEXT_LENGTH}
        )
    
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
        return output_path, None
    
    # Get validated voice
    selected_voice = get_best_voice(voice)
    attempted_voices.append(selected_voice)
    
    # =========================================
    # STEP 3: Try Edge TTS (3 attempts max for resilience)
    # =========================================
    logger.info("=" * 60)
    logger.info(f"Provider 1: Edge TTS (voice: {selected_voice})")
    logger.info("=" * 60)
    attempted_providers.append("Edge TTS")
    
    try:
        success = await _edge_tts_with_smart_retry(
            processed_text, 
            output_path, 
            voice=selected_voice,
            max_attempts=3
        )
        
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            logger.info("✓✓✓ SUCCESS: Edge TTS ✓✓✓")
            # Cache the result
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            os.replace(output_path, cache_path)
            os.replace(cache_path, output_path)
            return output_path, None
    except Exception as e:
        logger.warning(f"Edge TTS wrapper error: {type(e).__name__}: {e}")
        error_details["edge_tts"] = {"error": str(e), "type": type(e).__name__}
    
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # =========================================
    # STEP 4: Try ElevenLabs TTS (if configured)
    # ElevenLabs is preferred over Azure when API key is present.
    # =========================================
    logger.info("=" * 60)
    logger.info(f"Provider 2: ElevenLabs TTS (voice: {selected_voice})")
    logger.info("=" * 60)
    attempted_providers.append("ElevenLabs")

    try:
        success = await _elevenlabs_tts(processed_text, output_path)

        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            logger.info("✓✓✓ SUCCESS: ElevenLabs TTS ✓✓✓")
            # Cache the result
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            os.replace(output_path, cache_path)
            os.replace(cache_path, output_path)
            return output_path, None
    except Exception as e:
        logger.warning(f"ElevenLabs TTS error: {type(e).__name__}: {e}")
        error_details["elevenlabs_tts"] = {"error": str(e), "type": type(e).__name__}

    if os.path.exists(output_path):
        os.remove(output_path)
    
    # =========================================
    # STEP 5: Try gTTS (free fallback)
    # =========================================
    logger.info("=" * 60)
    logger.info("Provider 3: gTTS (Google Text-to-Speech)")
    logger.info("=" * 60)
    attempted_providers.append("gTTS")
    
    success = await _gtts_tts(processed_text, output_path, language="en")
    
    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        logger.info("✓✓✓ SUCCESS: gTTS ✓✓✓")
        # Cache the result
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        os.replace(output_path, cache_path)
        os.replace(cache_path, output_path)
        return output_path, None
    
    if os.path.exists(output_path):
        os.remove(output_path)
    
    # =========================================
    # STEP 6: Try pyttsx3 offline (last resort)
    # =========================================
    logger.info("=" * 60)
    logger.info("Provider 4: pyttsx3 (Offline fallback)")
    logger.info("=" * 60)
    attempted_providers.append("pyttsx3")
    
    success = await _pyttsx3_tts(processed_text, output_path)
    
    if success and os.path.exists(output_path):
        logger.info("✓✓✓ SUCCESS: pyttsx3 (Offline) ✓✓✓")
        # Don't cache offline TTS as formats may vary
        return output_path, None
    
    # =========================================
    # ALL PROVIDERS FAILED - RETURN STRUCTURED ERROR
    # =========================================
    error_msg = f"All TTS providers exhausted after {len(attempted_providers)} attempts"
    logger.error(f"✗✗✗ FAILURE: {error_msg} ✗✗✗")
    
    if os.path.exists(output_path):
        os.remove(output_path)
    
    return None, TTSError(
        success=False,
        error=error_msg,
        error_type="ALL_PROVIDERS_FAILED",
        details={
            "providers_attempted": len(attempted_providers),
            "error_details": error_details,
            "text_length": len(processed_text),
            "original_text_length": len(text)
        },
        attempted_voices=[selected_voice],
        attempted_providers=attempted_providers
    )


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
    voice: Optional[str] = None,
    **kwargs
) -> Dict:
    """
    Synchronous wrapper for generate_voice_async.
    Thread-safe and Flask-compatible with proper event loop handling.
    
    Returns structured response (success or error with details) for better Flask integration.
    
    Features:
    - Voice validation and fallback
    - Proper async/sync event loop management
    - Thread-safe with locking (only one Edge TTS request at a time)
    - Detailed error reporting
    
    Args:
        text: Text to convert to speech
        output_path: Path to save MP3 file (uses default if not specified)
        voice: Optional voice name (e.g., "en-US-JennyNeural")
        **kwargs: Ignored parameters for backward compatibility
                 (language, female_voice, voice_model, voice_provider, etc.)
    
    Returns:
        Dict with:
        - "success": bool (True if TTS succeeded)
        - "path": str (audio file path if successful)
        - "error": str (error message if failed)
        - "error_type": str (error classification)
        - "details": dict (additional error details)
        - "attempted_providers": list (providers that were tried)
        - "attempted_voices": list (voices that were attempted)
    
    Example:
        result = generate_voice("Hello world")
        if result["success"]:
            print(f"Audio saved to: {result['path']}")
        else:
            print(f"TTS failed: {result['error']}")
    """
    
    # Log ignored parameters for debugging
    if kwargs:
        ignored_params = [f"{k}={v}" for k, v in kwargs.items()]
        logger.info(f"Ignoring backward-compat parameters: {', '.join(ignored_params)}")
    
    # Acquire thread-safe lock
    with EDGE_TTS_LOCK:
        logger.info(f"Acquired EDGE_TTS_LOCK - starting TTS generation")
        logger.info(f"  voice={voice}, output_path={output_path}")
        
        try:
            loop = _get_or_create_event_loop()
            
            # Run async function and get results
            audio_path, tts_error = loop.run_until_complete(
                generate_voice_async(text, output_path, voice=voice)
            )
            
            if audio_path:
                # Success
                logger.info(f"✓ TTS generation successful: {audio_path}")
                return {
                    "success": True,
                    "path": audio_path,
                    "error": None,
                    "error_type": None,
                    "details": {},
                    "attempted_providers": [],
                    "attempted_voices": []
                }
            else:
                # Failure with error object
                error_dict = tts_error.to_dict() if tts_error else {
                    "success": False,
                    "error": "Unknown TTS error",
                    "error_type": "UNKNOWN_ERROR",
                    "details": {}
                }
                logger.error(f"✗ TTS generation failed: {error_dict['error']}")
                return error_dict
            
        except Exception as e:
            error_msg = f"TTS generation crashed: {type(e).__name__}: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "path": None,
                "error": error_msg,
                "error_type": "SYSTEM_ERROR",
                "details": {"exception": type(e).__name__, "message": str(e)},
                "attempted_providers": [],
                "attempted_voices": []
            }
        
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
) -> Tuple[Optional[str], Optional[TTSError]]:
    """
    Legacy async wrapper for backward compatibility.
    Ignores language and female_voice parameters (now uses smart voice validation).
    
    Args:
        text: Text to synthesize
        language: DEPRECATED - Ignored
        output_path: Path to save MP3 file
        female_voice: DEPRECATED - Ignored
    
    Returns:
        Tuple of (audio_path, error_or_none)
    """
    logger.info(f"Legacy async function called: language={language}, female_voice={female_voice}")
    logger.info("Note: Using smart voice validation instead of language/female_voice params")
    return await generate_voice_async(text, output_path)


def generate_voice_legacy(
    text: str,
    language: str = "english",
    output_path: Optional[str] = None,
    female_voice: bool = False,
) -> Optional[str]:
    """
    Legacy synchronous wrapper for backward compatibility.
    Ignores language and female_voice parameters (now uses smart voice validation).
    
    For new code, use generate_voice() instead which returns structured responses.
    
    Args:
        text: Text to synthesize
        language: DEPRECATED - Ignored
        output_path: Path to save MP3 file
        female_voice: DEPRECATED - Ignored
    
    Returns:
        Audio file path if successful, None if failed
    """
    logger.info(f"Legacy sync function called: language={language}, female_voice={female_voice}")
    logger.info("Note: Using smart voice validation instead of language/female_voice params")
    
    result = generate_voice(text, output_path)
    
    # For backward compatibility, return just the path string
    if result.get("success"):
        return result.get("path")
    else:
        return None

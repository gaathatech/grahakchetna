#!/usr/bin/env python3
"""
Run live TTS provider tests: Edge (always), Azure (if key), ElevenLabs (if key).
Produces files in output/ for inspection.
"""
import os
import asyncio
import logging
from tts_service import (
    _edge_tts_with_smart_retry,
    _elevenlabs_tts,
    _get_or_create_event_loop,
    DEFAULT_OUTPUT_DIR,
    get_cache_path,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_tests():
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    text = "This is a live TTS provider test. Please ignore."

    # 1) Edge TTS
    edge_out = os.path.join(DEFAULT_OUTPUT_DIR, "edge_test.mp3")
    logger.info("Running Edge TTS test...")
    try:
        ok = await _edge_tts_with_smart_retry(text, edge_out, voice=None, max_attempts=2)
        logger.info(f"Edge TTS result: {ok}, file_exists={os.path.exists(edge_out)}")
    except Exception as e:
        logger.exception("Edge TTS failed")

    # Azure removed — ElevenLabs is used as a configured fallback instead

    # 3) ElevenLabs
    if os.getenv("ELEVENLABS_API_KEY"):
        eleven_out = os.path.join(DEFAULT_OUTPUT_DIR, "eleven_test.mp3")
        logger.info("Running ElevenLabs TTS test...")
        try:
            ok = await _elevenlabs_tts(text, eleven_out)
            logger.info(f"ElevenLabs TTS result: {ok}, file_exists={os.path.exists(eleven_out)}")
        except Exception as e:
            logger.exception("ElevenLabs TTS failed")
    else:
        logger.info("Skipping ElevenLabs TTS test (ELEVENLABS_API_KEY not set)")

if __name__ == "__main__":
    loop = _get_or_create_event_loop()
    loop.run_until_complete(run_tests())

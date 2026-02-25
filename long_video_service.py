"""
Long video wrapper using the short-video layout.

This module provides `generate_long_video(...)` which reuses the
visual layout implemented in `video_service.generate_video` but
produces a horizontal 1920x1080 output. The implementation is a
lightweight wrapper that temporarily overrides the layout dimensions
in `video_service`, delegates composition, and restores original
settings.
"""

import os
import logging
from datetime import datetime
import video_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VIDEOS_DIR = "videos"
LONG_VIDEOS_DIR = os.path.join(VIDEOS_DIR, "long")


def generate_long_video(stories, audio_path, language="en", output_path=None, max_duration=None, story_medias=None, green_screen_media=None, **kwargs):
    """Generate a horizontal long-form video using the short-video layout.

    Args:
        stories: list of story dicts (used to build title/description)
        audio_path: path to narration audio file
        language: language tag passed to `generate_video`
        output_path: optional output path; if not provided an auto-named
                     file is created under `videos/long/`.
        max_duration: optional max duration forwarded to `generate_video`

    Returns:
        path to generated video file
    """
    os.makedirs(LONG_VIDEOS_DIR, exist_ok=True)

    # Build title/description from stories (simple fallback)
    title = "Long-form Video"
    description = ""
    try:
        if stories and isinstance(stories, list) and len(stories) > 0:
            title = ' | '.join([s.get('headline', '') for s in stories if s.get('headline')]) or title
            description = '\n\n'.join([s.get('description', '') for s in stories if s.get('description')])
    except Exception:
        pass

    # Output path default
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        output_path = os.path.join(LONG_VIDEOS_DIR, f"long_video_{ts}.mp4")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Temporarily set the short-layout dimensions to 1920x1080
    original_w = getattr(video_service, "WIDTH", None)
    original_h = getattr(video_service, "HEIGHT", None)
    try:
        video_service.WIDTH = 1920
        video_service.HEIGHT = 1080

        logger.info("Generating long video using short layout (1920x1080)")
        video_service.generate_video(title, description, audio_path, language=language, output_path=output_path, max_duration=max_duration)

    finally:
        # Restore original constants
        if original_w is not None:
            video_service.WIDTH = original_w
        if original_h is not None:
            video_service.HEIGHT = original_h

    logger.info(f"Long video written: {output_path}")
    return output_path


if __name__ == "__main__":
    # Quick smoke test (requires a real audio file path argument)
    import sys
    if len(sys.argv) > 1:
        audio = sys.argv[1]
        if os.path.exists(audio):
            print("Generating test long video...")
            out = generate_long_video([], audio)
            print("Done:", out)
        else:
            print("Audio file not found:", audio)
    else:
        print("Usage: python long_video_service.py <audio_file>")

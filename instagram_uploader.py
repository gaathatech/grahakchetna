import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class InstagramUploadError(Exception):
    pass


def upload_instagram(video_path: str, caption: str) -> Dict[str, Any]:
    """Placeholder for Instagram upload functionality.

    This is a stub that should be implemented with an Instagram Graph API
    or other upload flow. For now it returns a consistent response so the
    app routes and UI can call it without failing.
    """
    logger.info(f"Instagram upload called for {video_path}")
    # TODO: implement real upload
    return {"status": "skipped", "reason": "not_implemented"}

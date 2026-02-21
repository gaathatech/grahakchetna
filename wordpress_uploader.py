import os
import logging
from typing import Tuple, Dict, Any

import requests

logger = logging.getLogger(__name__)


class WordPressUploadError(Exception):
    pass


def upload_media(video_path: str, wp_url: str, username: str, app_password: str, timeout: int = 300) -> Dict[str, Any]:
    """
    Upload a video file to WordPress media library via REST API.

    Returns the JSON response from the media endpoint.
    """
    if not os.path.exists(video_path):
        raise WordPressUploadError(f"Video file not found: {video_path}")

    endpoint = f"{wp_url.rstrip('/')}/wp-json/wp/v2/media"

    headers = {
        "Content-Disposition": f'attachment; filename="{os.path.basename(video_path)}"'
    }

    try:
        with open(video_path, "rb") as fh:
            files = {"file": (os.path.basename(video_path), fh, "video/mp4")}
            resp = requests.post(endpoint, auth=(username, app_password), files=files, headers=headers, timeout=timeout)

        resp.raise_for_status()
        logger.info("✓ WordPress media uploaded")
        return resp.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"WordPress media upload failed: {e}")
        raise WordPressUploadError(str(e)) from e


def create_post(title: str, content: str, wp_url: str, username: str, app_password: str, media_id: int = None, status: str = "publish") -> Dict[str, Any]:
    endpoint = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    payload = {
        "title": title,
        "content": content,
        "status": status
    }
    if media_id is not None:
        payload["featured_media"] = media_id

    try:
        resp = requests.post(endpoint, auth=(username, app_password), json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("✓ WordPress post created")
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"WordPress post creation failed: {e}")
        raise WordPressUploadError(str(e)) from e


def publish_video_as_post(video_path: str, title: str, wp_url: str, username: str, app_password: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Uploads the video as media and creates a post linking/embedding it.

    Returns a tuple (media_response, post_response)
    """
    media = upload_media(video_path, wp_url, username, app_password)

    # Prefer the media source URL if available
    media_url = media.get("source_url") or media.get("guid", {}).get("rendered")

    # Simple post content embedding the video
    content = ""
    if media_url:
        content = f"<p>{title}</p>\n<video controls src=\"{media_url}\" style=\"max-width:100%\"></video>"
    else:
        content = f"<p>{title}</p>\n<p>Video uploaded to media library (ID: {media.get('id')}).</p>"

    post = create_post(title=title, content=content, wp_url=wp_url, username=username, app_password=app_password, media_id=media.get("id"))

    return media, post

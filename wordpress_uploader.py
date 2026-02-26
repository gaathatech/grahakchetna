import os
import logging
import ssl
from typing import Tuple, Dict, Any

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# --------------------------------------------------
# FORCE MODERN TLS (Fix TLSV1_ALERT_INTERNAL_ERROR)
# --------------------------------------------------

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def get_session(verify_ssl: bool):
    session = requests.Session()
    session.mount("https://", TLSAdapter())
    session.verify = verify_ssl
    return session


# --------------------------------------------------

class WordPressUploadError(Exception):
    pass


# --------------------------------------------------
# MEDIA UPLOAD
# --------------------------------------------------

def upload_media(video_path: str, wp_url: str, username: str, app_password: str,
                 timeout: int = 300, verify_ssl: bool = False) -> Dict[str, Any]:

    if not os.path.exists(video_path):
        raise WordPressUploadError(f"Video file not found: {video_path}")

    endpoint = f"{wp_url.rstrip('/')}/wp-json/wp/v2/media"
    session = get_session(verify_ssl)

    headers = {
        "Content-Disposition": f'attachment; filename="{os.path.basename(video_path)}"'
    }

    try:
        with open(video_path, "rb") as fh:
            files = {"file": (os.path.basename(video_path), fh, "video/mp4")}

            resp = session.post(
                endpoint,
                auth=(username, app_password),
                files=files,
                headers=headers,
                timeout=timeout
            )

        resp.raise_for_status()
        logger.info("✓ Media uploaded")
        return resp.json()

    except Exception as e:
        logger.error(f"Media upload failed: {e}")
        return {"error": str(e)}


# --------------------------------------------------
# SIMPLE POST (No tag/category resolving to avoid SSL spam)
# --------------------------------------------------

def create_post(title: str,
                content: str,
                wp_url: str,
                username: str,
                app_password: str,
                media_id: int = None,
                status: str = "publish",
                description: str = None,
                youtube_url: str = None,
                verify_ssl: bool = False,
                categories=None,
                tags=None) -> Dict[str, Any]:

    endpoint = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    session = get_session(verify_ssl)

    post_content = ""

    # YouTube embed
    if youtube_url:
        post_content += f'<iframe width="560" height="315" src="{youtube_url}" frameborder="0" allowfullscreen></iframe>\n'

    if description:
        post_content += f"<p>{description}</p>\n"

    post_content += content or ""

    payload = {
        "title": title,
        "content": post_content,
        "status": status
    }

    if media_id:
        payload["featured_media"] = media_id

    # IMPORTANT:
    # Do NOT resolve tags/categories (they trigger multiple SSL calls)
    # WordPress can auto-create tags via names in payload
    if tags:
        payload["tags"] = tags  # send raw names, avoid lookup

    try:
        resp = session.post(
            endpoint,
            auth=(username, app_password),
            json=payload,
            timeout=30
        )

        resp.raise_for_status()
        logger.info("✓ Post created")
        return resp.json()

    except Exception as e:
        logger.error(f"Post creation failed: {e}")
        return {"error": str(e)}


# --------------------------------------------------
# VIDEO + POST
# --------------------------------------------------

def publish_video_as_post(video_path: str,
                          title: str,
                          wp_url: str,
                          username: str,
                          app_password: str,
                          description: str = None,
                          youtube_url: str = None,
                          verify_ssl: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:

    media = upload_media(video_path, wp_url, username, app_password, verify_ssl=verify_ssl)

    media_url = media.get("source_url")

    content = ""
    if media_url:
        content = f'<video controls src="{media_url}" style="max-width:100%"></video>'

    post = create_post(
        title=title,
        content=content,
        wp_url=wp_url,
        username=username,
        app_password=app_password,
        media_id=media.get("id"),
        description=description,
        youtube_url=youtube_url,
        verify_ssl=verify_ssl
    )

    return media, post
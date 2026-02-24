import os
import logging
from typing import Tuple, Dict, Any

import requests
from requests.exceptions import SSLError
import urllib3

logger = logging.getLogger(__name__)


class WordPressUploadError(Exception):
    pass


def upload_media(video_path: str, wp_url: str, username: str, app_password: str, timeout: int = 300, verify_ssl: bool = True) -> Dict[str, Any]:
    """
    Upload a video file to WordPress media library via REST API.

    Args:
        video_path: Path to the video file
        wp_url: WordPress site URL
        username: WordPress username
        app_password: WordPress app password
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates (set to False for self-signed certs)

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
            try:
                resp = requests.post(
                    endpoint,
                    auth=(username, app_password),
                    files=files,
                    headers=headers,
                    timeout=timeout,
                    verify=verify_ssl
                )
            except SSLError as ssl_err:
                # If SSL error and verification was requested, retry with verify=False
                logger.warning(f"SSL error during media upload: {ssl_err}")
                if verify_ssl:
                    logger.warning("Retrying media upload with SSL verification disabled (verify=False)")
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    resp = requests.post(
                        endpoint,
                        auth=(username, app_password),
                        files=files,
                        headers=headers,
                        timeout=timeout,
                        verify=False
                    )
                else:
                    # Try with HTTP
                    logger.warning("Retrying media upload with HTTP instead of HTTPS")
                    http_endpoint = endpoint.replace('https://', 'http://')
                    resp = requests.post(
                        http_endpoint,
                        auth=(username, app_password),
                        files=files,
                        headers=headers,
                        timeout=timeout,
                        verify=False
                    )

        resp.raise_for_status()
        logger.info("✓ WordPress media uploaded")
        return resp.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"WordPress media upload failed: {e}")
        raise WordPressUploadError(str(e)) from e


def _resolve_category_ids(wp_url: str, username: str, app_password: str, categories, verify_ssl: bool = True):
    """Resolve category names or IDs to a list of category IDs.
    If a category name does not exist, attempt to create it.
    """
    if not categories:
        return []

    endpoint = f"{wp_url.rstrip('/')}/wp-json/wp/v2/categories"
    resolved = []
    for cat in categories:
        # If already an int-like ID, accept it
        if isinstance(cat, int):
            resolved.append(cat)
            continue

        name = str(cat).strip()
        if not name:
            continue

        try:
            try:
                resp = requests.get(endpoint, auth=(username, app_password), params={"search": name}, timeout=10, verify=verify_ssl)
            except SSLError as ssl_err:
                logger.warning(f"SSL error when resolving category '{name}': {ssl_err}")
                if verify_ssl:
                    logger.warning("Retrying category lookup with SSL verification disabled (verify=False)")
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    resp = requests.get(endpoint, auth=(username, app_password), params={"search": name}, timeout=10, verify=False)
                else:
                    # Try with HTTP
                    logger.warning("Retrying category lookup with HTTP instead of HTTPS")
                    http_endpoint = endpoint.replace('https://', 'http://')
                    resp = requests.get(http_endpoint, auth=(username, app_password), params={"search": name}, timeout=10, verify=False)
            resp.raise_for_status()
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                resolved.append(data[0].get('id'))
                continue

            # Not found; create it
            try:
                create_resp = requests.post(endpoint, auth=(username, app_password), json={"name": name}, timeout=10, verify=verify_ssl)
            except SSLError as ssl_err:
                logger.warning(f"SSL error when creating category '{name}': {ssl_err}")
                if verify_ssl:
                    logger.warning("Retrying category create with SSL verification disabled (verify=False)")
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    create_resp = requests.post(endpoint, auth=(username, app_password), json={"name": name}, timeout=10, verify=False)
                else:
                    # Try with HTTP
                    logger.warning("Retrying category create with HTTP instead of HTTPS")
                    http_endpoint = endpoint.replace('https://', 'http://')
                    create_resp = requests.post(http_endpoint, auth=(username, app_password), json={"name": name}, timeout=10, verify=False)
            create_resp.raise_for_status()
            created = create_resp.json()
            if created and 'id' in created:
                resolved.append(created['id'])
        except Exception as e:
            logger.warning(f"Could not resolve/create category '{name}': {e}")
            continue

    return resolved


def _resolve_tag_ids(wp_url: str, username: str, app_password: str, tags, verify_ssl: bool = True):
    """Resolve tag names or IDs to a list of tag IDs. Create tag if missing."""
    if not tags:
        return []

    endpoint = f"{wp_url.rstrip('/')}/wp-json/wp/v2/tags"
    resolved = []
    for t in tags:
        if isinstance(t, int):
            resolved.append(t)
            continue

        name = str(t).strip()
        if not name:
            continue

        try:
            try:
                resp = requests.get(endpoint, auth=(username, app_password), params={"search": name}, timeout=10, verify=verify_ssl)
            except SSLError as ssl_err:
                logger.warning(f"SSL error when resolving tag '{name}': {ssl_err}")
                if verify_ssl:
                    logger.warning("Retrying tag lookup with SSL verification disabled (verify=False)")
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    resp = requests.get(endpoint, auth=(username, app_password), params={"search": name}, timeout=10, verify=False)
                else:
                    # Try with HTTP instead
                    logger.warning("Retrying tag lookup with HTTP instead of HTTPS")
                    http_endpoint = endpoint.replace('https://', 'http://')
                    resp = requests.get(http_endpoint, auth=(username, app_password), params={"search": name}, timeout=10, verify=False)
            resp.raise_for_status()
            data = resp.json()
            if data and isinstance(data, list) and len(data) > 0:
                resolved.append(data[0].get('id'))
                continue

            try:
                create_resp = requests.post(endpoint, auth=(username, app_password), json={"name": name}, timeout=10, verify=verify_ssl)
            except SSLError as ssl_err:
                logger.warning(f"SSL error when creating tag '{name}': {ssl_err}")
                if verify_ssl:
                    logger.warning("Retrying tag create with SSL verification disabled (verify=False)")
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    create_resp = requests.post(endpoint, auth=(username, app_password), json={"name": name}, timeout=10, verify=False)
                else:
                    # Try with HTTP
                    logger.warning("Retrying tag create with HTTP instead of HTTPS")
                    http_endpoint = endpoint.replace('https://', 'http://')
                    create_resp = requests.post(http_endpoint, auth=(username, app_password), json={"name": name}, timeout=10, verify=False)
            create_resp.raise_for_status()
            created = create_resp.json()
            if created and 'id' in created:
                resolved.append(created['id'])
        except Exception as e:
            logger.warning(f"Could not resolve/create tag '{name}': {e}")
            continue

    return resolved


def create_post(title: str, content: str, wp_url: str, username: str, app_password: str, media_id: int = None, status: str = "publish", description: str = None, youtube_url: str = None, verify_ssl: bool = True, categories=None, tags=None) -> Dict[str, Any]:
    endpoint = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    
    # Build post content
    post_content = ""
    
    # Extract YouTube video ID from various URL formats
    video_id = None
    if youtube_url:
        # Handle https://youtube.com/watch?v=VIDEOID
        # Handle https://youtu.be/VIDEOID
        # Handle https://www.youtube.com/watch?v=VIDEOID
        if "youtube.com" in youtube_url:
            try:
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(youtube_url)
                video_id = parse_qs(parsed.query).get('v', [None])[0]
            except:
                # Fallback to simple split
                video_id = youtube_url.split('v=')[-1] if 'v=' in youtube_url else None
        elif "youtu.be" in youtube_url:
            # Extract from youtu.be/VIDEOID format
            video_id = youtube_url.split('/')[-1]
        else:
            # Assume it's just the video ID
            video_id = youtube_url.strip()
        
        if video_id:
            post_content += f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n'
    
    if description:
        post_content += f"<p>{description}</p>\n"
    else:
        post_content += f"<p>{title}</p>\n"
    
    if content:
        post_content += content
    
    payload = {
        "title": title,
        "content": post_content,
        "status": status
    }
    if media_id is not None:
        payload["featured_media"] = media_id
    # Resolve categories (names or ids) into IDs list
    try:
        cat_ids = _resolve_category_ids(wp_url, username, app_password, categories, verify_ssl=verify_ssl)
        if cat_ids:
            payload['categories'] = cat_ids
    except Exception:
        pass
    try:
        tag_ids = _resolve_tag_ids(wp_url, username, app_password, tags, verify_ssl=verify_ssl)
        if tag_ids:
            payload['tags'] = tag_ids
    except Exception:
        pass

    try:
        try:
            resp = requests.post(
                endpoint,
                auth=(username, app_password),
                json=payload,
                timeout=30,
                verify=verify_ssl
            )
        except SSLError as ssl_err:
            logger.warning(f"SSL error when creating post: {ssl_err}")
            if verify_ssl:
                logger.warning("Retrying post creation with SSL verification disabled (verify=False)")
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                resp = requests.post(
                    endpoint,
                    auth=(username, app_password),
                    json=payload,
                    timeout=30,
                    verify=False
                )
            else:
                # Try with HTTP
                logger.warning("Retrying post creation with HTTP instead of HTTPS")
                http_endpoint = endpoint.replace('https://', 'http://')
                resp = requests.post(
                    http_endpoint,
                    auth=(username, app_password),
                    json=payload,
                    timeout=30,
                    verify=False
                )
        resp.raise_for_status()
        logger.info("✓ WordPress post created")
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"WordPress post creation failed: {e}")
        raise WordPressUploadError(str(e)) from e


def publish_video_as_post(video_path: str, title: str, wp_url: str, username: str, app_password: str, description: str = None, youtube_url: str = None, verify_ssl: bool = True) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Uploads the video as media and creates a post linking/embedding it.

    Args:
        video_path: Path to the video file
        title: Post title
        wp_url: WordPress site URL
        username: WordPress username
        app_password: WordPress app password
        description: Post description (optional)
        youtube_url: YouTube video URL to embed (optional)
        verify_ssl: Whether to verify SSL certificates (set to False for self-signed certs)

    Returns a tuple (media_response, post_response)
    """
    media = upload_media(video_path, wp_url, username, app_password, verify_ssl=verify_ssl)

    # Prefer the media source URL if available
    media_url = media.get("source_url") or media.get("guid", {}).get("rendered")

    # Simple post content embedding the video
    content = ""
    if media_url:
        content = f"<video controls src=\"{media_url}\" style=\"max-width:100%\"></video>"
    else:
        content = f"<p>Video uploaded to media library (ID: {media.get('id')}).</p>"

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

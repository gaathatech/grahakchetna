import logging
import os
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


class InstagramUploadError(Exception):
    pass


def upload_instagram(video_path: str, caption: str, page_id: Optional[str] = None, page_access_token: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
    """Upload a local video file to Instagram via the Page/Instagram Graph API.

    Flow:
    1. Upload video to Facebook Page (/PAGE_ID/videos) using page access token.
    2. Get the uploaded video's source URL.
    3. Get the connected Instagram Business Account for the Page.
    4. Create an IG media container with `video_url` pointing to the FB video source.
    5. Publish the IG media container.

    Note: This requires the Page to be connected to an Instagram Business account
    and the access token must have the required permissions.
    """
    # Use env vars when not provided
    page_id = page_id or os.getenv('PAGE_ID')
    page_access_token = page_access_token or os.getenv('PAGE_ACCESS_TOKEN')

    if not page_id or not page_access_token:
        raise InstagramUploadError('PAGE_ID and PAGE_ACCESS_TOKEN are required')

    if not os.path.exists(video_path):
        raise InstagramUploadError(f'Video file not found: {video_path}')

    graph_base = 'https://graph.facebook.com'
    api_version = os.getenv('FACEBOOK_GRAPH_API_VERSION', 'v19.0')

    # 1) Upload video to Page
    upload_endpoint = f"{graph_base}/{api_version}/{page_id}/videos"
    files = {}
    try:
        with open(video_path, 'rb') as fh:
            files = {'file': (os.path.basename(video_path), fh, 'video/mp4')}
            params = {'access_token': page_access_token, 'description': caption}
            resp = requests.post(upload_endpoint, files=files, params=params, timeout=timeout)
        resp.raise_for_status()
        upload_json = resp.json()
    except requests.RequestException as e:
        logger.error('Page video upload failed: %s', e)
        raise InstagramUploadError(str(e)) from e

    video_id = upload_json.get('id')
    if not video_id:
        raise InstagramUploadError(f'Failed to upload video to Page: {upload_json}')

    # 2) Get source URL for uploaded video
    try:
        src_resp = requests.get(f"{graph_base}/{api_version}/{video_id}", params={'fields': 'source', 'access_token': page_access_token}, timeout=30)
        src_resp.raise_for_status()
        src_json = src_resp.json()
        video_url = src_json.get('source')
    except requests.RequestException as e:
        logger.error('Failed to fetch uploaded video source: %s', e)
        raise InstagramUploadError(str(e)) from e

    if not video_url:
        raise InstagramUploadError(f'Uploaded video source not available: {src_json}')

    # 3) Get connected Instagram Business Account for the Page
    try:
        conn_resp = requests.get(f"{graph_base}/{api_version}/{page_id}", params={'fields': 'instagram_business_account', 'access_token': page_access_token}, timeout=30)
        conn_resp.raise_for_status()
        conn_json = conn_resp.json()
        ig_info = conn_json.get('instagram_business_account') or conn_json.get('instagram_account')
        ig_id = ig_info.get('id') if ig_info else None
    except requests.RequestException as e:
        logger.error('Failed to get connected Instagram account: %s', e)
        raise InstagramUploadError(str(e)) from e

    if not ig_id:
        raise InstagramUploadError('No connected Instagram Business account found for the Page')

    # 4) Create IG media container using the video URL
    try:
        create_resp = requests.post(f"{graph_base}/{api_version}/{ig_id}/media", params={'video_url': video_url, 'caption': caption, 'access_token': page_access_token}, timeout=30)
        create_resp.raise_for_status()
        create_json = create_resp.json()
        creation_id = create_json.get('id')
    except requests.RequestException as e:
        logger.error('Failed to create IG media container: %s', e)
        raise InstagramUploadError(str(e)) from e

    if not creation_id:
        raise InstagramUploadError(f'IG media container creation failed: {create_json}')

    # 5) Publish the IG media container
    try:
        publish_resp = requests.post(f"{graph_base}/{api_version}/{ig_id}/media_publish", params={'creation_id': creation_id, 'access_token': page_access_token}, timeout=30)
        publish_resp.raise_for_status()
        publish_json = publish_resp.json()
    except requests.RequestException as e:
        logger.error('Failed to publish IG media: %s', e)
        raise InstagramUploadError(str(e)) from e

    return {
        'page_upload': upload_json,
        'video_source': src_json,
        'ig_creation': create_json,
        'ig_publish': publish_json,
    }

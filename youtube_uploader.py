import logging
from typing import Dict, Any

import logging
import os
import json
from typing import Dict, Any, Optional

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)


class YouTubeUploadError(Exception):
    pass


def _get_client_secrets_path() -> Optional[str]:
    # Prefer explicit env var, else look for downloaded client_secret file
    path = os.getenv('GOOGLE_CLIENT_SECRETS')
    if path and os.path.exists(path):
        return path
    # try to find a client_secret_*.json in workspace
    for fname in os.listdir('.'):
        if fname.startswith('client_secret_') and fname.endswith('.json'):
            return os.path.abspath(fname)
    return None


def get_authenticated_service(client_secrets_file: Optional[str] = None, credentials_path: str = 'youtube_token.json'):
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']

    if client_secrets_file is None:
        client_secrets_file = _get_client_secrets_path()

    if not client_secrets_file or not os.path.exists(client_secrets_file):
        raise YouTubeUploadError('Client secrets JSON not found. Set GOOGLE_CLIENT_SECRETS env or place client_secret_*.json in project root.')

    creds = None
    # Try to load saved credentials
    if os.path.exists(credentials_path):
        try:
            with open(credentials_path, 'r') as f:
                data = json.load(f)
            # If token exists, we'll still run the flow which will reuse cached credentials if supported
        except Exception:
            creds = None

    # Run OAuth flow (will open a local server and prompt for authorization)
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save credentials for the next run
    try:
        with open(credentials_path, 'w') as f:
            f.write(creds.to_json())
    except Exception as e:
        logger.warning('Failed to save credentials: %s', e)

    # Build the API client
    service = build('youtube', 'v3', credentials=creds)
    return service


def upload_youtube(video_path: str, title: str, description: str, privacy: str = 'unlisted') -> Dict[str, Any]:
    """Uploads a video to YouTube using OAuth2 credentials.

    This will run the InstalledAppFlow the first time and store tokens in `youtube_token.json`.

    Note: The OAuth client must be configured on Google Cloud and test users added if the app is in testing.
    """
    if not os.path.exists(video_path):
        raise YouTubeUploadError(f'Video file not found: {video_path}')

    try:
        service = get_authenticated_service()

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': [],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': privacy
            }
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/*')

        request = service.videos().insert(part=','.join(body.keys()), body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info('Upload progress: %s%%', int(status.progress() * 100))

        return {'status': 'success', 'id': response.get('id'), 'response': response}

    except HttpError as e:
        logger.exception('YouTube API error')
        raise YouTubeUploadError(str(e))
    except Exception as e:
        logger.exception('Unexpected error during upload')
        raise YouTubeUploadError(str(e))

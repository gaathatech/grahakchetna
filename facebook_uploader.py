"""
Facebook Reel Uploader Module

This module provides functionality to upload MP4 videos as Facebook Reels
using the Facebook Graph API v19.0 with 3-phase upload flow (start, upload, finish).

Author: Production System
Version: 1.0.0
"""

import logging
import os
from typing import Dict, Optional
from pathlib import Path

import requests


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
FACEBOOK_GRAPH_API_VERSION = "v19.0"
FACEBOOK_GRAPH_BASE_URL = "https://graph.facebook.com"
FACEBOOK_RUPLOAD_BASE_URL = "https://rupload.facebook.com"
DEFAULT_TIMEOUT = 300  # 5 minutes for file uploads
REQUEST_TIMEOUT = 30   # 30 seconds for API calls


class FacebookReelUploadError(Exception):
    """Custom exception for Facebook Reel upload errors."""
    pass


class FacebookReelUploadValidator:
    """Validator class for Facebook Reel upload parameters."""

    @staticmethod
    def validate_video_path(video_path: str) -> None:
        """
        Validate that video file exists and is an MP4.

        Args:
            video_path: Path to the video file

        Raises:
            FacebookReelUploadError: If file doesn't exist or is not MP4
        """
        if not video_path:
            raise FacebookReelUploadError("video_path cannot be empty")

        path = Path(video_path)
        if not path.exists():
            raise FacebookReelUploadError(f"Video file not found: {video_path}")

        if not path.is_file():
            raise FacebookReelUploadError(f"Path is not a file: {video_path}")

        if path.suffix.lower() != ".mp4":
            raise FacebookReelUploadError(f"Invalid file format. Expected MP4, got: {path.suffix}")

        file_size = path.stat().st_size
        if file_size == 0:
            raise FacebookReelUploadError("Video file is empty")

        logger.info(f"Video validation successful: {video_path} ({file_size} bytes)")

    @staticmethod
    def validate_parameters(
        caption: str,
        page_id: str,
        page_access_token: str
    ) -> None:
        """
        Validate required parameters.

        Args:
            caption: Video caption/description
            page_id: Facebook page ID
            page_access_token: Facebook page access token

        Raises:
            FacebookReelUploadError: If any parameter is invalid
        """
        if not page_id or not isinstance(page_id, str):
            raise FacebookReelUploadError("page_id must be a non-empty string")

        if not page_access_token or not isinstance(page_access_token, str):
            raise FacebookReelUploadError("page_access_token must be a non-empty string")

        if not isinstance(caption, str):
            raise FacebookReelUploadError("caption must be a string")

        if not page_id.isdigit():
            raise FacebookReelUploadError("page_id must contain only digits")

        logger.info(f"Parameter validation successful for page_id: {page_id}")


class FacebookReelUploader:
    """Handler for Facebook Reel upload operations."""

    def __init__(
        self,
        page_id: str,
        page_access_token: str,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """
        Initialize the uploader.

        Args:
            page_id: Facebook page ID
            page_access_token: Facebook page access token
            timeout: Request timeout in seconds
        """
        self.page_id = page_id
        self.page_access_token = page_access_token
        self.timeout = timeout
        self.video_id = None

    def _start_upload(self) -> str:
        """
        Start the upload phase to get a video ID.

        Returns:
            video_id: The video ID for upload

        Raises:
            FacebookReelUploadError: If API call fails
        """
        logger.info("Starting upload phase (START)")

        url = (
            f"{FACEBOOK_GRAPH_BASE_URL}/{FACEBOOK_GRAPH_API_VERSION}/"
            f"{self.page_id}/video_reels"
        )

        params = {
            "upload_phase": "start",
            "access_token": self.page_access_token
        }

        try:
            response = requests.post(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            data = response.json()

            if "video_id" not in data:
                raise FacebookReelUploadError(
                    f"No video_id in START response: {data}"
                )

            video_id = data["video_id"]
            logger.info(f"✓ START phase successful. Video ID: {video_id}")

            return video_id

        except requests.exceptions.Timeout:
            raise FacebookReelUploadError("START phase request timeout")
        except requests.exceptions.HTTPError as e:
            # Log response body for debugging
            try:
                logger.error(f"START phase HTTP error: {e} - response: {response.text}")
            except Exception:
                logger.error(f"START phase HTTP error: {e}")
            raise FacebookReelUploadError(f"START phase failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            error_msg = f"START phase failed: {str(e)}"
            logger.error(error_msg)
            raise FacebookReelUploadError(error_msg)

    def _upload_video_chunk(self, video_path: str) -> None:
        """
        Upload the video file in UPLOAD phase.

        Args:
            video_path: Path to the video file

        Raises:
            FacebookReelUploadError: If upload fails
        """
        logger.info(f"Starting upload phase (UPLOAD) for video: {video_path}")

        if not self.video_id:
            raise FacebookReelUploadError("video_id not set. Call _start_upload first.")

        url = (
            f"{FACEBOOK_RUPLOAD_BASE_URL}/video-upload/"
            f"{FACEBOOK_GRAPH_API_VERSION}/{self.video_id}"
        )

        headers = {
            "Authorization": f"OAuth {self.page_access_token}"
        }

        try:
            file_size = Path(video_path).stat().st_size
            logger.info(f"Uploading video file ({file_size} bytes)...")

            with open(video_path, "rb") as video_file:
                files = {"file": video_file}
                data = {"offset": 0}

                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                response.raise_for_status()

                logger.info("✓ UPLOAD phase successful")

        except FileNotFoundError as e:
            error_msg = f"Video file not found during upload: {str(e)}"
            logger.error(error_msg)
            raise FacebookReelUploadError(error_msg)
        except requests.exceptions.Timeout:
            raise FacebookReelUploadError(
                f"UPLOAD phase request timeout (timeout={self.timeout}s)"
            )
        except requests.exceptions.HTTPError as e:
            try:
                logger.error(f"UPLOAD phase HTTP error: {e} - response: {response.text}")
            except Exception:
                logger.error(f"UPLOAD phase HTTP error: {e}")
            raise FacebookReelUploadError(f"UPLOAD phase failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            error_msg = f"UPLOAD phase failed: {str(e)}"
            logger.error(error_msg)
            raise FacebookReelUploadError(error_msg)

    def _finish_upload(self, caption: str) -> Dict:
        """
        Finish the upload phase and complete the reel creation.

        Args:
            caption: Video description/caption

        Returns:
            response_data: API response containing reel details

        Raises:
            FacebookReelUploadError: If finish phase fails
        """
        logger.info("Starting upload phase (FINISH)")

        if not self.video_id:
            raise FacebookReelUploadError("video_id not set. Call _start_upload first.")

        url = (
            f"{FACEBOOK_GRAPH_BASE_URL}/{FACEBOOK_GRAPH_API_VERSION}/"
            f"{self.page_id}/video_reels"
        )

        params = {
            "upload_phase": "finish",
            "video_id": self.video_id,
            "description": caption,
            "access_token": self.page_access_token
        }
        try:
            response = requests.post(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            data = response.json()

            if "id" not in data:
                logger.warning(f"No reel ID in FINISH response: {data}")
                return data

            reel_id = data["id"]
            logger.info(f"✓ FINISH phase successful. Reel ID: {reel_id}")
            print(f"\n✓ Successfully uploaded Facebook Reel! ID: {reel_id}\n")

            return data

        except requests.exceptions.Timeout:
            raise FacebookReelUploadError("FINISH phase request timeout")
        except requests.exceptions.HTTPError as e:
            try:
                logger.error(f"FINISH phase HTTP error: {e} - response: {response.text}")
            except Exception:
                logger.error(f"FINISH phase HTTP error: {e}")
            raise FacebookReelUploadError(f"FINISH phase failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            error_msg = f"FINISH phase failed: {str(e)}"
            logger.error(error_msg)
            raise FacebookReelUploadError(error_msg)

    def upload(self, video_path: str, caption: str) -> Dict:
        """
        Execute the complete 3-phase upload flow.

        Args:
            video_path: Path to MP4 video file
            caption: Video description/caption

        Returns:
            response_data: API response containing reel details

        Raises:
            FacebookReelUploadError: If any phase fails
        """
        try:
            # Validate inputs
            FacebookReelUploadValidator.validate_video_path(video_path)

            # Phase 1: START
            self.video_id = self._start_upload()

            # Phase 2: UPLOAD
            self._upload_video_chunk(video_path)

            # Phase 3: FINISH
            response = self._finish_upload(caption)

            logger.info("✓ Complete upload flow successful")
            return response

        except FacebookReelUploadError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during upload: {str(e)}"
            logger.error(error_msg)
            raise FacebookReelUploadError(error_msg) from e


def upload_reel(
    video_path: str,
    caption: str,
    page_id: str,
    page_access_token: str,
    timeout: Optional[int] = None
) -> Dict:
    """
    Upload an MP4 video as a Facebook Reel using 3-phase upload flow.

    This function uploads a video to a Facebook Page as a Reel using the
    Facebook Graph API v19.0. The upload process consists of three phases:
    1. START: Initialize upload and get video ID
    2. UPLOAD: Upload the video file
    3. FINISH: Finalize the reel creation

    Args:
        video_path (str): Absolute or relative path to MP4 video file
        caption (str): Reel description/caption text
        page_id (str): Facebook Page ID (numeric string)
        page_access_token (str): Facebook Page access token
        timeout (Optional[int]): Upload timeout in seconds (default: 300)

    Returns:
        Dict: JSON response containing reel metadata. Example:
            {
                "id": "reel_id_here",
                "post_id": "post_id_here"
            }

    Raises:
        FacebookReelUploadError: If any upload phase fails or validation fails

    Example:
        >>> video_path = "/path/to/video.mp4"
        >>> caption = "Check out this amazing reel!"
        >>> page_id = "123456789"
        >>> access_token = "your_page_access_token"
        >>> response = upload_reel(video_path, caption, page_id, access_token)
        >>> print(f"Reel ID: {response['id']}")

    Raises:
        FacebookReelUploadError: On upload failures
    """
    # Sanitize token (strip whitespace and accidental surrounding characters)
    if isinstance(page_access_token, str):
        page_access_token = page_access_token.strip().strip('"').strip("'").strip()
        # Remove a trailing '>' if accidentally copied from some shells or URLs
        if page_access_token.endswith('>'):
            page_access_token = page_access_token.rstrip('>')

    # Validate parameters
    FacebookReelUploadValidator.validate_parameters(caption, page_id, page_access_token)
    FacebookReelUploadValidator.validate_video_path(video_path)

    # Set timeout
    upload_timeout = timeout or DEFAULT_TIMEOUT

    # Create uploader instance and execute
    uploader = FacebookReelUploader(page_id, page_access_token, upload_timeout)

    return uploader.upload(video_path, caption)


if __name__ == "__main__":
    # Example usage with error handling
    import sys

    try:
        # Environment variables or command line arguments
        video_file = os.getenv("VIDEO_PATH", "sample_video.mp4")
        reel_caption = os.getenv("CAPTION", "Check out this reel!")
        fb_page_id = os.getenv("PAGE_ID")
        fb_access_token = os.getenv("PAGE_ACCESS_TOKEN")

        if not fb_page_id or not fb_access_token:
            logger.error("PAGE_ID and PAGE_ACCESS_TOKEN environment variables required")
            sys.exit(1)

        logger.info(f"Uploading reel from: {video_file}")
        result = upload_reel(video_file, reel_caption, fb_page_id, fb_access_token)
        logger.info(f"Upload response: {result}")

    except FacebookReelUploadError as e:
        logger.error(f"Upload failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

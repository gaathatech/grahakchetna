"""Simple test runner to upload a video to YouTube.

Usage:
  python run_upload_test.py path/to/video.mp4 "Title" "Description"

The first run will open a browser window for OAuth consent (InstalledAppFlow).
Make sure your Google OAuth client JSON is in the project root or set `GOOGLE_CLIENT_SECRETS`.
"""
import sys
import logging
from youtube_uploader import upload_youtube, YouTubeUploadError

logging.basicConfig(level=logging.INFO)

def main():
    if len(sys.argv) < 4:
        print('Usage: python run_upload_test.py path/to/video.mp4 "Title" "Description"')
        sys.exit(1)

    video = sys.argv[1]
    title = sys.argv[2]
    desc = sys.argv[3]

    try:
        resp = upload_youtube(video, title, desc)
        print('Upload result:', resp)
    except YouTubeUploadError as e:
        print('Upload failed:', e)

if __name__ == '__main__':
    main()

"""
YouTube Video Fetcher Service
Fetches new videos from YouTube channel without API
Downloads videos and extracts metadata for auto-posting
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class YouTubeFetcher:
    def __init__(self, channel_url=None, output_dir="downloads/youtube"):
        """
        Initialize YouTube Fetcher
        Args:
            channel_url: YouTube channel URL or channel ID
            output_dir: Directory to save downloaded videos
        """
        self.channel_url = channel_url
        self.output_dir = output_dir
        self.metadata_file = os.path.join(output_dir, "youtube_metadata.json")
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Load existing metadata
        self.metadata = self._load_metadata()
        
    def _load_metadata(self):
        """Load previously fetched video metadata"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
        return {}
    
    def _save_metadata(self):
        """Save video metadata to file"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def fetch_channel_info(self, channel_url):
        """
        Fetch channel information
        Returns: Channel name and URL
        """
        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-warnings',
                f'{channel_url}'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return {
                    'channel_id': info.get('channel_id'),
                    'uploader': info.get('uploader'),
                    'channel_url': info.get('channel_url'),
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching channel info: {e}")
            return None
    
    def fetch_recent_videos(self, channel_url, max_videos=10):
        """
        Fetch recent videos from a YouTube channel
        Args:
            channel_url: Channel URL or ID
            max_videos: Maximum number of recent videos to fetch
        
        Returns:
            List of video metadata dictionaries
        """
        try:
            # Construct playlist URL if channel URL given
            if 'youtube.com/c/' in channel_url or 'youtube.com/@' in channel_url:
                playlist_url = f"{channel_url}/videos"
            elif 'youtube.com/channel/' in channel_url:
                channel_id = channel_url.split('/')[-1]
                playlist_url = f"https://www.youtube.com/channel/{channel_id}/videos"
            else:
                playlist_url = channel_url
            
            logger.info(f"Fetching videos from: {playlist_url}")
            
            # Use yt-dlp to get video list
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-warnings',
                '--playlist-items', f'1-{max_videos}',
                '--extract-audio',  # Will extract audio info
                '--no-download',
                playlist_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr}")
                return []
            
            videos = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        video_info = json.loads(line)
                        videos.append(self._extract_video_metadata(video_info))
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Fetched {len(videos)} videos")
            return videos
            
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp request timed out")
            return []
        except Exception as e:
            logger.error(f"Error fetching videos: {e}")
            return []
    
    def _extract_video_metadata(self, video_info):
        """Extract relevant metadata from yt-dlp response"""
        return {
            'video_id': video_info.get('id'),
            'title': video_info.get('title'),
            'description': video_info.get('description'),
            'uploader': video_info.get('uploader'),
            'upload_date': video_info.get('upload_date'),  # YYYYMMDD format
            'duration': video_info.get('duration'),  # seconds
            'view_count': video_info.get('view_count'),
            'like_count': video_info.get('like_count'),
            'url': f"https://www.youtube.com/watch?v={video_info.get('id')}",
            'thumbnail': video_info.get('thumbnail'),
            'ext': video_info.get('ext'),
            'format': video_info.get('format'),
        }
    
    def download_video(self, video_url, format_spec='best[height<=1080]'):
        """
        Download video from YouTube
        Args:
            video_url: YouTube video URL
            format_spec: yt-dlp format specification
        
        Returns:
            Path to downloaded file or None
        """
        try:
            logger.info(f"Downloading: {video_url}")
            
            output_template = os.path.join(
                self.output_dir,
                '%(title)s [%(id)s].%(ext)s'
            )
            
            cmd = [
                'yt-dlp',
                '-f', format_spec,
                '-o', output_template,
                '--no-warnings',
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Download successful: {video_url}")
                # Find the downloaded file
                for file in os.listdir(self.output_dir):
                    if video_url.split('v=')[-1] in file:
                        return os.path.join(self.output_dir, file)
                return None
            else:
                logger.error(f"Download failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Download timeout: {video_url}")
            return None
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    def is_video_posted(self, video_id):
        """Check if video was already posted"""
        return video_id in self.metadata and self.metadata[video_id].get('posted')
    
    def mark_as_posted(self, video_id, platform, post_id):
        """Mark video as posted to a platform"""
        if video_id not in self.metadata:
            self.metadata[video_id] = {}
        
        if 'posted_to' not in self.metadata[video_id]:
            self.metadata[video_id]['posted_to'] = {}
        
        self.metadata[video_id]['posted_to'][platform] = {
            'post_id': post_id,
            'timestamp': datetime.now().isoformat()
        }
        self.metadata[video_id]['posted'] = True
        self._save_metadata()
    
    def get_new_videos(self, channel_url, max_videos=10):
        """
        Get new unposted videos from channel
        Returns: List of new video metadata
        """
        try:
            recent_videos = self.fetch_recent_videos(channel_url, max_videos)
            new_videos = [v for v in recent_videos if not self.is_video_posted(v['video_id'])]
            
            return new_videos
            
        except Exception as e:
            logger.error(f"Error getting new videos: {e}")
            return []
    

def check_yt_dlp_installed():
    """Check if yt-dlp is installed"""
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, timeout=5)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def install_yt_dlp():
    """Install yt-dlp via pip"""
    try:
        logger.info("Installing yt-dlp...")
        subprocess.run(['pip', 'install', 'yt-dlp'], check=True)
        logger.info("yt-dlp installed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to install yt-dlp: {e}")
        return False


# Example usage
if __name__ == "__main__":
    # Check/install yt-dlp
    if not check_yt_dlp_installed():
        print("yt-dlp not found. Installing...")
        if not install_yt_dlp():
            print("Failed to install yt-dlp")
            exit(1)
    
    # Example: Fetch videos
    fetcher = YouTubeFetcher()
    
    # Replace with your channel URL
    CHANNEL_URL = "https://www.youtube.com/@YOUR_CHANNEL"
    
    # Get new videos
    new_videos = fetcher.get_new_videos(CHANNEL_URL, max_videos=5)
    print(f"Found {len(new_videos)} new videos")
    
    for video in new_videos:
        print(f"- {video['title']}")
        print(f"  Duration: {video['duration']}s")
        print(f"  URL: {video['url']}\n")

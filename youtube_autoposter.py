"""
YouTube Auto-Poster Orchestrator
Fetches videos from YouTube and auto-posts to Facebook and Instagram
"""

import os
import time
import logging
from datetime import datetime
from youtube_fetcher import YouTubeFetcher, check_yt_dlp_installed, install_yt_dlp
from facebook_uploader import FacebookReelUploader
from instagram_uploader import InstagramUploader
from wordpress_uploader import create_post as wordpress_create_post, WordPressUploadError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class YouTubeAutoPoster:
    def __init__(self, config_file="youtube_config.json"):
        """
        Initialize Auto-Poster
        Args:
            config_file: Configuration file path
        """
        self.config = self._load_config(config_file)
        self.youtube_fetcher = YouTubeFetcher(
            output_dir=self.config.get('download_dir', 'downloads/youtube')
        )
        
        # Initialize uploaders
        self.facebook_uploader = None
        self.instagram_uploader = None
        self._init_uploaders()
        
        logger.info("YouTubeAutoPoster initialized")
    
    def _load_config(self, config_file):
        """Load configuration"""
        import json
        default_config = {
            'youtube_channel': '',
            'facebook_page_id': '',
            'instagram_account': '',
            'wordpress_url': '',
            'wordpress_username': '',
            'wordpress_app_password': '',
            'download_dir': 'downloads/youtube',
            'check_interval': 300,  # seconds
            'max_videos': 5,
            'auto_post_facebook': True,
            'auto_post_instagram': True,
            'auto_post_wordpress': True,
            'wordpress_include_youtube_link': True,
            'include_source_link': False,
            'add_hashtags': True,
            'hashtags': '#YouTubeShorts #Repost #ViralVideo',
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def _init_uploaders(self):
        """Initialize Facebook and Instagram uploaders"""
        try:
            self.facebook_uploader = FacebookReelUploader(
                page_access_token=os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN', '')
            )
            logger.info("Facebook uploader initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Facebook uploader: {e}")
        
        try:
            self.instagram_uploader = InstagramUploader()
            logger.info("Instagram uploader initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Instagram uploader: {e}")
    
    def _prepare_caption(self, video_metadata):
        """
        Prepare caption for social media post
        Excludes YouTube link as per requirement
        """
        caption = video_metadata.get('title', '')
        
        # Add description if available
        description = video_metadata.get('description', '')
        if description:
            # Truncate description to avoid too long captions
            max_desc_length = 200
            if len(description) > max_desc_length:
                description = description[:max_desc_length] + "..."
            caption += f"\n\n{description}"
        
        # Add hashtags if configured
        if self.config.get('add_hashtags'):
            caption += f"\n\n{self.config.get('hashtags', '')}"
        
        # Add uploader info if available (but NOT the YouTube link)
        uploader = video_metadata.get('uploader', '')
        if uploader:
            caption += f"\n\n📺 via {uploader}"
        
        return caption
    
    def _prepare_thumbnail(self, video_metadata):
        """Get video thumbnail URL for preview"""
        return video_metadata.get('thumbnail')
    
    def post_to_facebook(self, video_file, video_metadata):
        """
        Post video to Facebook
        """
        if not self.facebook_uploader:
            logger.error("Facebook uploader not initialized")
            return None
        
        try:
            logger.info(f"Uploading to Facebook: {video_metadata['title']}")
            
            caption = self._prepare_caption(video_metadata)
            
            # Upload using facebook uploader
            post_id = self.facebook_uploader.upload_video(
                video_file=video_file,
                title=video_metadata.get('title', ''),
                description=caption,
                schedule_time=None  # Post immediately
            )
            
            if post_id:
                logger.info(f"Posted to Facebook successfully: {post_id}")
                return post_id
            else:
                logger.error("Failed to post to Facebook")
                return None
                
        except Exception as e:
            logger.error(f"Error posting to Facebook: {e}")
            return None
    
    def post_to_instagram(self, video_file, video_metadata):
        """
        Post video to Instagram
        """
        if not self.instagram_uploader:
            logger.error("Instagram uploader not initialized")
            return None
        
        try:
            logger.info(f"Uploading to Instagram: {video_metadata['title']}")
            
            caption = self._prepare_caption(video_metadata)
            
            # Upload using instagram uploader
            post_id = self.instagram_uploader.upload_video(
                video_file=video_file,
                caption=caption,
                thumbnail=self._prepare_thumbnail(video_metadata)
            )
            
            if post_id:
                logger.info(f"Posted to Instagram successfully: {post_id}")
                return post_id
            else:
                logger.error("Failed to post to Instagram")
                return None
                
        except Exception as e:
            logger.error(f"Error posting to Instagram: {e}")
            return None
    
    def post_to_wordpress(self, video_metadata):
        """
        Post video to WordPress with YouTube embed
        """
        wp_url = self.config.get('wordpress_url')
        wp_username = self.config.get('wordpress_username')
        wp_password = self.config.get('wordpress_app_password')
        
        if not all([wp_url, wp_username, wp_password]):
            logger.warning("WordPress credentials not fully configured")
            return None
        
        try:
            logger.info(f"Posting to WordPress: {video_metadata['title']}")
            
            title = video_metadata.get('title', 'Untitled')
            description = video_metadata.get('description', '')
            youtube_url = video_metadata.get('url')
            
            # Build post description with YouTube info
            post_description = description
            if self.config.get('add_hashtags'):
                post_description += f"\n\n{self.config.get('hashtags', '')}"
            
            # Include YouTube video link if configured
            youtube_link = ""
            if self.config.get('wordpress_include_youtube_link') and youtube_url:
                youtube_link = f"\n\n📺 Watch on YouTube: {youtube_url}"
                post_description += youtube_link
            
            # Create WordPress post with YouTube embed
            post_result = wordpress_create_post(
                title=title,
                content=post_description,
                wp_url=wp_url,
                username=wp_username,
                app_password=wp_password,
                youtube_url=youtube_url if self.config.get('wordpress_include_youtube_link') else None,
                status="publish",
                verify_ssl=False  # Allow self-signed certificates
            )
            
            if post_result and 'id' in post_result:
                post_id = post_result['id']
                post_url = post_result.get('link', wp_url)
                logger.info(f"Posted to WordPress successfully (ID: {post_id}): {post_url}")
                return post_id
            else:
                logger.error("Failed to create WordPress post")
                return None
                
        except WordPressUploadError as e:
            logger.error(f"WordPress upload error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error posting to WordPress: {e}")
            return None
    
    def process_video(self, video_metadata):
        """
        Process and auto-post a video
        """
        try:
            video_id = video_metadata['video_id']
            video_url = video_metadata['url']
            
            logger.info(f"Processing video: {video_metadata['title']}")
            
            # Determine video format to download
            duration = video_metadata.get('duration', 0)
            
            if duration <= 60:
                # YouTube Shorts (up to 60 seconds) - download as-is
                format_spec = 'best[height<=1080]/best'
                logger.info(f"Detected YouTube Short ({duration}s)")
            else:
                # Regular YouTube video - may need processing
                format_spec = 'best[height<=1080]/best'
                logger.info(f"Detected regular YouTube video ({duration}s)")
            
            # Download video
            video_file = self.youtube_fetcher.download_video(video_url, format_spec)
            
            if not video_file:
                logger.error(f"Failed to download video: {video_url}")
                return False
            
            logger.info(f"Downloaded video: {video_file}")
            
            posted = False
            
            # Post to Facebook
            if self.config.get('auto_post_facebook'):
                fb_post_id = self.post_to_facebook(video_file, video_metadata)
                if fb_post_id:
                    self.youtube_fetcher.mark_as_posted(video_id, 'facebook', fb_post_id)
                    posted = True
            
            # Post to Instagram
            if self.config.get('auto_post_instagram'):
                ig_post_id = self.post_to_instagram(video_file, video_metadata)
                if ig_post_id:
                    self.youtube_fetcher.mark_as_posted(video_id, 'instagram', ig_post_id)
                    posted = True
            
            # Post to WordPress (includes YouTube embed/link)
            if self.config.get('auto_post_wordpress'):
                wp_post_id = self.post_to_wordpress(video_metadata)
                if wp_post_id:
                    self.youtube_fetcher.mark_as_posted(video_id, 'wordpress', wp_post_id)
                    posted = True
            
            if posted:
                logger.info(f"Successfully posted video: {video_metadata['title']}")
            else:
                logger.warning(f"Video processed but not posted: {video_metadata['title']}")
            
            # Optional: Delete downloaded file after posting
            # os.remove(video_file)
            
            return posted
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return False
    
    def fetch_and_post(self, max_videos=5):
        """
        Fetch new videos and auto-post them
        """
        channel_url = self.config.get('youtube_channel')
        
        if not channel_url:
            logger.error("YouTube channel URL not configured")
            return 0
        
        logger.info(f"Fetching new videos from: {channel_url}")
        
        new_videos = self.youtube_fetcher.get_new_videos(channel_url, max_videos)
        
        if not new_videos:
            logger.info("No new videos found")
            return 0
        
        logger.info(f"Found {len(new_videos)} new videos to post")
        
        posted_count = 0
        for video in new_videos:
            if self.process_video(video):
                posted_count += 1
            time.sleep(2)  # Delay between posts to avoid rate limiting
        
        logger.info(f"Posted {posted_count}/{len(new_videos)} videos")
        return posted_count
    
    def run_daemon(self, interval=None):
        """
        Run auto-poster as daemon
        Periodically checks for new videos and posts them
        """
        interval = interval or self.config.get('check_interval', 300)
        
        logger.info(f"Starting YouTube Auto-Poster daemon (check interval: {interval}s)")
        
        try:
            while True:
                try:
                    logger.info(f"Checking for new videos... ({datetime.now()})")
                    self.fetch_and_post()
                except Exception as e:
                    logger.error(f"Error in daemon loop: {e}")
                
                logger.info(f"Next check in {interval} seconds")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Auto-Poster daemon stopped by user")
        except Exception as e:
            logger.error(f"Daemon error: {e}")
    
    def set_config(self, config_dict):
        """Update configuration"""
        self.config.update(config_dict)
        logger.info("Configuration updated")


# Example usage
if __name__ == "__main__":
    # Check/install yt-dlp
    if not check_yt_dlp_installed():
        print("yt-dlp not found. Installing...")
        if not install_yt_dlp():
            print("Failed to install yt-dlp")
            exit(1)
    
    # Initialize auto-poster
    auto_poster = YouTubeAutoPoster()
    
    # Configure (update as needed)
    auto_poster.set_config({
        'youtube_channel': 'https://www.youtube.com/@YOUR_CHANNEL',
        'auto_post_facebook': True,
        'auto_post_instagram': True,
    })
    
    # Option 1: Fetch and post once
    print("Fetching and posting videos...")
    posted = auto_poster.fetch_and_post(max_videos=5)
    print(f"Posted {posted} videos")
    
    # Option 2: Run as daemon (uncomment to enable)
    # auto_poster.run_daemon(interval=300)  # Check every 5 minutes

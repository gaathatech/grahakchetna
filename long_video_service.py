"""
Long-form YouTube video generation service (8-12 minutes, 1920x1080 horizontal).

Features:
- Clean 1920x1080 horizontal format optimized for YouTube
- Background video from assets/bg.mp4
- Lower-third section titles with smooth transitions
- Background music at low volume
- Logo/anchor overlay
- Professional layout with proper spacing
- Export to videos/long/ folder
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
import tempfile
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, ColorClip, 
    CompositeVideoClip, CompositeAudioClip, concatenate_videoclips, TextClip
)
from moviepy.audio.fx import all as afx
from PIL import Image, ImageDraw, ImageFont
import textwrap
import requests
import urllib.request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1920x1080 horizontal format
LONG_WIDTH = 1920
LONG_HEIGHT = 1080

VIDEOS_DIR = "videos"
LONG_VIDEOS_DIR = os.path.join(VIDEOS_DIR, "long")
VIDEO_MANIFEST = os.path.join(VIDEOS_DIR, "manifest.json")

# Colors
COLOR_PRIMARY_RED = (220, 20, 60)     # Crimson red
COLOR_DARK_RED = (139, 0, 0)          # Dark red
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_SHADOW = (0, 0, 0)
COLOR_OVERLAY_BG = (0, 0, 0)

# Font paths (reuse from existing setup)
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

def get_font(fontsize, bold=False):
    """Get available font, checking multiple paths."""
    paths = FONT_PATHS
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, fontsize)
            except Exception:
                continue
    return ImageFont.load_default()


def fetch_image_from_pexels(headline, dimension=400):
    """
    Fetch a relevant image from Pexels API based on headline.
    
    Args:
        headline: Topic/keywords to search for
        dimension: Image dimension for green screen (400x400 default)
    
    Returns:
        str: Path to downloaded image file, or None if failed
    """
    try:
        pexels_api_key = os.getenv("PEXELS_API_KEY")
        if not pexels_api_key:
            logger.warning("PEXELS_API_KEY not set in .env")
            return None
        
        # Extract main keywords from headline (first few words)
        keywords = " ".join(headline.split()[:3])
        
        logger.info(f"🔍 Fetching Pexels image for: {keywords}")
        
        # Search Pexels API
        headers = {"Authorization": pexels_api_key}
        params = {
            "query": keywords,
            "per_page": 1,
            "page": 1
        }
        
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code != 200:
            logger.warning(f"Pexels API error: {response.status_code}")
            return None
        
        data = response.json()
        if not data.get("photos"):
            logger.warning(f"No images found for: {keywords}")
            return None
        
        # Get the first image
        photo = data["photos"][0]
        image_url = photo["src"]["large"]
        
        logger.info(f"✓ Found image: {photo['photographer']} - {image_url}")
        
        # Download and save image
        os.makedirs("uploads", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"pexels_{timestamp}_{photo['id']}.jpg"
        image_path = os.path.join("uploads", image_filename)
        
        urllib.request.urlretrieve(image_url, image_path)
        logger.info(f"✓ Image downloaded: {image_path}")
        
        return image_path
    
    except Exception as e:
        logger.warning(f"Failed to fetch Pexels image: {e}")
        return None


def create_ticker_text(text, fontsize=40, width=1000, duration=10):
    """
    Create a horizontally scrolling ticker text overlay.
    Text scrolls from right to left across the screen.
    
    Returns:
        (path_to_image, total_width)
    """
    font = get_font(fontsize, bold=True)
    
    # Calculate text size with extra padding
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Create image with extra width for scrolling
    img_width = text_width + 2000  # Extra space for scrolling effect
    img_height = text_height + 20
    
    img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw shadow
    draw.text((15, 12), text, font=font, fill=(*COLOR_SHADOW, 200))
    # Draw text
    draw.text((10, 10), text, font=font, fill=COLOR_TEXT_WHITE)
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(temp_file.name)
    temp_file.close()
    
    return temp_file.name, img_width


def create_green_screen_placeholder(width=400, height=400):
    """Create a green screen placeholder image."""
    img = Image.new("RGBA", (width, height), (0, 128, 0, 200))  # Semi-transparent green
    draw = ImageDraw.Draw(img)
    
    font = get_font(24, bold=True)
    
    # Add text instructions
    text = "GREEN SCREEN\nOVERLAY AREA"
    draw.text((50, height//2 - 40), text, font=font, fill=(200, 200, 200, 255), anchor="lm")
    
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(temp_file.name)
    temp_file.close()
    
    return temp_file.name


def load_green_screen_media(media_path, width=400, height=400, duration=None):
    """
    Load user-provided green screen media (image or video).
    Returns a clip scaled to green screen dimensions.
    """
    try:
        if not os.path.exists(media_path):
            logger.warning(f"Green screen media not found: {media_path}")
            return create_green_screen_placeholder(width, height), None
        
        # Check if it's a video or image
        if media_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            # Load as video
            clip = VideoFileClip(media_path)
            if duration:
                if clip.duration > duration:
                    clip = clip.subclip(0, duration)
                else:
                    # Loop video if too short
                    from moviepy.video.fx import loop
                    clip = loop.loop(clip, duration=duration)
            clip = clip.resize((width, height))
            logger.info(f"✓ Green screen video loaded: {width}x{height}")
            return clip, "video"
        else:
            # Load as image
            clip = ImageClip(media_path)
            clip = clip.resize((width, height))
            if duration:
                clip = clip.set_duration(duration)
            logger.info(f"✓ Green screen image loaded: {width}x{height}")
            return clip, "image"
    
    except Exception as e:
        logger.warning(f"Failed to load green screen media: {e}")
        return create_green_screen_placeholder(width, height), None


def create_lower_third(section_title, fontsize=48):
    """
    Create a lower-third title overlay image.
    
    Returns:
        tuple: (path_to_image, height)
    """
    # Dimension for lower-third bar
    bar_width = LONG_WIDTH
    bar_height = 100
    margin = 40
    
    # Create image with transparency
    img = Image.new("RGBA", (bar_width, bar_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw colored bar on the left side (lower-third style)
    bar_color = (*COLOR_PRIMARY_RED, 230)
    draw.rectangle([0, 0, 600, bar_height], fill=bar_color)
    
    # Draw text
    font = get_font(fontsize, bold=True)
    text_color = COLOR_TEXT_WHITE
    
    # Draw shadow for depth
    draw.text(
        (margin + 2, bar_height // 2 - fontsize // 2 + 2),
        section_title,
        font=font,
        fill=(*COLOR_SHADOW, 180)
    )
    
    # Draw main text
    draw.text(
        (margin, bar_height // 2 - fontsize // 2),
        section_title,
        font=font,
        fill=text_color
    )
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(temp_file.name)
    temp_file.close()
    
    return temp_file.name, bar_height


def extend_or_loop_video(video_path, target_duration):
    """
    Load a video and extend it to target duration by looping.
    
    Args:
        video_path: Path to video file
        target_duration: Target duration in seconds
    
    Returns:
        VideoFileClip of target duration
    """
    try:
        if not os.path.exists(video_path):
            logger.warning(f"Video file not found: {video_path}")
            # Create a black background fallback
            return ColorClip(
                (LONG_WIDTH, LONG_HEIGHT), 
                color=(20, 20, 20)
            ).set_duration(target_duration)
        
        video = VideoFileClip(video_path)
        logger.info(f"Loaded background video: {video.duration:.1f}s")
        
        # Resize to match dimensions
        video = video.resize((LONG_WIDTH, LONG_HEIGHT))
        
        # If too short, loop it
        if video.duration < target_duration:
            from moviepy.video.fx import loop
            video = loop.loop(video, duration=target_duration)
        else:
            video = video.subclip(0, target_duration)
        
        return video
    
    except Exception as e:
        logger.error(f"Failed to load background video: {e}")
        return ColorClip(
            (LONG_WIDTH, LONG_HEIGHT), 
            color=(20, 20, 20)
        ).set_duration(target_duration)


def generate_long_video(
    headline,
    description,
    audio_path,
    language="english",
    output_path=None,
    sections_timing=None,
    green_screen_media=None
):
    """
    Generate a long-form YouTube video (8-12 minutes, 1920x1080 horizontal).
    
    Args:
        headline: Video headline
        description: Video description
        audio_path: Path to narration audio
        language: Script language
        output_path: Output video path (optional)
        sections_timing: dict of section timings {section_name: seconds} (optional)
        green_screen_media: Path to user-provided green screen media (image or video)
    
    Returns:
        str: Path to generated video
    """
    
    # Setup output directory
    os.makedirs(LONG_VIDEOS_DIR, exist_ok=True)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        output_path = os.path.join(LONG_VIDEOS_DIR, f"long_video_{timestamp}.mp4")
    
    logger.info(f"Generating long-form video: {os.path.basename(output_path)}")
    
    # Load and validate audio
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    voice = AudioFileClip(audio_path)
    duration = voice.duration
    logger.info(f"Audio duration: {duration:.1f} seconds ({int(duration // 60)}m {int(duration % 60)}s)")
    
    # ========== BUILD VIDEO COMPOSITION ==========
    
    # 1. Background video - Use long video background.mp4
    bg_path = "long video background.mp4"
    if not os.path.exists(bg_path):
        bg_path = "assets/bg.mp4"  # Fallback
        logger.warning(f"Long video background not found, using fallback: {bg_path}")
    
    background = extend_or_loop_video(bg_path, duration)
    logger.info(f"✓ Background video ready: {LONG_WIDTH}x{LONG_HEIGHT}")
    
    # 2. Overlay for depth (semi-transparent dark)
    overlay = (
        ColorClip((LONG_WIDTH, LONG_HEIGHT), color=COLOR_OVERLAY_BG)
        .set_opacity(0.25)
        .set_duration(duration)
    )
    
    # 3. Logo in top-right corner
    logo_path = "static/logo.jpg"
    logo_clip = None
    if os.path.exists(logo_path):
        try:
            logo_clip = (
                ImageClip(logo_path)
                .resize(height=80)
                .set_position((LONG_WIDTH - 120, 20))
                .set_duration(duration)
            )
            logger.info("✓ Logo overlay loaded")
        except Exception as e:
            logger.warning(f"Failed to load logo: {e}")
    
    # 4. Top title bar (headline)
    title_bar_height = 120
    title_bar = (
        ColorClip((LONG_WIDTH, title_bar_height), color=COLOR_PRIMARY_RED)
        .set_opacity(0.85)
        .set_duration(duration)
    )
    
    # Title text
    font_large = get_font(48, bold=True)
    
    # Create title text image 
    title_img = Image.new("RGBA", (LONG_WIDTH - 40, title_bar_height), (0, 0, 0, 0))
    title_draw = ImageDraw.Draw(title_img)
    
    # Wrap headline text
    words = headline.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_text = " ".join(current_line)
        bbox = font_large.getbbox(test_text)
        if (bbox[2] - bbox[0]) > (LONG_WIDTH - 80):
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    
    if current_line:
        lines.append(" ".join(current_line))
    
    # Draw title within bar
    y_pos = (title_bar_height - len(lines) * 45) // 2
    for line in lines[:2]:  # Limit to 2 lines
        title_draw.text((20, y_pos), line, font=font_large, fill=COLOR_TEXT_WHITE)
        y_pos += 50
    
    title_temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    title_img.save(title_temp.name)
    title_temp.close()
    
    title_text_clip = (
        ImageClip(title_temp.name)
        .set_duration(duration)
        .set_position((20, 10))
    )
    
    # 5. Section title lower-thirds (shown at timed intervals)
    section_clips = []
    
    default_sections = {
        "Hook": duration * 0.05,           # 5% through
        "Background Context": duration * 0.15,   # 15%
        "What Happened": duration * 0.35,  # 35%
        "Why It Matters": duration * 0.55, # 55%
        "Future Implications": duration * 0.75, # 75%
        "Strong Closing": duration * 0.90, # 90%
    }
    
    if sections_timing is None:
        sections_timing = default_sections
    
    for section_name, start_time in sections_timing.items():
        if start_time >= duration:
            continue
        
        # Each section title appears for 3 seconds
        section_duration = min(3, duration - start_time)
        
        section_img_path, _ = create_lower_third(section_name)
        section_clip = (
            ImageClip(section_img_path)
            .set_duration(section_duration)
            .set_start(start_time)
            .set_position((0, LONG_HEIGHT - 120))
            .crossfadeout(0.5)
        )
        section_clips.append(section_clip)
        logger.info(f"  - Section '{section_name}' at {start_time:.1f}s")
    
    # 6. Bottom info bar
    info_bar_height = 100
    info_bar = (
        ColorClip((LONG_WIDTH, info_bar_height), color=COLOR_DARK_RED)
        .set_opacity(0.8)
        .set_position((0, LONG_HEIGHT - info_bar_height))
        .set_duration(duration)
    )
    
    # Info text
    font_info = get_font(32, bold=False)
    info_img = Image.new("RGBA", (LONG_WIDTH - 40, info_bar_height), (0, 0, 0, 0))
    info_draw = ImageDraw.Draw(info_img)
    info_draw.text(
        (20, info_bar_height // 2 - 16),
        f"Grahak Chetna AI News Studio | {headline[:60]}...",
        font=font_info,
        fill=COLOR_TEXT_WHITE
    )
    
    info_temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    info_img.save(info_temp.name)
    info_temp.close()
    
    info_clip = (
        ImageClip(info_temp.name)
        .set_duration(duration)
        .set_position((0, LONG_HEIGHT - info_bar_height))
    )
    
    # 7. Audio track (voice + background music)
    music_path = "assets/music.mp3"
    final_audio = voice
    
    if os.path.exists(music_path):
        try:
            music = AudioFileClip(music_path)
            if music.duration < duration:
                # Loop music to match duration
                from moviepy.video.fx import loop
                music = loop.loop(music, duration=duration)
            else:
                music = music.subclip(0, duration)
            
            # Reduce music volume (background)
            music = music.volumex(0.1)
            
            final_audio = CompositeAudioClip([music, voice])
            logger.info("✓ Background music mixed at 10% volume")
        except Exception as e:
            logger.warning(f"Failed to load background music: {e}")
    
    # ========== NEW ELEMENTS ==========
    
    # 8. GREEN SCREEN OVERLAY (left side - 400x400)
    green_screen_clips = []
    green_screen_width = 400
    green_screen_height = 400
    green_screen_x = 40  # Left margin
    green_screen_y = 180  # Below title bar
    
    if green_screen_media and os.path.exists(green_screen_media):
        try:
            gs_clip, gs_type = load_green_screen_media(green_screen_media, green_screen_width, green_screen_height, duration)
            gs_positioned = gs_clip.set_position((green_screen_x, green_screen_y))
            if gs_type == "video":
                gs_positioned = gs_positioned.set_duration(duration)
            else:
                gs_positioned = gs_positioned.set_duration(duration)
            green_screen_clips.append(gs_positioned)
            logger.info(f"✓ Green screen overlay added: {green_screen_width}x{green_screen_height}")
        except Exception as e:
            logger.warning(f"Failed to add green screen: {e}")
    else:
        try:
            # Add placeholder green screen
            gs_placeholder = create_green_screen_placeholder(green_screen_width, green_screen_height)
            gs_clip = ImageClip(gs_placeholder).set_duration(duration)
            gs_positioned = gs_clip.set_position((green_screen_x, green_screen_y))
            green_screen_clips.append(gs_positioned)
            logger.info("✓ Green screen placeholder added")
        except Exception as e:
            logger.warning(f"Failed to add green screen placeholder: {e}")
    
    # 9. BREAKING NEWS TICKER (bottom - scrolling text)
    ticker_clips = []
    try:
        # Create breaking news ticker text
        ticker_text = f"🔴 BREAKING NEWS: {headline} — {description}"
        ticker_img_path, ticker_width = create_ticker_text(ticker_text, fontsize=36, duration=int(duration))
        
        # Ticker bar background (dark with red accent)
        ticker_bar_height = 70
        ticker_bar = (
            ColorClip((LONG_WIDTH, ticker_bar_height), color=(20, 20, 20))
            .set_opacity(0.95)
            .set_position((0, LONG_HEIGHT - ticker_bar_height - 100))  # Above info bar
            .set_duration(duration)
        )
        ticker_clips.append(ticker_bar)
        
        # Red accent line
        red_accent = (
            ColorClip((LONG_WIDTH, 3), color=COLOR_PRIMARY_RED)
            .set_position((0, LONG_HEIGHT - ticker_bar_height - 100))
            .set_duration(duration)
        )
        ticker_clips.append(red_accent)
        
        # Scrolling ticker text - moves from right to left
        ticker_clip = ImageClip(ticker_img_path)
        # Calculate scroll duration (text moves across the screen)
        scroll_duration = max(10, duration * 0.5)  # Scroll takes at least 10 seconds
        
        # Create animation: start from right edge, scroll to left edge
        def scroll_position(t):
            return (LONG_WIDTH - (t / scroll_duration) * ticker_width, LONG_HEIGHT - ticker_bar_height - 80)
        
        ticker_text_clip = (
            ticker_clip
            .set_duration(scroll_duration)
            .set_position(lambda t: scroll_position(t))
        )
        
        # Loop ticker if duration is longer
        if scroll_duration < duration:
            remaining = duration - scroll_duration
            loop_count = int(remaining / scroll_duration) + 1
            ticker_loop_clips = [ticker_text_clip] * loop_count
            
            # Adjust timing for looped clips
            current_time = 0
            adjusted_clips = []
            for i, clip in enumerate(ticker_loop_clips[:loop_count]):
                if i == 0:
                    adjusted_clips.append(clip)
                else:
                    adjusted_clips.append(
                        clip
                        .set_start(i * scroll_duration)
                        .set_duration(min(scroll_duration, duration - current_time))
                    )
                current_time += scroll_duration
            ticker_clips.extend(adjusted_clips[1:])
        else:
            ticker_clips.append(ticker_text_clip)
        
        logger.info(f"✓ Breaking news ticker added (scroll: {scroll_duration:.1f}s)")
    except Exception as e:
        logger.warning(f"Failed to add breaking news ticker: {e}")
    
    # 10. SIDE SCROLLING TEXT (right side - like short videos)
    side_text_clips = []
    try:
        # Create scrolling text for description
        side_text = description
        side_text_img_path, text_height = create_ticker_text(side_text, fontsize=32, duration=int(duration))
        
        # Right side panel background (semi-transparent)
        right_panel_width = 400
        right_panel = (
            ColorClip((right_panel_width, LONG_HEIGHT), color=(0, 0, 0))
            .set_opacity(0.3)
            .set_position((LONG_WIDTH - right_panel_width, 0))
            .set_duration(duration)
        )
        side_text_clips.append(right_panel)
        
        # Vertical scrolling text (top to bottom on right side)
        side_text_clip = ImageClip(side_text_img_path)
        side_scroll_duration = max(12, duration * 0.6)
        
        def vertical_scroll_position(t):
            y = (t / side_scroll_duration) * (LONG_HEIGHT + text_height) - text_height
            return (LONG_WIDTH - right_panel_width + 20, y)
        
        side_text_positioned = (
            side_text_clip
            .set_duration(side_scroll_duration)
            .set_position(lambda t: vertical_scroll_position(t))
        )
        side_text_clips.append(side_text_positioned)
        
        # Loop side text if needed
        if side_scroll_duration < duration:
            remaining = duration - side_scroll_duration
            loop_count = int(remaining / side_scroll_duration) + 1
            current_time = side_scroll_duration
            
            for i in range(1, loop_count):
                side_text_loop = (
                    ImageClip(side_text_img_path)
                    .set_start(current_time)
                    .set_duration(min(side_scroll_duration, duration - current_time))
                    .set_position(lambda t, start_t=current_time: vertical_scroll_position(t - start_t))
                )
                side_text_clips.append(side_text_loop)
                current_time += side_scroll_duration
        
        logger.info(f"✓ Side scrolling text added (scroll: {side_scroll_duration:.1f}s)")
    except Exception as e:
        logger.warning(f"Failed to add side scrolling text: {e}")
    
    # 8. Compose all clips
    clips_to_compose = [
        background,
        overlay,
        title_bar,
        title_text_clip,
    ]
    
    # Add green screen overlay
    clips_to_compose.extend(green_screen_clips)
    
    # Add ticker components
    clips_to_compose.extend(ticker_clips)
    
    # Add side scrolling text
    clips_to_compose.extend(side_text_clips)
    
    # Add info bar and logo
    clips_to_compose.extend([info_bar, info_clip])
    
    if logo_clip:
        clips_to_compose.append(logo_clip)
    
    # Add section clips
    clips_to_compose.extend(section_clips)
    
    # Create composite video
    final_video = CompositeVideoClip(clips_to_compose).set_audio(final_audio)
    
    # 9. Add ending screen (3 seconds)
    try:
        ending_duration = 3
        ending_bg = ColorClip((LONG_WIDTH, LONG_HEIGHT), color=(0, 0, 0)).set_duration(ending_duration)
        
        ending_font = get_font(72, bold=True)
        ending_img = Image.new("RGBA", (LONG_WIDTH, LONG_HEIGHT), (0, 0, 0, 0))
        ending_draw = ImageDraw.Draw(ending_img)
        ending_draw.text(
            (LONG_WIDTH // 2 - 300, LONG_HEIGHT // 2 - 100),
            "Thank You\nGrahak Chetna",
            font=ending_font,
            fill=COLOR_TEXT_WHITE
        )
        
        ending_temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        ending_img.save(ending_temp.name)
        ending_temp.close()
        
        ending_text = (
            ImageClip(ending_temp.name)
            .set_duration(ending_duration)
        )
        
        ending_clip = CompositeVideoClip([ending_bg, ending_text])
        final_video = concatenate_videoclips([final_video, ending_clip])
    except Exception as e:
        logger.warning(f"Failed to add ending screen: {e}")
    
    # 10. Write output video
    logger.info(f"Rendering video to: {output_path}")
    
    try:
        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            verbose=False,
            logger=None
        )
        logger.info(f"✓ Video generated successfully: {os.path.basename(output_path)}")
        
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"  File size: {file_size_mb:.2f} MB")
        
        return output_path
    
    except Exception as e:
        logger.error(f"Failed to render video: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test parameters
    test_headline = "Why Hungary Blocked EU Sanctions"
    test_description = "Hungary blocks EU sanctions package against Russia before war anniversary."
    
    # You would normally pass a real audio file here
    import sys
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        if os.path.exists(audio_file):
            print(f"Testing long-form video with audio: {audio_file}")
            try:
                output = generate_long_video(test_headline, test_description, audio_file)
                print(f"\n✓ Video generated: {output}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"Audio file not found: {audio_file}")
    else:
        print("Usage: python long_video_service.py <audio_file>")

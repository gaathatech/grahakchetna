from moviepy.editor import *
from moviepy.audio.fx import all as afx
from PIL import Image, ImageDraw, ImageFont
import textwrap
import tempfile
import os
import subprocess

Image.ANTIALIAS = Image.Resampling.LANCZOS

WIDTH = 1080
HEIGHT = 1920

# Enhanced professional colors
COLOR_ACCENT_RED = (220, 20, 60)     # Crimson red for better contrast
COLOR_ACCENT_DARK_RED = (139, 0, 0)  # Dark red
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_SHADOW = (0, 0, 0)
COLOR_OVERLAY_BG = (0, 0, 0)

# Try to find fonts on common Linux locations
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

# Gujarati and Indian script fonts
INDIC_FONT_PATHS = [
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    "/usr/share/fonts/truetype/droid/DroidSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansGujarati-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSerifGujarati-Regular.ttf",
    "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
    "/usr/share/fonts/truetype/lohit-gujarati/Lohit-Gujarati.ttf",
    "/usr/share/fonts/truetype/mangal.ttf",
]

# Map language to font paths
LANGUAGE_FONT_MAP = {
    "gujarati": INDIC_FONT_PATHS,
    "hindi": INDIC_FONT_PATHS,
    "default": FONT_PATHS
}

def get_font(bold=False, language="default"):
    """Get available font, fallback to default if not found"""
    # Try configured paths first
    font_paths = LANGUAGE_FONT_MAP.get(language, FONT_PATHS)
    for path in font_paths:
        if os.path.exists(path):
            return path

    # If not found, try system font listing via fc-list (if available)
    try:
        fc_list = subprocess.check_output(["fc-list", "--format", "%{file}\n"]).decode(errors="ignore")
        lines = [l.strip() for l in fc_list.splitlines() if l.strip()]

        # Language-specific keywords to look for in font file paths
        keywords = []
        lang = (language or "").lower()
        if "gujarati" in lang:
            keywords = ["gujarati", "noto", "lohit", "guj", "gujr"]
        elif "hindi" in lang or "devanagari" in lang:
            keywords = ["devanagari", "noto", "mangal", "lohit", "dev"]
        else:
            keywords = ["noto", "dejavu", "liberation", "freefont"]

        for l in lines:
            low = l.lower()
            for kw in keywords:
                if kw in low:
                    if os.path.exists(l):
                        return l
    except Exception:
        # fc-list not available or failed — ignore
        pass

    return None  # Use default PIL font if no font file found

FONT_REGULAR = get_font(bold=False)
FONT_BOLD = get_font(bold=True)
FONT_GUJARATI = get_font(bold=False, language="gujarati")
FONT_GUJARATI_BOLD = get_font(bold=True, language="gujarati")

def add_text_shadow(draw, text, position, font, shadow_offset=3):
    """Helper to add text shadow for better readability"""
    x, y = position
    # Draw shadow
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(*COLOR_SHADOW, 200))

def create_text_image(text, fontsize=65, color=(255, 255, 255), bold=False, max_width=620, language="en", add_shadow=True):
    """Create text image using PIL instead of ImageMagick with optional shadow"""
    if language in ["gujarati", "hindi"]:
        font_path = FONT_GUJARATI_BOLD if bold else FONT_GUJARATI
    else:
        font_path = FONT_BOLD if bold else FONT_REGULAR
    
    try:
        if font_path:
            font = ImageFont.truetype(font_path, fontsize)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Wrap text using actual pixel measurements
    lines = []
    words = text.split()
    current_line = ""
    
    for word in words:
        test_line = current_line + word + " "
        bbox = font.getbbox(test_line)
        line_width = bbox[2] - bbox[0]
        
        if line_width > max_width and current_line:
            lines.append(current_line.strip())
            current_line = word + " "
        else:
            current_line = test_line
    
    if current_line:
        lines.append(current_line.strip())
    
    # Calculate image size with proper spacing
    line_height = fontsize + 10
    shadow_offset = 3 if add_shadow else 0
    img_height = len(lines) * line_height + 20 + shadow_offset
    img_width = max_width + 40 + shadow_offset
    
    # Create image with transparency
    img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw text with shadow
    y = 10
    for line in lines:
        if add_shadow:
            draw.text((10 + shadow_offset, y + shadow_offset), line, font=font, fill=(*COLOR_SHADOW, 180))
        draw.text((10, y), line, font=font, fill=(*color, 255))
        y += line_height
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(temp_file.name)
    temp_file.close()
    
    return temp_file.name, img_height


def create_ticker_text_image(text, fontsize=50, color=(255, 255, 255), bold=True, language="en"):
    """Create a single-line text image for ticker scrolling with shadow"""
    if language in ["gujarati", "hindi"]:
        font_path = FONT_GUJARATI_BOLD if bold else FONT_GUJARATI
    else:
        font_path = FONT_BOLD if bold else FONT_REGULAR
    
    try:
        if font_path:
            font = ImageFont.truetype(font_path, fontsize)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Create image with extra width for scrolling
    img_height = fontsize + 30
    img_width = max(1200, len(text) * 20)  # Extra width for scrolling
    shadow_offset = 3
    
    # Create image
    img = Image.new("RGBA", (img_width + shadow_offset, img_height + shadow_offset), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw shadow
    draw.text((20 + shadow_offset, 15 + shadow_offset), text, font=font, fill=(*COLOR_SHADOW, 180))
    # Draw text
    draw.text((20, 15), text, font=font, fill=(*color, 255))
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(temp_file.name)
    temp_file.close()
    
    return temp_file.name, img_height


def generate_video(title, description, audio_path, language="en", use_female_anchor=True, output_path=None):

    if output_path is None:
        output_path = "static/final_video.mp4"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    voice = AudioFileClip(audio_path)
    duration = voice.duration

    # Background
    bg = (
        VideoFileClip("assets/bg.mp4")
        .resize((WIDTH, HEIGHT))
        .subclip(0, duration)
    )

    overlay = (
        ColorClip((WIDTH, HEIGHT), color=COLOR_OVERLAY_BG)
        .set_opacity(0.4)
        .set_duration(duration)
    )

    # Anchor - static position
    anchor = (
        ImageClip("static/anchor.png")
        .resize(height=750)
        .set_position((40, "center"))
        .set_duration(duration)
    )

    # Logo
    logo = (
        ImageClip("static/logo.jpg")
        .resize(height=100)
        .set_position(("center", 40))
        .set_duration(duration)
    )

    # ============= TOP RED HEADLINE BAR =============
    headline_bar_height = 120
    headline_bar_y = 150
    
    # Red background bar with gradient effect (simulated with darker red border)
    headline_bar = (
        ColorClip((WIDTH, headline_bar_height), color=COLOR_ACCENT_RED)
        .set_position(("center", headline_bar_y))
        .set_duration(duration)
    )
    
    # Add dark red border effect (creates depth)
    headline_bar_border = (
        ColorClip((WIDTH, 3), color=COLOR_ACCENT_DARK_RED)
        .set_position(("center", headline_bar_y + headline_bar_height - 3))
        .set_duration(duration)
    )

    # Create scrolling ticker text
    ticker_img_path, ticker_height = create_ticker_text_image(
        title,
        fontsize=50,
        color=(255, 255, 255),
        bold=True,
        language=language
    )
    
    # Create scrolling animation - text moves from right to left
    ticker_clip = ImageClip(ticker_img_path).set_duration(duration)
    
    # Animation function for scrolling
    def make_ticker_position(t):
        # Speed: move across screen in duration seconds, then loop
        scroll_speed = WIDTH + 1200  # Total distance to scroll
        x_pos = WIDTH - (t % duration) * (scroll_speed / duration)
        return (x_pos, headline_bar_y + 35)
    
    ticker_clip = ticker_clip.set_position(make_ticker_position)

    # ============= DESCRIPTION (CENTER-RIGHT AREA) =============
    text_x = 420
    text_start_y = 350
    text_width = 600
    # Maximum height: breaking news bar starts at HEIGHT - 220
    max_text_height = (HEIGHT - 220) - text_start_y - 50  # 50px buffer

    # Description (dynamic positioning) - smaller font to fit better
    desc_img_path, desc_height = create_text_image(
        description,
        fontsize=40,
        color=(255, 255, 255),
        bold=False,
        max_width=text_width,
        language=language
    )
    
    # If text is too tall, scale it down
    if desc_height > max_text_height:
        desc_clip = ImageClip(desc_img_path).set_duration(duration)
        scale_factor = max_text_height / desc_height
        desc_clip = desc_clip.resize(scale_factor)
    else:
        desc_clip = ImageClip(desc_img_path).set_duration(duration)
    
    desc_clip = desc_clip.set_position((text_x, text_start_y))

    # ============= BOTTOM BREAKING NEWS BAR =============
    breaking_bar_y = HEIGHT - 220

    breaking_bar = (
        ColorClip((WIDTH, 130), color=COLOR_ACCENT_RED)
        .set_position(("center", breaking_bar_y))
        .set_duration(duration)
    )
    
    # Add dark red border for depth
    breaking_bar_border = (
        ColorClip((WIDTH, 3), color=COLOR_ACCENT_DARK_RED)
        .set_position(("center", breaking_bar_y))
        .set_duration(duration)
    )

    breaking_text_img_path, _ = create_text_image(
        "BREAKING NEWS",
        fontsize=55,
        color=(255, 255, 255),
        bold=True,
        max_width=WIDTH - 100
    )
    breaking_text = ImageClip(breaking_text_img_path)
    breaking_text = (
        breaking_text
        .set_position(("center", breaking_bar_y + 25))
        .set_duration(duration)
    )

    # AI label
    ai_label_img_path, _ = create_text_image(
        "AI Generated Anchor",
        fontsize=28,
        color=(255, 255, 255),
        bold=False,
        max_width=WIDTH - 100
    )
    ai_label = ImageClip(ai_label_img_path)
    ai_label = (
        ai_label
        .set_position((20, HEIGHT - 60))
        .set_duration(duration)
    )

    # Background music (loop safe)
    music_clip = AudioFileClip("assets/music.mp3")

    if music_clip.duration < duration:
        music = afx.audio_loop(music_clip, duration=duration)
    else:
        music = music_clip.subclip(0, duration)

    music = music.volumex(0.08)

    final_audio = CompositeAudioClip([music, voice])

    main_video = CompositeVideoClip(
        [
            bg,
            overlay,
            anchor,
            logo,
            headline_bar,
            headline_bar_border,
            ticker_clip,
            desc_clip,
            breaking_bar,
            breaking_bar_border,
            breaking_text,
            ai_label,
        ]
    ).set_audio(final_audio)

    # Ending screen (3 sec)
    ending_duration = 3

    ending_bg = (
        ColorClip((WIDTH, HEIGHT), color=(0, 0, 0))
        .set_duration(ending_duration)
    )

    ending_text_img_path, _ = create_text_image(
        "Presented by\nGrahak Chetna",
        fontsize=75,
        color=(255, 255, 255),
        bold=True,
        max_width=WIDTH - 100
    )
    ending_text = ImageClip(ending_text_img_path)
    ending_text = (
        ending_text
        .set_position("center")
        .set_duration(ending_duration)
    )

    ending_clip = CompositeVideoClip(
        [ending_bg, ending_text]
    ).set_duration(ending_duration)

    final = concatenate_videoclips([main_video, ending_clip])

    # Use the provided output_path or default to static/final_video.mp4
    if not output_path:
        output_path = "static/final_video.mp4"

    final.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
    )

    return output_path

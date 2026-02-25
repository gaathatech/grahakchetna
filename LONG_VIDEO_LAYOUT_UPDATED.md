# Long Video Layout Structure (Updated)

## Overview

The long video layout has been updated with a dynamic right-side content box that intelligently displays either media or headline text based on availability. The layout is optimized for 9:16 vertical format (1080×1920).

## Layout Sections

### 1. **Background** (Full Screen)
- **Location:** Behind all elements
- **File:** `assets/bg.mp4` or `shorts background.png`
- **Fallback:** Auto-loops video background
- **Opacity:** 15% overlay on top for text contrast

### 2. **Anchor** (LEFT SIDE)
- **Position:** Left side, lower middle area
- **Image:** `static/anchor.png`
- **Height:** 750px (resized)
- **X Position:** 40px from left edge
- **Y Position:** 450px from top
- **Duration:** Full video duration
- **Notes:** Remains static on LEFT side, does not move

### 3. **Logo** (TOP RIGHT)
- **Position:** Top right corner
- **Image:** `static/logo.jpg`
- **Height:** 100px (resized)
- **X Position:** 950px from left (WIDTH - 130)
- **Y Position:** 40px from top
- **Duration:** Full video duration

### 4. **Top Headline Bar (TICKER)**
- **Position:** Top center area (Y: 150px)
- **Height:** 120px
- **Background:** Crimson red (220, 20, 60)
- **Border:** Dark red bottom border (3px)
- **Content:** SCROLLING HEADLINE TEXT
- **Text Variable:** `headline` (sameas right-content-box)
- **Font Size:** 50px, Bold
- **Animation:** Horizontal scroll from right to left
- **Duration:** Loops continuously

### 5. **RIGHT SIDE DYNAMIC CONTENT BOX** (NEW - OPPOSITE ANCHOR)

#### Positioning
- **X Position:** 55% from left (approximately right side)
- **Y Position:** 20% from top
- **Width:** 45% of screen width
- **Min-Height:** 200px
- **Note:** Positioned on RIGHT side, opposite the LEFT anchor

#### Conditional Logic

```
IF media_path is provided AND media file exists:
    ├─ Load media (image or video)
    ├─ Resize to fit right-side width while maintaining aspect ratio
    ├─ Display media on right side
    └─ HIDE text box

ELSE (No media or failed to load):
    ├─ Create headline text box
    ├─ Use same `headline` variable as ticker
    ├─ Display on right side with styling
    └─ HIDE media container
```

#### Text Box Design (When No Media)
```css
.right-content-box {
    position: absolute;
    top: 20%;
    right: 5%;
    width: 45%;
    min-height: 200px;
    background: rgba(0, 0, 0, 0.45);          /* 45% opacity black */
    backdrop-filter: blur(6px);                /* Blur effect */
    border-radius: 12px;                       /* Rounded corners */
    padding: 25px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: left;
}

.right-content-box h2 {
    font-size: 32px;
    font-weight: bold;
    line-height: 1.4;
    color: #ffffff;
}
```

#### Media Display (When Available)
- **Border Radius:** 12px (rounded corners)
- **Background:** Transparent (shows video/image directly)
- **Maintains Aspect Ratio:** Resized proportionally to fit width
- **Video Loop:** Auto-loops if shorter than video duration

### 6. **Breaking News Bar** (BOTTOM)
- **Position:** Bottom (Y: HEIGHT - 220)
- **Height:** 130px
- **Background:** Crimson red
- **Border:** Dark red top border (3px)
- **Content:** "BREAKING NEWS" text
- **Font:** Bold, 55px
- **Animation:** Fixed text (ticker label)
- **Note:** Uses static "BREAKING NEWS" text

### 7. **AI Label** (BOTTOM LEFT)
- **Position:** Bottom left corner (20, HEIGHT - 60)
- **Text:** "AI Generated Anchor"
- **Font Size:** 28px
- **Color:** White
- **Duration:** Full video duration

### 8. **Ending Screen** (3 seconds)
- **Background:** Black
- **Text:** "Presented by\nGrahak Chetna"
- **Font Size:** 75px, Bold
- **Position:** Centered
- **Duration:** 3 seconds

## Key Features

### Headline Text Consistency
- **Single Variable:** `headline = title`
- **Used in Two Places:**
  1. Top ticker (scrolling)
  2. Right content box (static, when no media)
- **No Duplication:** Same text pulled from single variable

### Responsive Spacing
- **Anchor:** Positioned at (40, 450) - LEFT side
- **Right Box:** Positioned at (~550, ~380) - RIGHT side
- **No Overlap:** Clear separation between elements
- **Vertical Format:** 9:16 aspect ratio (1080×1920)

### Media Detection Logic
```python
has_media = media_path and os.path.exists(media_path)

if has_media:
    # Try to load and display media on right side
    # If load fails, fallback to text box
else:
    # Display headline text box on right side
```

## Function Signatures

### Main Video Generation
```python
def generate_video(
    title,           # Headline text for ticker and right box
    description,     # Description (kept for reference)
    audio_path,      # Narration audio
    language="en",   # Text language
    use_female_anchor=True,
    output_path=None,
    max_duration=None,
    media_path=None  # NEW: Optional media file for right side
)
```

### Long Video Wrapper
```python
def generate_long_video(
    stories,
    audio_path,
    language="en",
    output_path=None,
    max_duration=None,
    story_medias=None,
    media_path=None,  # NEW: Media path parameter
    green_screen_media=None
)
```

### Right Content Box Creation
```python
def create_right_content_box(
    text,              # Headline text to display
    fontsize=32,       # Font size
    color=(255, 255, 255),  # Text color (white)
    bold=True,
    language="en"      # Language for text rendering
)
# Returns: (image_path, width, height)
```

## Usage Examples

### Example 1: Generate Video with Media
```python
from video_service import generate_video

generate_video(
    title="Breaking News: Major Announcement",
    description="Full description here...",
    audio_path="path/to/audio.mp3",
    language="en",
    media_path="path/to/image.png"  # Shows image on right
)
```

### Example 2: Generate Video without Media (Text Box)
```python
from video_service import generate_video

generate_video(
    title="Breaking News: Major Announcement",
    description="Full description here...",
    audio_path="path/to/audio.mp3",
    language="en",
    media_path=None  # Shows headline text box on right
)
```

### Example 3: Long Video with Media
```python
from long_video_service import generate_long_video

generate_long_video(
    stories=[...],
    audio_path="path/to/audio.mp3",
    language="en",
    media_path="path/to/news_image.jpg"
)
```

## Layout Diagram

```
┌─────────────────────────────────────────────────────┐
│                                                       │
│  [LOGO] 🔴 HEADLINE TICKER SCROLLING ────────►      │
│  ┌─────────────────────────────────────────────┐   │
│  │                                               │   │
│  │  ┌──────────────┐  ┌─────────────────────┐  │   │
│  │  │              │  │   RIGHT CONTENT     │  │   │
│  │  │   ANCHOR     │  │   (Media or Text)   │  │   │
│  │  │              │  │                     │  │   │
│  │  │   LEFT       │  │   RIGHT SIDE        │  │   │
│  │  │   SIDE       │  │   45% width         │  │   │
│  │  │              │  │                     │  │   │
│  │  └──────────────┘  └─────────────────────┘  │   │
│  │                                               │   │
│  │  [BREAKING NEWS TICKER]                      │   │
│  │                                               │   │
│  └─────────────────────────────────────────────┘   │
│                                                       │
│  AI Generated Anchor                                 │
└─────────────────────────────────────────────────────┘
```

## Responsive Behavior

### Video Format: 9:16 (1080×1920)
- **Aspect Ratio:** Portrait (vertical)
- **Width:** 1080px
- **Height:** 1920px
- **Safe Areas:** Top 20% for right content, Bottom 220px for breaking bar

### Anchor (LEFT)
- **Width:** Auto (resized to 750px height)
- **Position:** Fixed at (40, 450)
- **Does NOT scale:** Maintains consistent position

### Right Content Box
- **Width:** 45% of screen (486px for 1080px width)
- **Height:** Dynamic (min 200px)
- **Position:** Maintains 20% top, 55% left margins
- **Spacing:** 5% right margin ensures no edge touching

## Technical Implementation

### Media Handling
1. **Check if media exists:** `os.path.exists(media_path)`
2. **Detect type:** File extension determines if image or video
3. **Load media:**
   - Image: Use ImageClip, resize to fit right-side width
   - Video: Use VideoFileClip, loop if shorter than duration
4. **Fallback:** If media fails to load, automatically uses text box

### Text Box Styling
- **Background:** 45% opacity black (rgba(0, 0, 0, 0.45))
- **Blur Effect:** 6px backdrop filter (CSS-like, simulated in image)
- **Border Radius:** 12px rounded corners
- **Padding:** 25px (25 pixels on all sides)
- **Text Alignment:** Left-aligned, vertically centered

## Notes

- ✅ **Anchor remains on LEFT side** - Does not overlap with right content
- ✅ **Headline text used in ticker AND right box** - No duplication of text variable
- ✅ **Dynamic media/text rendering** - Conditional based on media availability
- ✅ **Optimized for 9:16 format** - Vertical video layout with proper spacing
- ✅ **Responsive spacing** - Elements positioned with percentages and safe margins
- ✅ **Breaking news uses same headline** - Ticker bar pulls from same variable

## Files Modified

1. **`video_service.py`**
   - Added `create_right_content_box()` function
   - Updated `generate_video()` with media_path parameter
   - Added conditional media/text rendering logic
   - Updated CompositeVideoClip with right_content_clip

2. **`long_video_service.py`**
   - Updated `generate_long_video()` to accept media_path
   - Added media path forwarding to generate_video()

3. **`templates/long.html`**
   - Added `.right-content-box` CSS styling
   - Reference CSS for design consistency

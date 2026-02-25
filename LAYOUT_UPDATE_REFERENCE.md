# Long Video Layout Update - Quick Reference

## What Changed

### 1. New Dynamic Right-Side Content Box
- **Previously:** Always showed description text on right side
- **Now:** Shows media (image/video) if available, otherwise shows headline text

### 2. Unified Headline Variable
- **Previously:** Ticker used `title`, description was separate
- **Now:** Single `headline` variable used for both ticker AND right content box
- **Benefit:** No text duplication, consistent messaging

### 3. Media Support
- **New Parameter:** `media_path` in `generate_video()` and `generate_long_video()`
- **Auto-Detection:** Checks if media file exists
- **Fallback:** Automatically uses text box if media fails to load
- **Format Support:** Both images and videos supported

## Layout Positions (1080×1920)

| Element | Position | Size | Notes |
|---------|----------|------|-------|
| **Anchor** | LEFT (40, 450) | 750px H | Static, does not move |
| **Logo** | TOP-RIGHT (950, 40) | 100px H | Top corner |
| **Ticker** | TOP-CENTER (Y: 150) | 120px H | Scrolls left-to-right |
| **Right Content** | RIGHT (Y: 380) | 45% W, ≥200px H | Media or text |
| **Breaking Bar** | BOTTOM (Y: 1700) | 130px H | Static label |

## Conditional Rendering Logic

```python
# In video_service.py generate_video()

# Check media availability
has_media = media_path and os.path.exists(media_path)

if has_media:
    # Load and display media on right side
    right_content_clip = media_clip
    use_text_box = False
else:
    # Create headline text box
    right_content_clip = headline_text_box
    use_text_box = True
```

## CSS Styling for Right Content Box

```css
.right-content-box {
    position: absolute;
    top: 20%;
    right: 5%;
    width: 45%;
    min-height: 200px;
    background: rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(6px);
    border-radius: 12px;
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
}
```

## Function Call Examples

### Generate Video with Media
```python
from video_service import generate_video

result = generate_video(
    title="Breaking: Major News",
    description="Details here...",
    audio_path="audio.mp3",
    language="en",
    media_path="news_image.jpg"  # <-- New parameter
)
```

### Generate Video without Media (Text Only)
```python
result = generate_video(
    title="Breaking: Major News",
    description="Details here...",
    audio_path="audio.mp3",
    language="en"
    # media_path omitted → uses text box
)
```

### Long Video with Media
```python
from long_video_service import generate_long_video

result = generate_long_video(
    stories=[...],
    audio_path="audio.mp3",
    language="en",
    media_path="image.png"  # <-- Forwarded to generate_video
)
```

## Key Implementation Details

### create_right_content_box() Function
- **Location:** `video_service.py`
- **Purpose:** Creates headline text box for right side
- **Returns:** (image_path, width, height)
- **Design:**
  - 45% opacity black background
  - 6px blur effect (simulated in image)
  - 12px border radius
  - 25px padding
  - Left-aligned text

### Media Loading Logic
- **Images:** Resized to fit width, maintain aspect ratio
- **Videos:** 
  - Resized to fit width
  - Auto-looped if shorter than video duration
  - Truncated if longer than video duration

### Headline Variable Consistency
```python
# In generate_video()
headline = title  # Single variable

# Used in:
1. Ticker clip - create_ticker_text_image(headline)
2. Right content box - create_right_content_box(headline)
```

## Breaking Changes
- ⚠️ `generate_video()` now accepts optional `media_path` parameter
- ⚠️ Old description-only right side replaced with media/text conditional logic
- ✅ Backward compatible - works with existing calls (media_path defaults to None)

## Backward Compatibility
- ✅ Existing code without `media_path` still works
- ✅ Defaults to text box when media_path not provided
- ✅ Falls back to text box if media loading fails
- ✅ All existing parameters unchanged

## Files Modified
1. **video_service.py** - Core logic updates
2. **long_video_service.py** - Media path forwarding
3. **templates/long.html** - CSS styling added

## Testing Checklist

- [ ] Generate video without media (should show text box)
- [ ] Generate video with image media (should show image)
- [ ] Generate video with video media (should show video)
- [ ] Generate video with invalid media path (should fallback to text)
- [ ] Verify anchor doesn't overlap right content
- [ ] Verify ticker text matches right box text
- [ ] Verify responsive spacing in 9:16 format
- [ ] Test with multiple languages (en, gujarati, hindi)

## Performance Notes

- Media files should be pre-processed/optimized before passing
- Large videos may slow down composition time
- Images are recommended for faster rendering
- Media smaller than right-side width will be upscaled by default

## Future Enhancements

- [ ] Add media cropping/filtering options
- [ ] Support for animated GIFs
- [ ] Custom media positioning/alignment
- [ ] Media duration override in right side
- [ ] Fade in/out effects for media transition

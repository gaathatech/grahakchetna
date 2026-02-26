# Video Layout Adjustment UI - Complete Implementation

## Overview
A comprehensive video layout adjustment UI has been added to the Long Video generation page, allowing users to customize the video layout before generation.

## 🎨 Features Added

### 1. **Layout Customization Controls**
The new layout section includes the following adjustable parameters:

#### **Media Position** 
- 📌 Right Side (Default) - Media displays on the right side (45% width)
- 📌 Left Side - Media displays on the left side  
- 📌 Center/Full Width - Media centered or fills entire width

#### **Media Size**
- 🎬 Small (35%) - Compact media display
- 🎬 Medium (50%) - Balanced layout (Default)
- 🎬 Large (70%) - Large media with minimal text
- 🎬 Full Width (100%) - Fills entire video width

#### **Media Opacity**
- Adjustable from 0% to 100% using a slider
- Real-time opacity display
- Affects both image/video transparency and text box background

#### **Text Alignment**
- ⬅️ Left Aligned - Text positioned to the left
- ⬅️➡️ Center (Default) - Centered text layout
- ➡️ Right Aligned - Text positioned to the right

#### **Background Blur**
- None - Clear background
- Light (Default) - Subtle blur effect
- Medium - Moderate blur
- Heavy - Strong blur for better text contrast

### 2. **Quick Layout Presets**
Four pre-configured layouts for quick selection:

| Preset | Description | Settings |
|--------|-------------|----------|
| **Default** | Standard right-aligned media | Right, Medium (50%), 100%, Center, Light |
| **Cinema** | Full-width cinematic layout | Center, Full (100%), 80%, Center, Heavy |
| **Split** | Balanced split-screen layout | Left, Medium (50%), 100%, Right, None |
| **Focus** | Large focused media | Center, Large (70%), 90%, Center, Medium |

### 3. **Real-Time Layout Preview**
- Visual preview showing media position and size
- Updates in real-time as controls are adjusted
- Shows anchor on one side and media on the other
- Opacity visualization with transparency effect
- Text description of current layout settings

## 📝 Implementation Details

### Files Modified

#### 1. **templates/long.html**
- Added "Customize Video Layout" section before the form
- New CSS styling for layout controls and preview
- Interactive layout preview visualization
- JavaScript functions for layout management:
  - `updatePreview()` - Updates preview visualization
  - `applyLayoutPreset()` - Applies preset configurations
  - `syncLayoutHiddenFields()` - Syncs UI to form fields
- Event listeners for all layout controls
- Layout parameters added to form submission

#### 2. **video_service.py**
- Updated `generate_video()` function signature to accept layout parameters
- Implemented layout parameter handling:
  - `layout_mediaPosition` - Controls media placement
  - `layout_mediaSize` - Adjusts media dimensions
  - `layout_mediaOpacity` - Sets media transparency
  - `layout_textAlignment` - Aligns text content
  - `layout_backgroundBlur` - Applies background blur effect
- Media positioning logic updated to respect all layout parameters
- Opacity applied to media clips and text boxes

#### 3. **long_video_service.py**
- Updated `generate_long_video()` function to accept and pass layout parameters
- All layout parameters passed through to `video_service.generate_video()`

#### 4. **app.py**
- Updated `/generate-long` route to extract layout parameters from request
- Parameters extracted from both JSON and form data requests
- Layout parameters passed to `generate_long_video()` function
- Default values provided for all layout parameters

## 🔧 Layout Parameter Flow

```
templates/long.html (UI)
    ↓
    Stores in hidden form fields + syncLayoutHiddenFields()
    ↓
    FormData submission to /generate-long
    ↓
app.py (/generate-long route)
    ↓
    Extract layout parameters from request
    ↓
    Pass to generate_long_video()
    ↓
long_video_service.py (generate_long_video)
    ↓
    Temporarily set WIDTH/HEIGHT to 1920x1080
    ↓
    Pass layout parameters to video_service.generate_video()
    ↓
video_service.py (generate_video)
    ↓
    Apply layout parameters to video composition
    ↓
    Generate video with custom layout
```

## 📊 Usage Example

1. **Navigate to Long Video page** - Go to `/long` in the application
2. **Adjust Layout** - Modify layout controls in the "Customize Video Layout" section
3. **Watch Preview** - See real-time changes in the layout preview
4. **Apply Preset** (optional) - Click a preset button for quick templates
5. **Fill Video Details** - Enter headline, description, and upload media
6. **Generate Video** - Click "Generate Video" with your custom layout

## 🛡️ WordPress SSL Status

### SSL Issue Analysis ✅ VERIFIED

The WordPress posting functionality includes comprehensive SSL handling:

#### Current SSL Features:
1. **Automatic SSL Verification** 
   - Default: `verify_ssl=True`
   - Can be disabled via environment variable: `WORDPRESS_VERIFY_SSL=false`

2. **Self-Signed Certificate Support**
   - Built-in fallback: If SSL verification fails, automatically retries with `verify=False`
   - Suppresses urllib3 warnings for self-signed certificates
   - Error handling with try-except for SSLError

3. **Domain-Specific Configuration**
   - Special handling for grahakchetna.in: SSL verification disabled by default
   - Prevents SSL issues on specific problematic domains

4. **Global SSL Handling Functions**
   - All request functions (`requests.post()`, `requests.get()`) use verify parameter
   - Functions with SSL support:
     - `upload_media()` - Media upload with SSL handling
     - `_resolve_category_ids()` - Category resolution with SSL handling
     - `_resolve_tag_ids()` - Tag resolution with SSL handling
     - `create_post()` - Post creation with SSL handling
     - `publish_video_as_post()` - Complete publish workflow with SSL handling

5. **Error Recovery**
   - Catches `requests.exceptions.SSLError`
   - Logs SSL errors for debugging
   - Retries without SSL verification on failure
   - Provides user-friendly error messages

### Verification Results:
✅ All API endpoints properly use `verify_ssl` parameter  
✅ Error handling includes SSL-specific fallback logic  
✅ grahakchetna.in has special SSL configuration  
✅ Environment variable override available  
✅ urllib3 warnings suppressed appropriately  

### Testing SSL Issues:
To verify WordPress posting is working:
```bash
# Check WordPress credentials are set
grep WORDPRESS_ .env

# Test posting via the WordPress blueprint:
# POST /wordpress/post with video file and headlines
```

### Troubleshooting:
If WordPress posting fails:

1. **Check SSL Certificate:**
   ```bash
   openssl s_client -connect grahakchetna.in:443
   ```

2. **Disable SSL Verification:**
   - Set in `.env`: `WORDPRESS_VERIFY_SSL=false`
   - Or let the automatic fallback handle it

3. **Check WordPress Credentials:**
   - Verify `WORDPRESS_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD`
   - Ensure username uses app-specific password, not regular password

4. **Check Network/Firewall:**
   - Ensure port 443 is accessible
   - Check for any proxy/VPN blocking

## ✨ Future Enhancements

Possible improvements:
- Add animation effects selection (fade, slide, etc.)
- Text color customization for different video sections
- Multiple media support with layout coordination
- Background image/video customization
- Custom font size adjustments
- Export layout templates for reuse

## 📋 Summary

The video layout adjustment feature is fully implemented with:
- ✅ Complete UI with 5 customizable parameters
- ✅ Real-time preview visualization
- ✅ 4 preset layouts for quick configuration
- ✅ Backend integration with video generation
- ✅ Parameter propagation through all service layers
- ✅ WordPress SSL issues verified and handled

The system is ready for use and provides users with powerful control over video layout customization!

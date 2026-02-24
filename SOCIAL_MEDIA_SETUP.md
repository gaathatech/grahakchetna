# Grahakchetna - Social Media Integration & UI Refinement

## ✅ Completed Setup

This document outlines all social media posting integrations and UI improvements for Grahakchetna AI News Studio.

---

## 🔐 Credentials Status

All social media platforms are now fully configured and verified:

### Facebook (👤)
- **Status**: ✓ Configured
- **Page ID**: `374211199112915`
- **Token**: Active
- **Feature**: Direct Reel upload via Graph API v19.0

### Instagram (📸)
- **Status**: ✓ Configured
- **Instagram ID**: `17841467723671727`
- **Method**: Facebook Graph API proxy
- **Feature**: Direct video posting with caption support

### WordPress (📝)
- **Status**: ✓ Configured
- **URL**: `https://www.grahakchetna.in`
- **SSL Verification**: **Disabled** (for self-signed certificates)
- **Features**: 
  - Direct media upload
  - Automatic post creation
  - YouTube video embedding support
  - Custom description & metadata

---

## 📋 Key Changes Made

### 1. **WordPress SSL Support** (Self-Signed Certificates)

**File**: `wordpress_uploader.py`

Added SSL verification parameter to all functions:
```python
def upload_media(..., verify_ssl: bool = True) -> Dict[str, Any]
def create_post(..., verify_ssl: bool = True) -> Dict[str, Any]
def publish_video_as_post(..., verify_ssl: bool = True) -> Tuple[Dict, Dict]
```

**Benefit**: Allows posting to WordPress sites with self-signed SSL certificates without errors.

**File**: `wordpress_blueprint.py`

Added environment variable handling:
```python
verify_ssl = os.getenv('WORDPRESS_VERIFY_SSL', 'true').lower() not in ['false', '0', 'no']
```

**Configuration**: Set `WORDPRESS_VERIFY_SSL=false` in `.env` to disable SSL verification

### 2. **Credential Status Endpoint** (New)

**File**: `app.py`

New API endpoint: `GET /config/credentials`

Returns:
```json
{
  "facebook": {
    "configured": true,
    "page_id": "374211199112915"
  },
  "instagram": {
    "configured": true,
    "insta_id": "17841467723671727"
  },
  "wordpress": {
    "configured": true,
    "url": "grahakchetna.in",
    "verify_ssl": false
  }
}
```

**Usage**: UI polls this endpoint to show real-time credential status

### 3. **Enhanced UI with Credential Status**

**File**: `templates/index.html`

#### Credential Status Badge (New)
- Shows at top of page
- Color-coded indicators:
  - 🟢 Green: Platform configured and ready
  - 🟠 Orange: Platform not configured
- Auto-updates on page load via `/config/credentials` endpoint

#### Improved Platform Tabs
- **Before**: "f Facebook" (unclear emoji)
- **After**: "👤 Facebook" (clear user icon)
- Instagram: "📸 Instagram" ✓
- WordPress: "📝 WordPress" ✓
- Videos: "📹 Videos" (new label)

#### JavaScript Enhancement
New function `checkCredentials()`:
- Fetches credential status on page load
- Updates status badges dynamically
- Shows SSL settings for WordPress
- Provides user feedback on platform availability

---

## 🎯 Platform Integration Details

### Facebook Posting Flow
1. User generates short-form video
2. User clicks "Facebook Post" button in video library
3. UI shows posting form in modal
4. User enters caption
5. API calls `/facebook/post` endpoint
6. Upload to Facebook Graph API via `facebook_uploader.py`
7. Success/failure shown in real-time

**Required Credentials**:
- `PAGE_ID`
- `PAGE_ACCESS_TOKEN`

**Endpoint**: `POST /facebook/post`

### Instagram Posting Flow
1. Similar to Facebook
2. Supports two modes:
   - **Direct API**: Via Facebook Graph API
   - **Web Share**: Via browser native sharing
3. Automatic fallback if API fails

**Required Credentials**:
- `PAGE_ID`
- `PAGE_ACCESS_TOKEN`
- Connected Instagram Business account

**Endpoint**: `POST /instagram/post`

### WordPress Posting Flow
1. User generates video (short or long form)
2. User clicks "WordPress Publish" button
3. UI shows posting form in modal with options
4. User enters:
   - Title (required)
   - Description (optional)
   - YouTube URL (optional - for embedding)
5. API calls `/wordpress/post` endpoint
6. Video uploaded to media library
7. Post created with embeddings
8. Post link shown to user

**Required Credentials**:
- `WORDPRESS_URL`
- `WORDPRESS_USERNAME`
- `WORDPRESS_APP_PASSWORD`

**Optional Settings**:
- `WORDPRESS_VERIFY_SSL=false` (for self-signed certs)

**Endpoint**: `POST /wordpress/post`

---

## 🔧 Environment Variables

Add to `.env`:

```dotenv
# Facebook Integration
PAGE_ID=374211199112915
PAGE_ACCESS_TOKEN=EAAT3Q4oZCLo0BQ3QHiX2yaKtKrZChxwyBNZCH1ZCl26Fhr9mPQSBktcBtcxQEO35uVf2PMebNCAaTEsxtPYLtZAWvvse4cE7MX1bVijCk043xpGZBvBRZBPGAN0M4ZBNEKs9A6ChcmvmD99kKk5CZAZBy4ZAsJI7rR7TLBBhJXbKtPRvfoZBRAwGpwE2hdUp7EYABAZDZD

# Instagram Integration  
INSTA_ID=17841467723671727
# Uses same PAGE_ID and PAGE_ACCESS_TOKEN as Facebook

# WordPress Integration
WORDPRESS_URL=https://www.grahakchetna.in
WORDPRESS_USERNAME=hardik
WORDPRESS_APP_PASSWORD=aQT9 1HmL lQXx w51s afpm tcqS
# Disable SSL verification for self-signed certificates
WORDPRESS_VERIFY_SSL=false
```

---

## 🧪 Testing the Integration

### Test Credential Status
```bash
curl http://localhost:5002/config/credentials
```

Expected response:
```json
{
  "facebook": {"configured": true, "page_id": "374211199112915"},
  "instagram": {"configured": true, "insta_id": "17841467723671727"},
  "wordpress": {"configured": true, "url": "grahakchetna.in", "verify_ssl": false}
}
```

### Test Facebook Posting
1. Generate a short video
2. Click "Facebook Post" in video library
3. Enter caption
4. Click "Post to Facebook"
5. Check page: https://www.facebook.com/grahakchetna

### Test Instagram Posting
1. Generate a short video
2. Click "Instagram Post" in video library
3. Choose "Direct API" method
4. Enter caption
5. Click "Post to Instagram"
6. Check: https://instagram.com/[connected_account]

### Test WordPress Posting
1. Generate a video
2. Click "WordPress Publish" in video library
3. Enter title and optional description/YouTube URL
4. Click "Publish"
5. Check: https://www.grahakchetna.in/posts

---

## 📊 UI Components

### Status Badge
- Location: Top of page
- Updates: Every page load
- Shows: Real-time credential status for each platform

### Tabs Navigation
```
⏱ Short Video | ▶ Long Video | 📝 WordPress | 👤 Facebook | 📸 Instagram | 📹 Videos
```

### Posting Modals
Three modal forms for:
1. WordPress Post (title, description, YouTube URL)
2. Facebook Post (caption only)
3. Instagram Post (caption, 2 upload methods)

Each modal shows:
- Cancel button
- Submit button with loading state
- Error/success messages
- Retry buttons on failure

---

## 🛡️ Error Handling

All posting functions include:
- Credential validation
- File existence checks
- Network error handling
- Retry mechanisms for WordPress
- Timeout protection (300-600 seconds)
- Detailed error messages

### Common Issues & Solutions

**Issue**: "SSL: CERTIFICAT E_VERIFY_FAILED" on WordPress
- **Solution**: Set `WORDPRESS_VERIFY_SSL=false` in `.env`

**Issue**: "No connected Instagram Business account found"
- **Solution**: Ensure Facebook page is connected to Instagram account

**Issue**: "Facebook credentials not configured"
- **Solution**: Check `PAGE_ID` and `PAGE_ACCESS_TOKEN` in `.env`

**Issue**: WordPress posts created but video not showing
- **Solution**: Check plugin compatibility, may need media handling plugin

---

## 📈 Production Checklist

- [ ] All credentials set in `.env`
- [ ] Facebook page token valid and not expired
- [ ] WordPress app password created (not account password)
- [ ] WordPress SSL status verified in environment
- [ ] Test posting to each platform
- [ ] Monitor first few posts for issues
- [ ] Update automation schedule as needed

---

## 📚 Related Documentation

- Facebook Graph API: https://developers.facebook.com/docs/graph-api
- Instagram Graph API: https://developers.instagram.com/
- WordPress REST API: https://developer.wordpress.org/rest-api/
- MoviePy Documentation: https://zulko.github.io/moviepy/

---

**Last Updated**: February 24, 2026
**Version**: 1.0

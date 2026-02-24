from flask import Flask, render_template, request, send_file, jsonify
from script_service import generate_script
from long_script_service import generate_long_script
from tts_service import generate_voice
from video_service import generate_video
from long_video_service import generate_long_video
from facebook_uploader import upload_reel, FacebookReelUploadError
from wordpress_uploader import publish_video_as_post, WordPressUploadError
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Register uploader blueprints
try:
    from wordpress_blueprint import wordpress_bp
    app.register_blueprint(wordpress_bp)
except Exception:
    pass

try:
    from facebook_blueprint import facebook_bp
    app.register_blueprint(facebook_bp)
except Exception:
    pass

try:
    from instagram_blueprint import instagram_bp
    app.register_blueprint(instagram_bp)
except Exception:
    pass

try:
    from youtube_blueprint import youtube_bp
    app.register_blueprint(youtube_bp)
except Exception:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create videos directory for storing all generated videos
VIDEOS_DIR = "videos"
VIDEO_MANIFEST = f"{VIDEOS_DIR}/manifest.json"

def ensure_directories():
    """Ensure all required directories exist"""
    os.makedirs("output", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)

def load_manifest():
    """Load video manifest"""
    if os.path.exists(VIDEO_MANIFEST):
        try:
            with open(VIDEO_MANIFEST, 'r') as f:
                return json.load(f)
        except:
            return {"videos": []}
    return {"videos": []}

def save_manifest(manifest):
    """Save video manifest"""
    with open(VIDEO_MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)

def add_to_manifest(video_path, headline, description, language):
    """Add video entry to manifest"""
    manifest = load_manifest()
    entry = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3],
        "filename": os.path.basename(video_path),
        "path": video_path,
        "headline": headline,
        "description": description,
        "language": language,
        "created_at": datetime.now().isoformat(),
        "size_mb": round(os.path.getsize(video_path) / (1024*1024), 2)
    }
    manifest["videos"].insert(0, entry)  # New videos first
    save_manifest(manifest)
    return entry


def _get_video_duration(video_path):
    """Get video duration in seconds"""
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        return duration
    except Exception:
        return 0


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/videos", methods=["GET"])
def list_videos():
    """List all generated videos"""
    manifest = load_manifest()
    return jsonify(manifest)

@app.route("/config/credentials", methods=["GET"])
def get_credentials_status():
    """
    Check which posting platforms are configured.
    Returns status of credentials for Facebook, Instagram, WordPress.
    """
    return jsonify({
        "facebook": {
            "configured": bool(os.getenv("PAGE_ID") and os.getenv("PAGE_ACCESS_TOKEN")),
            "page_id": os.getenv("PAGE_ID", "").split()[0] if os.getenv("PAGE_ID") else None,
        },
        "instagram": {
            "configured": bool(os.getenv("PAGE_ID") and os.getenv("PAGE_ACCESS_TOKEN")),
            "insta_id": os.getenv("INSTA_ID", "").split()[0] if os.getenv("INSTA_ID") else None,
        },
        "wordpress": {
            "configured": bool(os.getenv("WORDPRESS_URL") and os.getenv("WORDPRESS_USERNAME") and os.getenv("WORDPRESS_APP_PASSWORD")),
            "url": os.getenv("WORDPRESS_URL", "").split("/")[2] if os.getenv("WORDPRESS_URL") else None,
            "verify_ssl": os.getenv('WORDPRESS_VERIFY_SSL', 'true').lower() not in ['false', '0', 'no']
        }
    })

@app.route("/video/<filename>", methods=["GET"])
def get_video(filename):
    """Download a specific video"""
    # Validate filename to prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid filename"}), 400
    
    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
        return send_file(
            video_path, 
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
    return jsonify({"error": "Video not found"}), 404

@app.route("/video/<filename>", methods=["DELETE"])
def delete_video(filename):
    """Delete a specific video"""
    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
        os.remove(video_path)
        # Update manifest
        manifest = load_manifest()
        manifest["videos"] = [v for v in manifest["videos"] if v["filename"] != filename]
        save_manifest(manifest)
        return jsonify({"status": "deleted", "filename": filename})
    return jsonify({"error": "Video not found"}), 404

@app.route("/generate", methods=["POST"])
def generate():

    headline = request.form["headline"]
    description = request.form["description"]
    language = request.form["language"]
    voice_provider = request.form.get("voice_provider", "auto")
    voice_model = request.form.get("voice_model", "auto")
    video_length = request.form.get("video_length", "full")

    # 1️⃣ Generate Script
    script = generate_script(headline, description, language)

    if not script:
        return jsonify({"error": "Script generation failed"}), 400

    # 2️⃣ Generate Voice
    tts_result = generate_voice(script)

    if not tts_result.get("success"):
        error_msg = tts_result.get("error", "Voice generation failed")
        logger.error(f"TTS error: {error_msg}")
        logger.debug(f"TTS details: {tts_result.get('details', {})}")
        return jsonify({
            "error": error_msg,
            "error_type": tts_result.get("error_type"),
            "attempted_providers": tts_result.get("attempted_providers", [])
        }), 400
    
    audio_path = tts_result.get("path")
    if not audio_path:
        return jsonify({"error": "Voice generation succeeded but no file path returned"}), 400

    # 3️⃣ Generate unique video filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    video_filename = f"video_{timestamp}.mp4"
    output_video_path = os.path.join(VIDEOS_DIR, video_filename)
    
    # 4️⃣ Generate Video with custom output path
    # Map video_length to max_duration (seconds)
    max_duration = None
    if video_length == "short":
        max_duration = 15
    elif video_length == "long":
        max_duration = 120

    video_path = generate_video(headline, description, audio_path, language=language, output_path=output_video_path, max_duration=max_duration)

    if not video_path:
        return jsonify({"error": "Video generation failed"}), 400

    # 5️⃣ Add to manifest
    entry = add_to_manifest(video_path, headline, description, language)
    
    return jsonify({
        "status": "success",
        "video": entry,
        "download_url": f"/video/{video_filename}"
    })


@app.route("/generate-and-post", methods=["POST"])
def generate_and_post():
    """Generate video and auto-post to Facebook"""
    try:
        headline = request.form["headline"]
        description = request.form["description"]
        language = request.form["language"]
        voice_provider = request.form.get("voice_provider", "auto")
        voice_model = request.form.get("voice_model", "auto")
        video_length = request.form.get("video_length", "full")
        auto_post = request.form.get("auto_post", "false").lower() == "true"

        # 1️⃣ Generate Script
        script = generate_script(headline, description, language)
        if not script:
            return jsonify({"error": "Script generation failed"}), 400

        # 2️⃣ Generate Voice
        tts_result = generate_voice(script)
        if not tts_result.get("success"):
            error_msg = tts_result.get("error", "Voice generation failed")
            logger.error(f"TTS error: {error_msg}")
            logger.debug(f"TTS details: {tts_result.get('details', {})}")
            return jsonify({
                "error": error_msg,
                "error_type": tts_result.get("error_type"),
                "attempted_providers": tts_result.get("attempted_providers", [])
            }), 400
        
        audio_path = tts_result.get("path")
        if not audio_path:
            return jsonify({"error": "Voice generation succeeded but no file path returned"}), 400

        # 3️⃣ Generate unique video filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        video_filename = f"video_{timestamp}.mp4"
        output_video_path = os.path.join(VIDEOS_DIR, video_filename)
        
        # 4️⃣ Generate Video
        # Map video_length to max_duration (seconds)
        max_duration = None
        if video_length == "short":
            max_duration = 15
        elif video_length == "long":
            max_duration = 120

        video_path = generate_video(
            headline, description, audio_path, 
            language=language, output_path=output_video_path, max_duration=max_duration
        )
        if not video_path:
            return jsonify({"error": "Video generation failed"}), 400

        # 5️⃣ Add to manifest
        entry = add_to_manifest(video_path, headline, description, language)
        
        # 6️⃣ Auto-post to Facebook if enabled
        facebook_response = None
        reel_id = None
        
        if auto_post:
            try:
                page_id = os.getenv("PAGE_ID")
                page_access_token = os.getenv("PAGE_ACCESS_TOKEN")
                
                if not page_id or not page_access_token:
                    logger.warning("Facebook credentials not configured. Skipping auto-post.")
                else:
                    logger.info(f"Auto-posting to Facebook page {page_id}...")
                    facebook_response = upload_reel(
                        video_path=video_path,
                        caption=f"{headline}\n\n{description}",
                        page_id=page_id,
                        page_access_token=page_access_token,
                        timeout=600  # 10 minutes for large files
                    )
                    reel_id = facebook_response.get("id")
                    logger.info(f"✓ Successfully posted to Facebook! Reel ID: {reel_id}")
                    
            except FacebookReelUploadError as e:
                logger.error(f"Facebook upload failed: {e}")
                # Return success for video generation but note the Facebook error
                return jsonify({
                    "status": "success",
                    "video": entry,
                    "download_url": f"/video/{video_filename}",
                    "facebook": {
                        "status": "failed",
                        "error": str(e)
                    }
                }), 200
            except Exception as e:
                logger.error(f"Unexpected error during Facebook upload: {e}")
                return jsonify({
                    "status": "success",
                    "video": entry,
                    "download_url": f"/video/{video_filename}",
                    "facebook": {
                        "status": "error",
                        "error": str(e)
                    }
                }), 200
        
        return jsonify({
            "status": "success",
            "video": entry,
            "download_url": f"/video/{video_filename}",
            "facebook": {
                "status": "posted" if auto_post else "skipped",
                "reel_id": reel_id,
                "response": facebook_response if auto_post else None
            } if auto_post else None
        })

    except Exception as e:
        logger.error(f"Generate and post failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/generate-long", methods=["POST"])
def generate_long():
    """
    Generate a long-form YouTube video (8-12 minutes, 1920x1080).
    
    Expects JSON or form data input:
    JSON:
    {
        "title": "Topic headline",
        "description": "Short summary",
        "language": "english" (optional)
    }
    
    Form data also accepts:
    - green_screen: File upload (image or video for green screen overlay)
    """
    try:
        # Support both JSON and form data
        headline = None
        description = None
        language = "english"
        green_screen_media = None
        
        if request.is_json:
            data = request.get_json()
            headline = data.get("title")
            description = data.get("description")
            language = data.get("language", "english")
        else:
            headline = request.form.get("title")
            description = request.form.get("description")
            language = request.form.get("language", "english")
            
            # Handle green screen file upload
            if 'green_screen' in request.files:
                try:
                    gs_file = request.files['green_screen']
                    if gs_file and gs_file.filename:
                        from werkzeug.utils import secure_filename
                        filename = secure_filename(gs_file.filename)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        gs_filename = f"gs_{timestamp}_{filename}"
                        gs_path = os.path.join("uploads", gs_filename)
                        os.makedirs("uploads", exist_ok=True)
                        gs_file.save(gs_path)
                        green_screen_media = gs_path
                        logger.info(f"✓ Green screen media uploaded: {gs_filename}")
                except Exception as e:
                    logger.warning(f"Failed to save green screen upload: {e}")
        
        # If no green screen uploaded, fetch from Pexels API
        if not green_screen_media:
            logger.info("📸 No green screen uploaded, fetching from Pexels API...")
            from long_video_service import fetch_image_from_pexels
            pexels_image = fetch_image_from_pexels(headline)
            if pexels_image:
                green_screen_media = pexels_image
                logger.info(f"✓ Using Pexels image as green screen")
            else:
                logger.info("⚠️ Pexels API unavailable, will use placeholder green screen")
        
        if not headline or not description:
            return jsonify({"error": "title and description required"}), 400
        
        logger.info(f"🎬 Starting long-form video generation: {headline}")
        
        # 1️⃣ Generate Long Script (1000-1500 words)
        logger.info("📝 Step 1: Generating long-form script...")
        script_result = generate_long_script(headline, description, language)
        
        if not script_result.get("success"):
            error_msg = script_result.get("error", "Script generation failed")
            logger.error(f"Script generation failed: {error_msg}")
            return jsonify({
                "status": "failed",
                "stage": "script_generation",
                "error": error_msg
            }), 400
        
        script_text = script_result.get("script")
        word_count = script_result.get("word_count", 0)
        
        logger.info(f"✓ Script generated ({word_count} words)")
        
        # 2️⃣ Generate TTS Audio using existing tts_service
        logger.info("🎤 Step 2: Generating voice narration...")
        tts_result = generate_voice(script_text)
        
        if not tts_result.get("success"):
            error_msg = tts_result.get("error", "Voice generation failed")
            logger.error(f"TTS error: {error_msg}")
            return jsonify({
                "status": "failed",
                "stage": "tts_generation",
                "error": error_msg,
                "attempted_providers": tts_result.get("attempted_providers", [])
            }), 400
        
        audio_path = tts_result.get("path")
        if not audio_path:
            return jsonify({
                "status": "failed",
                "stage": "tts_generation",
                "error": "Voice generation succeeded but no file path returned"
            }), 400
        
        logger.info(f"✓ Voice generated: {os.path.basename(audio_path)}")
        
        # 3️⃣ Generate Horizontal Video (1920x1080) with Green Screen
        logger.info("🎥 Step 3: Creating long-form video...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        video_filename = f"long_video_{timestamp}.mp4"
        output_video_path = os.path.join(VIDEOS_DIR, "long", video_filename)
        
        try:
            video_path = generate_long_video(
                headline=headline,
                description=description,
                audio_path=audio_path,
                language=language,
                output_path=output_video_path,
                green_screen_media=green_screen_media
            )
            logger.info(f"✓ Video generated: {os.path.basename(video_path)}")
        except Exception as e:
            logger.error(f"Video generation failed: {str(e)}")
            return jsonify({
                "status": "failed",
                "stage": "video_generation",
                "error": str(e)
            }), 400
        
        # 4️⃣ Add to manifest
        logger.info("📋 Step 4: Saving metadata...")
        entry = add_to_manifest(video_path, headline, description, language)
        
        logger.info(f"✅ Long-form video complete!")
        logger.info(f"   Word count: {word_count}")
        logger.info(f"   Duration: {_get_video_duration(video_path):.1f}s")
        logger.info(f"   Size: {entry.get('size_mb', 0):.1f} MB")
        
        # 5️⃣ Return response
        return jsonify({
            "status": "success",
            "video_path": video_path,
            "video_url": f"/video/{video_filename}",
            "script_word_count": word_count,
            "video": entry,
            "details": {
                "headline": headline,
                "language": language,
                "format": "1920x1080 (YouTube long-form)",
                "word_count": word_count
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Long-form generation failed: {str(e)}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500


@app.route("/test-long", methods=["GET"])
def test_long():
    """
    Test endpoint: Generate a sample long-form video.
    
    Uses:
    - Title: "Why Hungary Blocked EU Sanctions"
    - Description: "Hungary blocks EU sanctions package against Russia before war anniversary."
    """
    logger.info("🧪 Running long-form video test...")
    
    test_headline = "Why Hungary Blocked EU Sanctions"
    test_description = "Hungary blocks EU sanctions package against Russia before war anniversary."
    
    try:
        # Forward to /generate-long as a full JSON request
        test_data = {
            "title": test_headline,
            "description": test_description,
            "language": "english"
        }
        
        # Create a test request
        import json as json_lib
        test_request = type('obj', (object,), {
            'get_json': lambda: test_data
        })()
        
        # Call generate_long directly
        logger.info(f"Test case: {test_headline}")
        
        # 1️⃣ Generate script
        logger.info("Generating test script...")
        script_result = generate_long_script(test_headline, test_description)
        
        if not script_result.get("success"):
            return jsonify({
                "status": "test_failed",
                "stage": "script",
                "error": script_result.get("error")
            }), 400
        
        script_text = script_result.get("script")
        word_count = script_result.get("word_count", 0)
        
        # 2️⃣ Generate voice
        logger.info("Generating test voice...")
        tts_result = generate_voice(script_text)
        
        if not tts_result.get("success"):
            return jsonify({
                "status": "test_failed",
                "stage": "tts",
                "error": tts_result.get("error")
            }), 400
        
        audio_path = tts_result.get("path")
        
        # 3️⃣ Generate video
        logger.info("Generating test video...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        test_video_path = os.path.join(VIDEOS_DIR, "long", f"TEST_long_video_{timestamp}.mp4")
        
        video_path = generate_long_video(
            headline=test_headline,
            description=test_description,
            audio_path=audio_path,
            language="english",
            output_path=test_video_path
        )
        
        entry = add_to_manifest(video_path, test_headline, test_description, "english")
        
        logger.info("✅ Test completed successfully!")
        
        return jsonify({
            "status": "success",
            "test_name": "Long-form video generation test",
            "headline": test_headline,
            "description": test_description,
            "script_word_count": word_count,
            "video_path": video_path,
            "video_url": f"/video/{os.path.basename(video_path)}",
            "video": entry,
            "message": "Test long-form video generated successfully. Check /videos/long/ folder."
        }), 200
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return jsonify({
            "status": "test_failed",
            "error": str(e)
        }), 500


def post_to_wordpress():
    """Create a WordPress post using the generated video.

    Expects form-data: `filename`, `headline` (optional)
    """
    try:
        filename = request.form.get("filename")
        headline = request.form.get("headline") or filename

        if not filename:
            return jsonify({"error": "filename required"}), 400

        page_url = os.getenv("WORDPRESS_URL")
        wp_user = os.getenv("WORDPRESS_USERNAME")
        wp_app_pass = os.getenv("WORDPRESS_APP_PASSWORD")

        if not page_url or not wp_user or not wp_app_pass:
            logger.warning("WordPress credentials not configured")
            return jsonify({"error": "WordPress credentials not configured"}), 400

        video_path = os.path.join(VIDEOS_DIR, filename)
        if not os.path.exists(video_path):
            return jsonify({"error": "Video file not found"}), 404

        media_resp, post_resp = publish_video_as_post(video_path, headline, page_url, wp_user, wp_app_pass)

        return jsonify({
            "status": "published",
            "media": media_resp,
            "post": post_resp
        })

    except WordPressUploadError as e:
        logger.error(f"WordPress publish failed: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error in post-to-wordpress: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    ensure_directories()
    app.run(host="0.0.0.0", port=5002, debug=False)

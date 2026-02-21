from flask import Flask, render_template, request, send_file, jsonify
from script_service import generate_script
from tts_service import generate_voice
from video_service import generate_video
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

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/videos", methods=["GET"])
def list_videos():
    """List all generated videos"""
    manifest = load_manifest()
    return jsonify(manifest)

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
    female_voice = request.form.get("female_voice", "false").lower() == "true"
    voice_provider = request.form.get("voice_provider", "auto")
    voice_model = request.form.get("voice_model", "auto")
    video_length = request.form.get("video_length", "full")

    # 1️⃣ Generate Script
    script = generate_script(headline, description, language)

    if not script:
        return jsonify({"error": "Script generation failed"}), 400

    # 2️⃣ Generate Voice
    audio_path = generate_voice(script, language, output_path=None, female_voice=female_voice, voice_model=voice_model, voice_provider=voice_provider)

    if not audio_path:
        return jsonify({"error": "Voice generation failed"}), 400

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
        female_voice = request.form.get("female_voice", "false").lower() == "true"
        voice_provider = request.form.get("voice_provider", "auto")
        voice_model = request.form.get("voice_model", "auto")
        video_length = request.form.get("video_length", "full")
        auto_post = request.form.get("auto_post", "false").lower() == "true"

        # 1️⃣ Generate Script
        script = generate_script(headline, description, language)
        if not script:
            return jsonify({"error": "Script generation failed"}), 400

        # 2️⃣ Generate Voice
        audio_path = generate_voice(script, language, output_path=None, female_voice=female_voice, voice_model=voice_model, voice_provider=voice_provider)
        if not audio_path:
            return jsonify({"error": "Voice generation failed"}), 400

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


@app.route("/post-to-wordpress", methods=["POST"])
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

from flask import Flask, render_template, request, send_file, jsonify
from script_service import generate_script
from tts_service import generate_voice
from video_service import generate_video
import os
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

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
    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=True, download_name=filename)
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

    # 1️⃣ Generate Script
    script = generate_script(headline, description, language)

    if not script:
        return jsonify({"error": "Script generation failed"}), 400

    # 2️⃣ Generate Voice
    audio_path = generate_voice(script, language)

    if not audio_path:
        return jsonify({"error": "Voice generation failed"}), 400

    # 3️⃣ Generate unique video filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    video_filename = f"video_{timestamp}.mp4"
    output_video_path = os.path.join(VIDEOS_DIR, video_filename)
    
    # 4️⃣ Generate Video with custom output path
    video_path = generate_video(headline, description, audio_path, language=language, output_path=output_video_path)

    if not video_path:
        return jsonify({"error": "Video generation failed"}), 400

    # 5️⃣ Add to manifest
    entry = add_to_manifest(video_path, headline, description, language)
    
    return jsonify({
        "status": "success",
        "video": entry,
        "download_url": f"/video/{video_filename}"
    })


if __name__ == "__main__":
    ensure_directories()
    app.run(host="0.0.0.0", port=5002, debug=False)

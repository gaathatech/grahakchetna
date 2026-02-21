from flask import Blueprint, request, jsonify
from youtube_uploader import upload_youtube, YouTubeUploadError
import os

youtube_bp = Blueprint('youtube_bp', __name__, url_prefix='/youtube')


@youtube_bp.route('/post', methods=['POST'])
def post_to_youtube():
    filename = request.form.get('filename')
    title = request.form.get('title', filename)
    description = request.form.get('description', '')

    if not filename:
        return jsonify({"error": "filename required"}), 400

    video_path = os.path.join('videos', filename)
    if not os.path.exists(video_path):
        return jsonify({"error": "video not found"}), 404

    try:
        resp = upload_youtube(video_path, title, description)
        return jsonify({"status": "posted", "response": resp})
    except YouTubeUploadError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

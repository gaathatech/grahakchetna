from flask import Blueprint, request, jsonify
from instagram_uploader import upload_instagram, InstagramUploadError
import os

instagram_bp = Blueprint('instagram_bp', __name__, url_prefix='/instagram')


@instagram_bp.route('/post', methods=['POST'])
def post_to_instagram():
    filename = request.form.get('filename')
    caption = request.form.get('caption', '')

    if not filename:
        return jsonify({"error": "filename required"}), 400

    video_path = os.path.join('videos', filename)
    if not os.path.exists(video_path):
        return jsonify({"error": "video not found"}), 404

    try:
        resp = upload_instagram(video_path, caption)
        return jsonify({"status": "posted", "response": resp})
    except InstagramUploadError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

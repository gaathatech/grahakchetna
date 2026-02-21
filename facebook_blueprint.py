from flask import Blueprint, request, jsonify
from facebook_uploader import upload_reel, FacebookReelUploadError
import os

facebook_bp = Blueprint('facebook_bp', __name__, url_prefix='/facebook')


@facebook_bp.route('/post', methods=['POST'])
def post_to_facebook():
    filename = request.form.get('filename')
    caption = request.form.get('caption', '')

    if not filename:
        return jsonify({"error": "filename required"}), 400

    video_path = os.path.join('videos', filename)
    if not os.path.exists(video_path):
        return jsonify({"error": "video not found"}), 404

    page_id = os.getenv('PAGE_ID')
    page_access_token = os.getenv('PAGE_ACCESS_TOKEN')

    if not page_id or not page_access_token:
        return jsonify({"error": "Facebook credentials not configured"}), 400

    try:
        resp = upload_reel(video_path=video_path, caption=caption, page_id=page_id, page_access_token=page_access_token)
        return jsonify({"status": "posted", "response": resp})
    except FacebookReelUploadError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

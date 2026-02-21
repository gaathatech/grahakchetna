from flask import Blueprint, request, jsonify
from wordpress_uploader import publish_video_as_post, WordPressUploadError
import os

wordpress_bp = Blueprint('wordpress_bp', __name__, url_prefix='/wordpress')


@wordpress_bp.route('/post', methods=['POST'])
def post_to_wordpress_bp():
    filename = request.form.get('filename')
    headline = request.form.get('headline') or filename

    if not filename:
        return jsonify({"error": "filename required"}), 400

    video_path = os.path.join('videos', filename)
    if not os.path.exists(video_path):
        return jsonify({"error": "video not found"}), 404

    page_url = os.getenv('WORDPRESS_URL')
    wp_user = os.getenv('WORDPRESS_USERNAME')
    wp_app_pass = os.getenv('WORDPRESS_APP_PASSWORD')

    if not page_url or not wp_user or not wp_app_pass:
        return jsonify({"error": "WordPress credentials not configured"}), 400

    try:
        media_resp, post_resp = publish_video_as_post(video_path, headline, page_url, wp_user, wp_app_pass)
        return jsonify({"status": "published", "media": media_resp, "post": post_resp})
    except WordPressUploadError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

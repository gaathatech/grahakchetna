from flask import Blueprint, request, jsonify
from wordpress_uploader import publish_video_as_post, WordPressUploadError
import os

wordpress_bp = Blueprint('wordpress_bp', __name__, url_prefix='/wordpress')


@wordpress_bp.route('/post', methods=['POST'])
def post_to_wordpress_bp():
    from werkzeug.utils import secure_filename
    
    # Handle both file upload and filename
    video_path = None
    
    # Check if file is uploaded
    if 'video' in request.files:
        video_file = request.files['video']
        if video_file and video_file.filename:
            # Save uploaded file
            filename = secure_filename(video_file.filename)
            videos_dir = os.path.join('videos', filename)
            os.makedirs('videos', exist_ok=True)
            video_file.save(videos_dir)
            video_path = videos_dir
    
    # Fallback to filename parameter (for backward compatibility)
    if not video_path:
        filename = request.form.get('filename')
        if filename:
            video_path = os.path.join('videos', filename)
    
    if not video_path or not os.path.exists(video_path):
        return jsonify({"error": "video file required"}), 400

    headline = request.form.get('headline') or filename
    description = request.form.get('description') or ''
    youtube_url = request.form.get('youtube_url') or ''

    page_url = os.getenv('WORDPRESS_URL')
    wp_user = os.getenv('WORDPRESS_USERNAME')
    wp_app_pass = os.getenv('WORDPRESS_APP_PASSWORD')

    if not page_url or not wp_user or not wp_app_pass:
        return jsonify({"error": "WordPress credentials not configured"}), 400

    try:
        media_resp, post_resp = publish_video_as_post(
            video_path,
            headline,
            page_url,
            wp_user,
            wp_app_pass,
            description=description,
            youtube_url=youtube_url
        )
        return jsonify({"status": "published", "media": media_resp, "post": post_resp})
    except WordPressUploadError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

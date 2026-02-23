from flask import Blueprint, request, jsonify
from instagram_uploader import upload_instagram, InstagramUploadError
import os

instagram_bp = Blueprint('instagram_bp', __name__, url_prefix='/instagram')


@instagram_bp.route('/post', methods=['POST'])
def post_to_instagram():
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

    caption = request.form.get('caption', '')

    try:
        page_id = os.getenv('PAGE_ID')
        page_access_token = os.getenv('PAGE_ACCESS_TOKEN')
        resp = upload_instagram(video_path, caption, page_id=page_id, page_access_token=page_access_token)
        return jsonify({"status": "posted", "response": resp})
    except InstagramUploadError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

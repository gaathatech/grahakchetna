from flask import Blueprint, request, jsonify
from facebook_uploader import upload_reel, FacebookReelUploadError
import os

facebook_bp = Blueprint('facebook_bp', __name__, url_prefix='/facebook')


@facebook_bp.route('/post', methods=['POST'])
def post_to_facebook():
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

    page_id = os.getenv('PAGE_ID')
    page_access_token = os.getenv('PAGE_ACCESS_TOKEN')

    if not page_id or not page_access_token:
        return jsonify({"error": "Facebook credentials not configured"}), 400
    # Sanitize token locally and mask for logs
    try:
        tok = page_access_token.strip().strip('"').strip("'")
        if tok.endswith('>'):
            tok = tok.rstrip('>')
        # Mask token for logs
        masked = (tok[:6] + '...' + tok[-4:]) if len(tok) > 12 else '***'
        import logging
        logging.getLogger(__name__).info(f"Using PAGE_ACCESS_TOKEN: {masked}")

        resp = upload_reel(video_path=video_path, caption=caption, page_id=page_id, page_access_token=tok)
        return jsonify({"status": "posted", "response": resp})
    except FacebookReelUploadError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

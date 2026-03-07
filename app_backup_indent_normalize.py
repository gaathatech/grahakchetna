

# =========================================================
# VIDEO PATH RESOLVER + MANIFEST CLEANUP PATCH
# =========================================================
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
VIDEOS_DIR = BASE_DIR / "videos"
MANIFEST_PATH = VIDEOS_DIR / "manifest.json"


def _resolve_video_path(filename):
    """Resolve video path from multiple possible locations."""

    if not filename:
        return None

    direct = Path(filename)
    if direct.exists():
        return direct

    legacy = VIDEOS_DIR / filename
    if legacy.exists():
        return legacy

    for root, _, files in os.walk(VIDEOS_DIR):
        if filename in files:
            return Path(root) / filename

    return None


def _prune_missing_manifest_entries(manifest):
    """Remove entries for videos that no longer exist."""

    if not manifest:
        return manifest

    videos = manifest.get("videos", [])
    cleaned = []

    for v in videos:
        path = v.get("path") or v.get("filename")
        resolved = _resolve_video_path(path)

        if resolved and resolved.exists():
            cleaned.append(v)

    manifest["videos"] = cleaned
    return manifest


from flask import Flask, render_template, request, send_file, jsonify
from script_service import generate_script
from long_script_service import generate_long_script
from tts_service import generate_voice
from video_service import generate_video
from long_video_service import generate_long_video
import os
import json
import logging
import uuid
import shutil
from datetime import datetime
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_secret_for_flash')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create videos directory for storing all generated videos
VIDEOS_DIR = "videos"
VIDEO_MANIFEST = f"{VIDEOS_DIR}/manifest.json"
LAYOUTS_CONFIG = "layouts.json"

def ensure_directories():
    """Ensure all required directories exist"""
    os.makedirs("output", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)


# ===== LAYOUT MANAGEMENT FUNCTIONS =====
def load_layouts():
    """Load saved layout configurations"""
    if os.path.exists(LAYOUTS_CONFIG):
            with open(LAYOUTS_CONFIG, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_layouts(layouts):
    """Save layout configurations"""
        with open(LAYOUTS_CONFIG, 'w') as f:
            json.dump(layouts, f, indent=2)
        logger.info(f"✓ Saved {len(layouts)} layouts")
    except Exception as e:
        logger.error(f"✗ Failed to save layouts: {e}")
        raise


def get_layout_for_video(video_format='short'):
    """Get current layout config for a video format from session storage"""
    # Layouts can be passed via sessionStorage from the designer
    # For now, return defaults
    if video_format == 'long':
        return {
            'anchor_x': 0, 'anchor_y': 15, 'anchor_width': 35, 'anchor_height': 70, 'anchor_opacity': 100,
            'media_x': 40, 'media_y': 10, 'media_width': 50, 'media_height': 80, 'media_opacity': 100,
            'headline_y': 8, 'headline_height': 10, 'headline_color': '#dc143c', 'headline_fontsize': 50,
            'breaking_y': 8, 'breaking_height': 10, 'breaking_color': '#dc143c', 'breaking_fontsize': 40,
            'textbox_x': 40, 'textbox_y': 30, 'textbox_width': 50, 'textbox_height': 50,
            'textbox_bg_opacity': 60, 'textbox_fontsize': 32, 'textbox_color': '#ffffff',
            'overlay_opacity': 15, 'bg_blur': 'light'
        }
    else:  # short
        return {
            'anchor_x': 0, 'anchor_y': 20, 'anchor_width': 40, 'anchor_height': 60, 'anchor_opacity': 100,
            'media_x': 50, 'media_y': 20, 'media_width': 45, 'media_height': 55, 'media_opacity': 100,
            'headline_y': 10, 'headline_height': 8, 'headline_color': '#dc143c', 'headline_fontsize': 50,
            'breaking_y': 10, 'breaking_height': 8, 'breaking_color': '#dc143c', 'breaking_fontsize': 40,
            'textbox_x': 50, 'textbox_y': 35, 'textbox_width': 45, 'textbox_height': 40,
            'textbox_bg_opacity': 60, 'textbox_fontsize': 32, 'textbox_color': '#ffffff',
            'overlay_opacity': 15, 'bg_blur': 'light'
        }


def layout_to_video_params(layout_config, video_format='short'):
    """Convert layout designer config to video generation parameters"""
    params = {}
    
    # Media positioning
    if layout_config.get('media_x') and layout_config.get('media_y'):
        if float(layout_config.get('media_x', 0)) > 50:
            params['layout_mediaPosition'] = 'right'
        elif float(layout_config.get('media_x', 0)) < 30:
            params['layout_mediaPosition'] = 'left'
        else:
            params['layout_mediaPosition'] = 'center'
    
    # Media size mapping
    media_width = float(layout_config.get('media_width', 50))
    if media_width >= 90:
        params['layout_mediaSize'] = 'full'
    elif media_width >= 60:
        params['layout_mediaSize'] = 'large'
    elif media_width >= 40:
        params['layout_mediaSize'] = 'medium'
    else:
        params['layout_mediaSize'] = 'small'
    
    # Media opacity
    params['layout_mediaOpacity'] = int(float(layout_config.get('media_opacity', 100)))
    
    # Text alignment
    textbox_x = float(layout_config.get('textbox_x', 50))
    if textbox_x < 30:
        params['layout_textAlignment'] = 'left'
    elif textbox_x > 60:
        params['layout_textAlignment'] = 'right'
    else:
        params['layout_textAlignment'] = 'center'
    
    # Background blur
    params['layout_backgroundBlur'] = layout_config.get('bg_blur', 'light')
    
    # Detailed layout parameters (pass through)
    params['layout_config'] = layout_config
    
    return params

def load_manifest():
    """Load video manifest"""
    if os.path.exists(VIDEO_MANIFEST):
            with open(VIDEO_MANIFEST, 'r') as f:
                return json.load(f)
        except Exception:
            return {"videos": []}
    return {"videos": []}

def save_manifest(manifest):
    """Save video manifest"""
        # Ensure directory exists
        os.makedirs(VIDEOS_DIR, exist_ok=True)
        # Write to temp file first, then move (atomic write)
        temp_path = f"{VIDEO_MANIFEST}.tmp"
        with open(temp_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        # Atomic rename
        shutil.move(temp_path, VIDEO_MANIFEST)
        logger.info(f"✓ Manifest saved successfully ({len(manifest.get('videos', []))} videos)")
    except Exception as e:
        logger.error(f"✗ Failed to save manifest: {e}")
        raise

def add_to_manifest(video_path, headline, description, language):
    """Add video entry to manifest"""
        # Verify video file exists
        if not os.path.exists(video_path):
            logger.error(f"✗ Video file not found: {video_path}")
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        manifest = load_manifest()
        
        # Get file size with error handling
            file_size_mb = round(os.path.getsize(video_path) / (1024*1024), 2)
        except Exception as e:
            logger.warning(f"⚠️ Could not get file size for {video_path}: {e}")
            file_size_mb = 0
        
        entry = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3],
            "filename": os.path.basename(video_path),
            "path": video_path,
            "headline": headline,
            "description": description,
            "language": language,
            "created_at": datetime.now().isoformat(),
            "size_mb": file_size_mb
        }
        manifest["videos"].insert(0, entry)  # New videos first
        save_manifest(manifest)
        logger.info(f"✓ Added to manifest: {headline} ({file_size_mb} MB)")
        return entry
    except Exception as e:
        logger.error(f"✗ Failed to add to manifest: {e}")
        raise


def _get_video_duration(video_path):
    """Get video duration in seconds"""
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        return duration
    except Exception:
        return 0


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template("short.html")


@app.route("/rss", methods=["GET"])
def rss_page():
    """Separate RSS management UI page."""
    return render_template("rss.html")


# Routes for separate pages
@app.route('/short', methods=['GET'])
def short_page():
    return render_template('short.html')


@app.route('/long', methods=['GET'])
def long_page():
    return render_template('long.html')


@app.route('/videos', methods=['GET'])
def videos_page():
    return render_template('videos.html')


@app.route('/layout-designer', methods=['GET'])
def layout_designer():
    """Professional layout designer page"""
    return render_template('layout-designer.html')


@app.route('/settings', methods=['GET'])
def settings_page():
    """Background and UI configuration"""
    return render_template('settings.html')


@app.route('/api/layouts', methods=['GET'])
def get_layouts():
    """Get all saved layouts"""
    layouts = load_layouts()
    return jsonify(layouts)


@app.route('/api/layouts', methods=['POST'])
def save_layout():
    """Save a new layout"""
        data = request.get_json()
        layout_name = data.get('name', '').strip()
        layout_data = data.get('data', {})
        
        if not layout_name:
            return jsonify({'error': 'Layout name required'}), 400
        
        layouts = load_layouts()
        layouts[layout_name] = {
            'data': layout_data,
            'timestamp': datetime.now().isoformat()
        }
        save_layouts(layouts)
        
        return jsonify({'status': 'saved', 'name': layout_name}), 200
    except Exception as e:
        logger.error(f"Failed to save layout: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/layouts/<name>', methods=['DELETE'])
def delete_layout(name):
    """Delete a saved layout"""
        layouts = load_layouts()
        if name in layouts:
            del layouts[name]
            save_layouts(layouts)
            return jsonify({'status': 'deleted', 'name': name}), 200
        else:
            return jsonify({'error': 'Layout not found'}), 404
    except Exception as e:
        logger.error(f"Failed to delete layout: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/videos', methods=['GET'])
def list_videos():
    """List all generated videos"""
    manifest = load_manifest()
    return jsonify(manifest)


@app.route('/short_ui', methods=['GET'])
def short_ui_root():
    return render_template('short.html')


@app.route('/long_ui', methods=['GET'])
def long_ui_root():
    return render_template('long.html')


@app.route('/videos_ui', methods=['GET'])
def videos_ui_root():
    return render_template('videos_ui.html')


# make current year available in templates
@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}

# Background management storage helpers
BACKGROUND_FOLDER = os.path.join(os.getcwd(), 'static', 'backgrounds')
BACKGROUND_DB = os.path.join(os.getcwd(), 'backgrounds.json')

def ensure_bg_storage():
    os.makedirs(BACKGROUND_FOLDER, exist_ok=True)
    if not os.path.exists(BACKGROUND_DB):
        with open(BACKGROUND_DB, 'w') as f:
            json.dump([], f)

def load_backgrounds():
    ensure_bg_storage()
        with open(BACKGROUND_DB, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_backgrounds(bg_list):
    with open(BACKGROUND_DB, 'w') as f:
        json.dump(bg_list, f)


@app.route('/upload-background', methods=['POST'])
def upload_background():
    ensure_bg_storage()
    file = request.files.get('bgFile')
    name = request.form.get('bgName', '').strip()
    description = request.form.get('bgDescription', '').strip()
    make_default = request.form.get('makeDefault', 'false').lower() in ['true', '1', 'on']

    if not file or file.filename == '' or not name:
        return jsonify({'error': 'Name and file required'}), 400

    allowed = ['jpg', 'jpeg', 'png', 'mp4', 'webm']
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed:
        return jsonify({'error': 'Unsupported file type'}), 400

    filename = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(BACKGROUND_FOLDER, filename)
        file.save(save_path)
    except Exception as e:
        logger.error(f"Background upload failed: {e}")
        return jsonify({'error': 'Failed to save file'}), 500

    bg_list = load_backgrounds()
    if make_default:
        for bg in bg_list:
            bg['default'] = False

    entry = {
        'id': uuid.uuid4().hex,
        'name': name,
        'description': description,
        'path': '/' + os.path.relpath(save_path, start=os.getcwd()).replace(os.path.sep, '/'),
        'uploadedAt': datetime.now().isoformat(),
        'default': make_default
    }
    bg_list.append(entry)
    save_backgrounds(bg_list)

    return jsonify({'status': 'ok', 'filePath': entry['path'], 'bgName': entry['name'], 'makeDefault': make_default})


@app.route('/get-backgrounds', methods=['GET'])
def get_backgrounds():
    bg_list = load_backgrounds()
    return jsonify({'backgrounds': bg_list})


@app.route('/rss_get_mapping', methods=['GET'])
def rss_get_mapping():
        from rss_service import _load_category_map
        return jsonify(_load_category_map())
    except Exception as e:
        logger.error(f"rss_get_mapping failed: {e}")
        return jsonify({}), 500


@app.route('/rss_save_mapping', methods=['POST'])
def rss_save_mapping():
        data = None
        if request.is_json:
            data = request.get_json()
        else:
            raw = request.form.get('mapping')
            import json
            data = json.loads(raw) if raw else {}

        if not isinstance(data, dict):
            return jsonify({'error': 'mapping must be a JSON object'}), 400

        from rss_service import _save_category_map
        ok = _save_category_map(data)
        return jsonify({'saved': bool(ok)})
    except Exception as e:
        logger.error(f"rss_save_mapping failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/video/<filename>")
def get_video(filename):
    path = _resolve_video_path(filename)

    if not path or not path.exists():
        return jsonify({"error": "Video not found"}), 404

    return send_file(path, mimetype="video/mp4", conditional=True)
    
    # First check if video exists in manifest and use the full path from there
    manifest = load_manifest()
    video_entry = next((v for v in manifest["videos"] if v["filename"] == filename), None)
    
    if video_entry:
        video_path = video_entry["path"]
        if os.path.exists(video_path):
            return send_file(
                video_path, 
                as_attachment=True,
                download_name=filename,
                mimetype='video/mp4'
            )
    
    # Fallback to old location for backwards compatibility
    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
        return send_file(
            video_path, 
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
    return jsonify({"error": "Video not found"}), 404


@app.route("/preview/<filename>")
def preview_video(filename):
    path = _resolve_video_path(filename)

    if not path or not path.exists():
        return jsonify({"error": "Video not found"}), 404

    return send_file(path, mimetype="video/mp4", conditional=True)

    manifest = load_manifest()
    video_entry = next((v for v in manifest["videos"] if v["filename"] == filename), None)
    if video_entry and os.path.exists(video_entry["path"]):
        return send_file(video_entry["path"], as_attachment=False, mimetype='video/mp4')

    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=False, mimetype='video/mp4')

    return jsonify({"error": "Video not found"}), 404

@app.route("/video/<filename>")
def get_video(filename):
    path = _resolve_video_path(filename)

    if not path or not path.exists():
        return jsonify({"error": "Video not found"}), 404

    return send_file(path, mimetype="video/mp4", conditional=True)
    
    # Fallback to old location for backwards compatibility
    video_path = os.path.join(VIDEOS_DIR, filename)
    if os.path.exists(video_path):
            os.remove(video_path)
            # Update manifest
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
    # Do not force-trim audio here — let the video length follow the generated audio.
    # If a caller wants to cap duration, they can pass a value; by default use None.
    max_duration = None

    video_path = generate_video(headline, description, audio_path, language=language, output_path=output_video_path, max_duration=max_duration)

    if not video_path:
        return jsonify({"error": "Video generation failed"}), 400

    # 5️⃣ Add to manifest
        entry = add_to_manifest(video_path, headline, description, language)
    except Exception as e:
        logger.error(f"Failed to add video to manifest: {e}")
        return jsonify({
            "error": "Video generated but failed to save to archive",
            "details": str(e),
            "video_path": video_path
        }), 500
    
    return jsonify({
        "status": "success",
        "video": entry,
        "download_url": f"/video/{video_filename}"
    })


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
        # Support both JSON/form multi-story and legacy single-story form
        language = "english"
        green_screen_media = None
        stories = []
        story_media = []
        
        # Extract layout parameters
        layout_mediaPosition = "right"
        layout_mediaSize = "medium"
        layout_mediaOpacity = 100
        layout_textAlignment = "center"
        layout_backgroundBlur = "light"

        if request.is_json:
            data = request.get_json()
            # Accept {title, description} as single story
            title = data.get("title")
            description = data.get("description")
            language = data.get("language", "english")
            layout_mediaPosition = data.get("layout_mediaPosition", "right")
            layout_mediaSize = data.get("layout_mediaSize", "medium")
            layout_mediaOpacity = int(data.get("layout_mediaOpacity", 100))
            layout_textAlignment = data.get("layout_textAlignment", "center")
            layout_backgroundBlur = data.get("layout_backgroundBlur", "light")
            if title and description:
                stories = [{"headline": title, "description": description}]
        else:
            language = request.form.get("language", "english")
            layout_mediaPosition = request.form.get("layout_mediaPosition", "right")
            layout_mediaSize = request.form.get("layout_mediaSize", "medium")
            layout_mediaOpacity = int(request.form.get("layout_mediaOpacity", 100))
            layout_textAlignment = request.form.get("layout_textAlignment", "center")
            layout_backgroundBlur = request.form.get("layout_backgroundBlur", "light")
            # Multi-story form submission (stories JSON) preferred
            if 'stories' in request.form:
                    import json as _json
                    stories = _json.loads(request.form.get('stories') or '[]')
                except Exception as e:
                    logger.error(f"Failed to parse stories JSON: {e}")
                    return jsonify({"error": "Invalid stories JSON"}), 400
            else:
                # Legacy single-story form fields (accept either 'title' or 'headline')
                title = request.form.get('title') or request.form.get('headline')
                description = request.form.get('description')
                if title and description:
                    stories = [{"headline": title, "description": description}]

            # Handle per-story file uploads: story_file_0, story_file_1, ...
            from werkzeug.utils import secure_filename
            os.makedirs('uploads', exist_ok=True)
            # Save any uploaded story files
            i = 0
            while True:
                key = f'story_file_{i}'
                if key not in request.files:
                    break
                f = request.files.get(key)
                if f and getattr(f, 'filename', None):
                        filename = secure_filename(f.filename)
                        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                        outname = f'story_{i}_{ts}_{filename}'
                        outpath = os.path.join('uploads', outname)
                        f.save(outpath)
                        story_media.append(outpath)
                        logger.info(f'✓ Saved story upload: {outpath}')
                    except Exception as e:
                        logger.warning(f'Failed to save story upload {key}: {e}')
                i += 1

            # pick first uploaded media if any
            if story_media:
                green_screen_media = story_media[0]

        # If still no green screen uploaded, attempt Pexels for first story headline
        if not green_screen_media and stories:
            logger.info('📸 No green screen uploaded for stories, fetching from Pexels API...')
            from pexels_helper import fetch_image_from_pexels
            first_headline = stories[0].get('headline') if isinstance(stories, list) and len(stories) > 0 else None
            if first_headline:
                pexels_image = fetch_image_from_pexels(first_headline)
                if pexels_image:
                    green_screen_media = pexels_image
                    logger.info('✓ Using Pexels image as green screen')
                else:
                    logger.info('⚠️ Pexels API unavailable or no image found; placeholder will be used')

        if not stories:
            return jsonify({"error": "title and description required (or provide stories)"}), 400
        
        # Log high-level start (headline set later after combining stories)
            preview_headline = stories[0].get('headline') if stories and len(stories) > 0 else 'Long Video'
        except Exception:
            preview_headline = 'Long Video'
        logger.info(f"🎬 Starting long-form video generation: {preview_headline} (stories={len(stories)})")
        
        # 1️⃣ Generate Long Script(s) for each story and concatenate
        logger.info('📝 Step 1: Generating long-form script for stories...')
        combined_scripts = []
        total_words = 0
        for s in stories:
            h = s.get('headline') or ''
            d = s.get('description') or ''
            if not h or not d:
                logger.error('Story missing headline or description')
                return jsonify({'error': 'Each story requires headline and description'}), 400
            logger.info(f'Generating script for story: {h[:80]}')
            script_result = generate_long_script(h, d, language)
            if not script_result.get('success'):
                error_msg = script_result.get('error', 'Script generation failed')
                logger.error(f'Script generation failed for story "{h}": {error_msg}')
                return jsonify({ 'status': 'failed', 'stage': 'script_generation', 'error': error_msg }), 400
            piece = script_result.get('script')
            wc = script_result.get('word_count', 0)
            combined_scripts.append(piece)
            total_words += wc

        # Join scripts with a clear separator to allow natural pauses
        script_text = '\n\n---\n\n'.join(combined_scripts)
        word_count = total_words
        logger.info(f'✓ Combined script generated ({word_count} words total)')

        # Prepare combined metadata for video (use joined headlines/descriptions)
            headline = ' | '.join([s.get('headline','') for s in stories if s.get('headline')])
            description = '\n\n'.join([s.get('description','') for s in stories if s.get('description')])
        except Exception:
            headline = stories[0].get('headline') if stories else 'Long Video'
            description = stories[0].get('description') if stories else ''
        
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
            video_path = generate_long_video(
                stories=stories,
                audio_path=audio_path,
                language=language,
                output_path=output_video_path,
                story_medias=story_media,
                green_screen_media=green_screen_media,
                layout_mediaPosition=layout_mediaPosition,
                layout_mediaSize=layout_mediaSize,
                layout_mediaOpacity=layout_mediaOpacity,
                layout_textAlignment=layout_textAlignment,
                layout_backgroundBlur=layout_backgroundBlur
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
        except Exception as e:
            logger.error(f"Failed to add video to manifest: {e}")
            return jsonify({
                "status": "failed",
                "stage": "manifest_save",
                "error": "Video generated but failed to save to archive",
                "details": str(e),
                "video_path": video_path
            }), 500
        
        logger.info("✅ Long-form video complete!")
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
        tb = traceback.format_exc()
        logger.error(f"Long-form generation failed: {str(e)}\n{tb}")
        return jsonify({
            "status": "failed",
            "error": str(e),
            "traceback": tb
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
        except Exception as e:
            logger.error(f"Failed to add test video to manifest: {e}")
            return jsonify({
                "status": "test_partial_success",
                "message": "Video generated but failed to save metadata",
                "video_path": video_path,
                "error": str(e)
            }), 500
        
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


if __name__ == "__main__":
    ensure_directories()
    ensure_directories()
    # Allow overriding port via PORT or FLASK_PORT environment variables for testing
        port = int(os.getenv('PORT') or os.getenv('FLASK_PORT') or 5002)
    except Exception:
        port = 5002
    app.run(host="0.0.0.0", port=port, debug=False)

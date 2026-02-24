from flask import Flask, request, jsonify
import os
import time

app = Flask(__name__)


@app.route('/wp-json/wp/v2/media', methods=['POST'])
def media_upload():
    # Accept file and return a fake media object
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'no file'}), 400
    filename = file.filename or f'uploaded_{int(time.time())}.mp4'
    # Save to temporary folder
    os.makedirs('mock_media', exist_ok=True)
    path = os.path.join('mock_media', filename)
    file.save(path)
    return jsonify({'id': int(time.time()), 'source_url': f'http://{request.host}/mock_media/{filename}'})


@app.route('/wp-json/wp/v2/categories', methods=['GET', 'POST'])
def categories():
    if request.method == 'GET':
        q = request.args.get('search', '')
        return jsonify([])
    else:
        data = request.get_json() or {}
        return jsonify({'id': int(time.time()), 'name': data.get('name')})


@app.route('/wp-json/wp/v2/tags', methods=['GET', 'POST'])
def tags():
    if request.method == 'GET':
        return jsonify([])
    else:
        data = request.get_json() or {}
        return jsonify({'id': int(time.time()), 'name': data.get('name')})


@app.route('/wp-json/wp/v2/posts', methods=['POST'])
def create_post():
    data = request.get_json() or {}
    post_id = int(time.time())
    return jsonify({'id': post_id, 'link': f'http://{request.host}/?p={post_id}', 'title': data.get('title'), 'content': data.get('content')})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

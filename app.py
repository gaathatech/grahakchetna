from flask import Flask, render_template, request, send_file
from script_service import generate_script
from tts_service import generate_voice
from video_service import generate_video
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():

    headline = request.form["headline"]
    description = request.form["description"]
    language = request.form["language"]

    # 1️⃣ Generate Script
    script = generate_script(headline, description, language)

    if not script:
        return "Script generation failed."

    # 2️⃣ Generate Voice
    audio_path = generate_voice(script, language)

    if not audio_path:
        return "Voice generation failed."

    # 3️⃣ Generate Video
    video_path = generate_video(headline, description, audio_path, language=language)

    if not video_path:
        return "Video generation failed."

    return send_file(video_path, as_attachment=True)


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    app.run(host="0.0.0.0", port=5002, debug=False)

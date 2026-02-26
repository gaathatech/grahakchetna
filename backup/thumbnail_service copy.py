from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

def create_thumbnail(headline):
    img = Image.new("RGB", (1280, 720), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype("assets/font.ttf", 80)
    wrapped = textwrap.fill(headline, width=20)

    draw.text((100, 200), wrapped, font=font, fill="white")

    path = "output/thumbnails/thumb.jpg"
    img.save(path)

    return path

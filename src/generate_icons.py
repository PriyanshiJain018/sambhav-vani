#!/usr/bin/env python3
"""
generate_icons.py — Run once to create icon-192.png and icon-512.png
Usage: python3 generate_icons.py
Output: public/icons/icon-192.png, public/icons/icon-512.png

Requires: pip install Pillow
"""
import os
from PIL import Image, ImageDraw, ImageFont

SIZES = [192, 512]
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'icons')
os.makedirs(OUT_DIR, exist_ok=True)

BG      = (148, 63, 8)      # --saffron-dark
ACCENT  = (255, 255, 255)

def make_icon(size):
    img = Image.new('RGBA', (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    # Rounded square background
    pad = int(size * 0.06)
    r   = int(size * 0.22)
    draw.rounded_rectangle([pad, pad, size-pad, size-pad], radius=r, fill=BG)

    # Om symbol (U+0950) centered — fallback to "ॐ" text
    font_size = int(size * 0.48)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf', font_size)
    except Exception:
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', font_size)
        except Exception:
            font = ImageFont.load_default()

    text = '\u0950'  # ॐ
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1] - int(size * 0.02)
    draw.text((x, y), text, font=font, fill=ACCENT)

    out = os.path.join(OUT_DIR, f'icon-{size}.png')
    img.save(out, 'PNG')
    print(f'  ✓ {out}')

for s in SIZES:
    make_icon(s)

print('Icons generated.')

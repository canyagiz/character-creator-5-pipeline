"""
annotate_debug.py — Debug render'lara ölçüm etiketi ekler.
Blender render'daki renkli konturlara PIL ile eşleşen renkli metin yazar.

Kullanım:
  python annotate_debug.py --id char_11256
  python annotate_debug.py           # debug klasöründeki tümü
"""

import json
import os
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont

DEBUG_ROOT = os.path.join(os.path.dirname(__file__), "..", "renders", "debug")

try:
    FONT = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15)
    FONT_SM = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)
except Exception:
    FONT = ImageFont.load_default()
    FONT_SM = FONT

PADDING = 1.20   # render_views.py ile aynı

def z_to_pix(z_m, z_floor, height_m, img_h=512):
    z_center  = z_floor + height_m / 2.0
    delta_z   = z_m - z_center
    delta_pix = -delta_z * img_h / (height_m * PADDING)
    return int(img_h / 2.0 + delta_pix)

def annotate_char(char_id, debug_dir):
    debug_json = os.path.join(debug_dir, f"{char_id}_debug.json")
    if not os.path.exists(debug_json):
        print(f"  JSON bulunamadi: {debug_json}")
        return

    with open(debug_json) as f:
        data = json.load(f)

    z_floor  = data["z_floor"]
    height_m = data["height_m"]
    meas     = data["measurements"]

    for view in ("front", "right"):
        src = os.path.join(debug_dir, f"{char_id}_debug_{view}.png")
        if not os.path.exists(src):
            continue

        img  = Image.open(src).convert("RGBA")
        draw = ImageDraw.Draw(img)

        for label, info in meas.items():
            z_m   = info["plane_co"][2]
            circ  = info["circ_cm"]
            rgb   = tuple(int(c * 255) for c in info["color"])
            color = (*rgb, 230)
            py    = z_to_pix(z_m, z_floor, height_m)

            # Kesik çizgi
            for x in range(0, 512, 14):
                draw.line([(x, py), (min(x + 8, 511), py)],
                          fill=color, width=2)

            # Etiket (sol kenar)
            text = f"{label}: {circ:.0f} cm"
            # Arka plan (okunabilirlik)
            bbox = draw.textbbox((6, py - 17), text, font=FONT)
            draw.rectangle([bbox[0]-2, bbox[1]-1, bbox[2]+2, bbox[3]+1],
                           fill=(0, 0, 0, 160))
            draw.text((6, py - 17), text, fill=color, font=FONT)

        out_path = os.path.join(debug_dir, f"{char_id}_annotated_{view}.png")
        img.save(out_path)
        print(f"  {os.path.basename(out_path)}")

parser = argparse.ArgumentParser()
parser.add_argument("--id",  default=None)
parser.add_argument("--dir", default=DEBUG_ROOT)
args = parser.parse_args()

debug_dir = os.path.normpath(args.dir)

if args.id:
    # --dir char_dir olarak geldiyse direkt kullan, yoksa debug_root/char_id subdir'ine in
    if os.path.basename(debug_dir) == args.id:
        char_dir = debug_dir
    else:
        char_dir = os.path.join(debug_dir, args.id)
    annotate_char(args.id, char_dir)
else:
    for entry in sorted(os.scandir(debug_dir)):
        if entry.is_dir() and entry.name.startswith("char_"):
            print(f"{entry.name}:")
            annotate_char(entry.name, entry.path)

"""
debug_height.py — Height segment debug görüntüleri üretir.

Total height + lower_leg / upper_leg / torso / neck_head segmentlerini
renkli dimension çizgileri ve PIL etiketleri ile gösterir.

Kullanım:
  python blender-pipeline/debug_height.py                   # fbx_export/ tümü
  python blender-pipeline/debug_height.py --id ansur_00000  # tek karakter
  python blender-pipeline/debug_height.py --overwrite       # mevcut PNG üzerine yaz

Çıktı: renders/debug/<char_id>_height_annotated_front.png
"""

import subprocess
import sys
import os
import json
import argparse

from PIL import Image, ImageDraw, ImageFont

_BASE         = os.path.dirname(os.path.abspath(__file__))
BLENDER_EXE   = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
RENDER_SCRIPT = os.path.join(_BASE, "render_debug_height.py")
FBX_ROOT      = os.path.abspath(os.path.join(_BASE, "..", "fbx_export"))
DEBUG_ROOT    = os.path.abspath(os.path.join(_BASE, "..", "renders", "debug"))

try:
    FONT    = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15)
    FONT_SM = ImageFont.truetype("C:/Windows/Fonts/arial.ttf",   13)
except Exception:
    FONT = FONT_SM = ImageFont.load_default()

PADDING = 1.20   # render_debug_height.py ile aynı

def z_to_pix(z_m, z_floor, height_m, img_h=512):
    z_center  = z_floor + height_m / 2.0
    delta_pix = -(z_m - z_center) * img_h / (height_m * PADDING)
    return int(img_h / 2.0 + delta_pix)

def annotate(char_id, debug_dir):
    json_path = os.path.join(debug_dir, f"{char_id}_height.json")
    png_path  = os.path.join(debug_dir, f"{char_id}_height_front.png")
    out_path  = os.path.join(debug_dir, f"{char_id}_height_annotated_front.png")

    if not os.path.exists(json_path) or not os.path.exists(png_path):
        print(f"  Eksik dosya: {char_id}")
        return

    with open(json_path) as f:
        data = json.load(f)

    z_floor  = data["z_floor"]
    height_m = data["height_m"]
    segs     = data["segments"]

    img  = Image.open(png_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    iw, ih = img.size

    # ── Sol: çevre ölçümleri ──────────────────────────────────────────────────
    circ_meas = data.get("measurements", {})
    for label, info in circ_meas.items():
        z_m   = info["plane_co"][2]
        circ  = info["circ_cm"]
        rgb   = tuple(int(c * 255) for c in info["color"])
        color_fill = (*rgb, 220)
        py = z_to_pix(z_m, z_floor, height_m, ih)
        # Kesik çizgi
        for x in range(0, iw // 2 - 10, 14):
            draw.line([(x, py), (min(x + 8, iw//2 - 12), py)], fill=color_fill, width=1)
        text = f"{label}: {circ:.0f} cm"
        bbox = draw.textbbox((6, py - 16), text, font=FONT_SM)
        draw.rectangle([bbox[0]-2, bbox[1]-1, bbox[2]+2, bbox[3]+1], fill=(0,0,0,160))
        draw.text((6, py - 16), text, fill=color_fill, font=FONT_SM)

    # ── Sağ: height segment etiketleri ───────────────────────────────────────
    SEG_ORDER = ["foot", "lower_leg", "upper_leg", "torso", "neck", "head", "total"]
    for label in SEG_ORDER:
        if label not in segs:
            continue
        info   = segs[label]
        z_mid  = info["z_mid"]
        z_lo   = info["z_lo"]
        z_hi   = info["z_hi"]
        length = info["length_cm"]
        rgb    = tuple(int(c * 255) for c in info["color"])
        color_fill = (*rgb, 230)

        py_mid = z_to_pix(z_mid, z_floor, height_m, ih)

        text = f"HEIGHT {length:.1f}cm" if label == "total" else f"{label}: {length:.1f}cm"
        font = FONT if label == "total" else FONT_SM
        tx = iw - 148
        bbox = draw.textbbox((tx, py_mid - 8), text, font=font)
        draw.rectangle([bbox[0]-2, bbox[1]-1, bbox[2]+2, bbox[3]+1], fill=(0,0,0,170))
        draw.text((tx, py_mid - 8), text, fill=color_fill, font=font)

    # ── Başlık ────────────────────────────────────────────────────────────────
    title = f"{char_id}  |  height: {data['height_cm']:.1f} cm"
    draw.rectangle([0, 0, iw, 22], fill=(0, 0, 0, 180))
    draw.text((6, 4), title, fill=(255, 255, 255, 230), font=FONT_SM)

    img.save(out_path)
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--id",        default=None)
parser.add_argument("--dir",       default=FBX_ROOT)
parser.add_argument("--overwrite", action="store_true")
args = parser.parse_args()

fbx_dir = os.path.normpath(args.dir)

if args.id:
    fbx_files = [os.path.join(fbx_dir, f"{args.id}.fbx")]
else:
    fbx_files = sorted([
        os.path.join(fbx_dir, f)
        for f in os.listdir(fbx_dir)
        if f.endswith(".fbx")
    ])

os.makedirs(DEBUG_ROOT, exist_ok=True)
total = len(fbx_files); done = 0; failed = 0; skipped = 0

print(f"Toplam: {total} FBX | cikti: {DEBUG_ROOT}\n")

for i, fbx_path in enumerate(fbx_files):
    char_id  = os.path.splitext(os.path.basename(fbx_path))[0]
    char_dir = os.path.join(DEBUG_ROOT, char_id)
    out_png  = os.path.join(char_dir, f"{char_id}_height_annotated_front.png")

    if not args.overwrite and os.path.exists(out_png):
        skipped += 1
        continue

    os.makedirs(char_dir, exist_ok=True)
    print(f"[{i+1}/{total}] {char_id} ...", end=" ", flush=True)

    # Blender render
    r = subprocess.run(
        [BLENDER_EXE, "--background", "--python", RENDER_SCRIPT,
         "--", os.path.abspath(fbx_path), char_dir],
        capture_output=True, text=True
    )

    if r.returncode != 0:
        failed += 1
        print("BLENDER HATA")
        print(r.stderr[-400:])
        continue

    # PIL annotation
    out = annotate(char_id, char_dir)
    if out:
        done += 1
        height_line = next(
            (l.strip() for l in r.stdout.splitlines() if "TOTAL:" in l), "")
        print(f"OK  {height_line}")
    else:
        failed += 1
        print("ANNOTATE HATA")

print(f"\nBitti: {done} OK, {skipped} atlandi, {failed} hata")

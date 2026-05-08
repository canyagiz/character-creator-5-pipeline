"""
batch_render.py — FBX klasöründeki tüm dosyaları render eder + antropometrik ölçüm alır.

Kullanım:
  python batch_render.py                             # fbx_export/ altındaki tüm .fbx
  python batch_render.py --dir fbx_export/extremes  # belirli klasör
  python batch_render.py --id char_00037            # tek karakter
  python batch_render.py --no-measure               # sadece render, ölçüm alma
  python batch_render.py --debug                    # ölçüm debug görseli de üret
  python batch_render.py --masks                    # segmentation GT maskesi üret

Çıktı:
  renders/raw/<char_id>/          — 8 PNG (orijinal materyaller)
  renders/silhouettes/<char_id>/  — 8 PNG (silüet)
  renders/meta/                   — tüm ölçümleri içeren JSON
  renders/measurements/           — antropometrik ölçüm JSON
  renders/debug/                  — ölçüm kontur görselleri (--debug ile)
  renders/segmentation/<char_id>/ — 8 PNG RGB segmentation maskesi (--masks ile)
"""

import subprocess
import sys
import os
import argparse
import json

# ── Ayarlar ───────────────────────────────────────────────────────────────────
BLENDER_EXE    = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
RENDER_SCRIPT      = os.path.join(os.path.dirname(__file__), "render_views.py")
MEASURE_SCRIPT     = os.path.join(os.path.dirname(__file__), "measure_anthropometry.py")
HEIGHT_DEBUG_SCRIPT = os.path.join(os.path.dirname(__file__), "debug_height.py")
MASK_SCRIPT        = os.path.join(os.path.dirname(__file__), "render_segmentation_masks.py")
_BASE          = os.path.dirname(os.path.abspath(__file__))
FBX_ROOT       = os.path.abspath(os.path.join(_BASE, "..", "fbx_export"))
RAW_ROOT       = os.path.abspath(os.path.join(_BASE, "..", "renders", "raw"))
SIL_ROOT       = os.path.abspath(os.path.join(_BASE, "..", "renders", "silhouettes"))
META_ROOT      = os.path.abspath(os.path.join(_BASE, "..", "renders", "meta"))
DEBUG_ROOT     = os.path.abspath(os.path.join(_BASE, "..", "renders", "debug"))
MASK_ROOT      = os.path.abspath(os.path.join(_BASE, "..", "renders", "segmentation"))

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--dir",           default=FBX_ROOT, help="FBX klasörü")
parser.add_argument("--id",            default=None,     help="Tek char_id (örn: char_00037)")
parser.add_argument("--overwrite",     action="store_true", help="Mevcut render/ölçümleri yeniden al")
parser.add_argument("--no-measure",    action="store_true", help="Olcum adimini atla")
parser.add_argument("--measure-only",  action="store_true", help="Render atla, sadece olcum al")
parser.add_argument("--debug",         action="store_true", help="Olcum kontur gorseli uret")
parser.add_argument("--masks",         action="store_true", help="Segmentation GT maskesi uret")
args = parser.parse_args()

fbx_dir = os.path.normpath(args.dir)

# ── FBX listesi ───────────────────────────────────────────────────────────────
if args.id:
    fbx_files = [os.path.join(fbx_dir, f"{args.id}.fbx")]
else:
    fbx_files = sorted([
        os.path.join(fbx_dir, f)
        for f in os.listdir(fbx_dir)
        if f.endswith(".fbx")
    ])

if not fbx_files:
    print(f"FBX bulunamadı: {fbx_dir}")
    sys.exit(1)

total         = len(fbx_files)
render_done   = 0
render_skip   = 0
render_fail   = 0
measure_done  = 0
measure_skip  = 0
measure_fail  = 0
mask_done     = 0
mask_skip     = 0
mask_fail     = 0

print(f"Toplam: {total} FBX")
print(f"  raw       : {RAW_ROOT}")
print(f"  siluet    : {SIL_ROOT}")
print(f"  meta      : {META_ROOT}")

if args.debug:
    print(f"  debug     : {DEBUG_ROOT}")
if args.masks:
    print(f"  maske     : {MASK_ROOT}")
print()

for i, fbx_path in enumerate(fbx_files):
    char_name    = os.path.splitext(os.path.basename(fbx_path))[0]
    raw_dir      = os.path.join(RAW_ROOT,  char_name)
    sil_dir      = os.path.join(SIL_ROOT,  char_name)
    meta_path    = os.path.join(META_ROOT, f"{char_name}_meta.json")

    prefix = f"[{i+1}/{total}] {char_name}"

    # ── Render ────────────────────────────────────────────────────────────────
    if not args.overwrite and os.path.exists(os.path.join(sil_dir, f"{char_name}_front.png")):
        render_skip += 1
        render_tag = "render:SKIP"
    else:
        result = subprocess.run(
            [BLENDER_EXE, "--background", "--python", RENDER_SCRIPT,
             "--", fbx_path, raw_dir, sil_dir, META_ROOT],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            render_fail += 1
            render_tag = "render:HATA"
            print(f"{prefix} | {render_tag}")
            print(result.stderr[-800:])
            continue  # ölçüme geçme, FBX bozuk olabilir
        else:
            render_done += 1
            height_line = next(
                (l.strip() for l in result.stdout.splitlines() if "Height:" in l), ""
            )
            render_tag = f"render:OK  {height_line}"

    # ── Ölçüm ─────────────────────────────────────────────────────────────────
    measure_tag = ""
    if not args.no_measure:
        def _has_measurements(path):
            try:
                with open(path) as f:
                    return "chest_circ_cm" in json.load(f)
            except Exception:
                return False

        if not args.overwrite and _has_measurements(meta_path):
            measure_skip += 1
            measure_tag = "olcum:SKIP"
        else:
            result = subprocess.run(
                [BLENDER_EXE, "--background", "--python", MEASURE_SCRIPT,
                 "--", fbx_path, META_ROOT],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                measure_fail += 1
                measure_tag = "olcum:HATA"
                print(result.stderr[-400:])
            else:
                measure_done += 1
                summary = []
                for line in result.stdout.splitlines():
                    if any(k in line for k in ("chest_circ", "waist_circ", "WARN")):
                        summary.append(line.strip())
                measure_tag = "olcum:OK" + (f"  [{' | '.join(summary)}]" if summary else "")

    # ── Segmentation maskesi ──────────────────────────────────────────────────
    if args.masks:
        mask_dir    = os.path.join(MASK_ROOT, char_name)
        mask_front  = os.path.join(mask_dir, f"{char_name}_front.png")
        if not args.overwrite and os.path.exists(mask_front):
            mask_skip += 1
            mask_tag = "maske:SKIP"
        else:
            os.makedirs(mask_dir, exist_ok=True)
            fbx_abs = os.path.abspath(fbx_path)
            r = subprocess.run(
                [BLENDER_EXE, "--background", "--python", MASK_SCRIPT,
                 "--", fbx_abs, mask_dir],
                capture_output=True, text=True
            )
            if r.returncode != 0:
                mask_fail += 1
                mask_tag = "maske:HATA"
                print(r.stderr[-400:])
            else:
                mask_done += 1
                mask_tag = "maske:OK"

    # ── Debug görseli ─────────────────────────────────────────────────────────
    if args.debug:
        char_debug_dir = os.path.join(DEBUG_ROOT, char_name)
        annotated = os.path.join(char_debug_dir, f"{char_name}_height_annotated_front.png")
        if not args.overwrite and os.path.exists(annotated):
            debug_tag = "debug:SKIP"
        else:
            r = subprocess.run(
                [sys.executable, HEIGHT_DEBUG_SCRIPT,
                 "--id", char_name, "--dir", fbx_dir]
                + (["--overwrite"] if args.overwrite else []),
                capture_output=True, text=True
            )
            if r.returncode != 0:
                debug_tag = "debug:HATA"
                print(r.stderr[-400:])
            else:
                debug_tag = "debug:OK"

    # ── Satır çıktısı ──────────────────────────────────────────────────────────
    tags = [render_tag]
    if not args.no_measure:
        tags.append(measure_tag)
    if args.masks:
        tags.append(mask_tag)
    if args.debug:
        tags.append(debug_tag)
    print(f"{prefix} | {' | '.join(tags)}")

# ── Ozet ──────────────────────────────────────────────────────────────────────
print(f"\n-- Render : {render_done} OK, {render_skip} atlandi, {render_fail} hata")
if not args.no_measure:
    print(f"-- Olcum  : {measure_done} OK, {measure_skip} atlandi, {measure_fail} hata")
if args.masks:
    print(f"-- Maske  : {mask_done} OK, {mask_skip} atlandi, {mask_fail} hata")

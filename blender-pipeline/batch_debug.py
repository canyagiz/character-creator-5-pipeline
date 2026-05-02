"""
batch_debug.py — Ölçüm debug görsellerini toplu üretir.

Kullanım:
  python batch_debug.py --id char_11256
  python batch_debug.py --dir fbx_export/extremes
"""

import subprocess
import sys
import os
import argparse

BLENDER_EXE    = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
DEBUG_SCRIPT   = os.path.join(os.path.dirname(__file__), "render_debug_measurements.py")
ANNOTATE_SCRIPT = os.path.join(os.path.dirname(__file__), "annotate_debug.py")
FBX_ROOT       = os.path.join(os.path.dirname(__file__), "..", "fbx_export")
DEBUG_ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "renders", "debug"))

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=FBX_ROOT)
parser.add_argument("--id",  default=None)
parser.add_argument("--overwrite", action="store_true")
args = parser.parse_args()

fbx_dir = os.path.normpath(args.dir)

if args.id:
    fbx_files = [os.path.join(fbx_dir, f"{args.id}.fbx")]
else:
    fbx_files = sorted([os.path.join(fbx_dir, f)
                        for f in os.listdir(fbx_dir) if f.endswith(".fbx")])

os.makedirs(DEBUG_ROOT, exist_ok=True)
total = len(fbx_files); done = 0; failed = 0

print(f"Toplam: {total} FBX -> {DEBUG_ROOT}\n")

for i, fbx_path in enumerate(fbx_files):
    fbx_path  = os.path.abspath(fbx_path)
    char_name = os.path.splitext(os.path.basename(fbx_path))[0]
    char_dir  = os.path.join(DEBUG_ROOT, char_name)
    out_front = os.path.join(char_dir, f"{char_name}_annotated_front.png")

    if not args.overwrite and os.path.exists(out_front):
        print(f"[{i+1}/{total}] {char_name} SKIP")
        continue

    os.makedirs(char_dir, exist_ok=True)
    print(f"[{i+1}/{total}] {char_name} ...", end=" ", flush=True)

    r = subprocess.run(
        [BLENDER_EXE, "--background", "--python", DEBUG_SCRIPT,
         "--", fbx_path, char_dir],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        failed += 1
        print("HATA")
        print(r.stderr[-600:])
        continue

    subprocess.run([sys.executable, ANNOTATE_SCRIPT, "--id", char_name,
                    "--dir", char_dir], capture_output=True)

    done += 1
    print("OK")

print(f"\nBitti: {done} OK, {failed} hata")

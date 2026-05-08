"""
batch_measure.py — FBX klasöründeki tüm dosyalar için antropometrik ölçüm alır.

Kullanım:
  python batch_measure.py                            # fbx_export/ tümü
  python batch_measure.py --dir fbx_export/extremes # belirli klasör
  python batch_measure.py --id char_00037           # tek karakter
  python batch_measure.py --overwrite               # mevcut JSON'ları yeniden hesapla
"""

import subprocess
import sys
import os
import csv
import argparse

BLENDER_EXE   = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
SCRIPT_PATH   = os.path.join(os.path.dirname(__file__), "measure_anthropometry.py")
FBX_ROOT      = os.path.join(os.path.dirname(__file__), "..", "fbx_export")
MEASURE_ROOT  = os.path.join(os.path.dirname(__file__), "..", "renders", "measurements")
DATASET_CSV   = os.path.join(os.path.dirname(__file__), "..", "logs", "dataset_inverted.csv")

# char_id -> weight_kg (Siri BF% icin)
_weight_map = {}
if os.path.exists(DATASET_CSV):
    with open(DATASET_CSV, encoding="utf-8") as _f:
        for _r in csv.DictReader(_f):
            if "weight_kg" in _r:
                _weight_map[_r["char_id"]] = _r["weight_kg"]

parser = argparse.ArgumentParser()
parser.add_argument("--dir",       default=FBX_ROOT, help="FBX klasörü")
parser.add_argument("--id",        default=None,      help="Tek char_id")
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

if not fbx_files:
    print(f"FBX bulunamadi: {fbx_dir}")
    sys.exit(1)

total   = len(fbx_files)
done    = 0
skipped = 0
failed  = 0

print(f"Toplam: {total} FBX | cikti: {MEASURE_ROOT}\n")

for i, fbx_path in enumerate(fbx_files):
    char_name = os.path.splitext(os.path.basename(fbx_path))[0]
    out_path  = os.path.join(MEASURE_ROOT, f"{char_name}_measurements.json")

    if not args.overwrite and os.path.exists(out_path):
        skipped += 1
        continue

    print(f"[{i+1}/{total}] {char_name} ...", end=" ", flush=True)

    weight_arg = _weight_map.get(char_name, "")
    cmd = [BLENDER_EXE, "--background", "--python", SCRIPT_PATH,
           "--", fbx_path, MEASURE_ROOT]
    if weight_arg:
        cmd.append(weight_arg)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        failed += 1
        print("HATA")
        print(result.stderr[-600:])
    else:
        done += 1
        # height satırını bul ve özetle yazdır
        for line in result.stdout.splitlines():
            if "height_cm" in line:
                print(line.strip())
                break
        else:
            print("OK")

print(f"\nBitti: {done} olcum, {skipped} atlandi, {failed} hata")

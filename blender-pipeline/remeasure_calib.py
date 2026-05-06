"""
remeasure_calib.py — Kalibrasyon FBX'lerine shoulder_width_cm ve hip_width_cm ekler.
Mevcut calib meta JSON'larini gunceller (merge eder, silmez).

Calistir: python blender-pipeline/remeasure_calib.py
"""

import subprocess
import sys
import os

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
SCRIPT      = os.path.join(os.path.dirname(__file__), "measure_anthropometry.py")
FBX_DIR     = r"C:\Users\aliya\workspace\cc5-scripts\calib\fbx_export_calib\calib"
META_DIR    = r"C:\Users\aliya\workspace\cc5-scripts\calib\renders_calib\meta"

fbx_files = sorted([
    os.path.join(FBX_DIR, f)
    for f in os.listdir(FBX_DIR)
    if f.endswith(".fbx")
])

total  = len(fbx_files)
done   = 0
failed = 0

print(f"Toplam: {total} FBX -> {META_DIR}\n")

for i, fbx_path in enumerate(fbx_files):
    char_name = os.path.splitext(os.path.basename(fbx_path))[0]
    meta_path = os.path.join(META_DIR, f"{char_name}_meta.json")

    # Zaten shoulder_width_cm varsa atla
    if os.path.exists(meta_path):
        import json
        with open(meta_path) as f:
            existing = json.load(f)
        if "shoulder_width_cm" in existing:
            print(f"[{i+1}/{total}] {char_name} SKIP (zaten var)")
            done += 1
            continue

    print(f"[{i+1}/{total}] {char_name} ...", end=" ", flush=True)

    result = subprocess.run(
        [BLENDER_EXE, "--background", "--python", SCRIPT,
         "--", fbx_path, META_DIR],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        failed += 1
        print("HATA")
        print(result.stderr[-400:])
    else:
        done += 1
        for line in result.stdout.splitlines():
            if "shoulder_width" in line:
                print(line.strip())
                break
        else:
            print("OK")

print(f"\nBitti: {done} OK, {failed} hata")

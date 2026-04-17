"""
CC5 Production Export Script
Çalıştırma: CC5 Script Editor
"""

import RLPy
import csv
import os
import sys
sys.path.insert(0, r"C:\Users\aliya\workspace\cc5-scripts")
from cc5_helpers import compute_all_weights, ALL_MORPHS, PROJECT_FILES

CSV_PATH   = r"C:\Users\aliya\workspace\cc5-scripts\dataset.csv"
OUTPUT_DIR = r"C:\Users\aliya\workspace\cc5-scripts\fbx_export"
LOG_PATH   = r"C:\Users\aliya\workspace\cc5-scripts\logs\cc5_export.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
log_file = open(LOG_PATH, "w", encoding="utf-8", buffering=1)

def log(msg):
    print(msg)
    log_file.write(msg + "\n")

def make_fbx_setting():
    s = RLPy.RExportFbxSetting()
    s.SetOption(RLPy.EExportFbxOptions__None)
    s.SetOption2(RLPy.EExportFbxOptions2__None)
    s.SetOption2(RLPy.EExportFbxOptions2_ResetBoneScale)
    s.EnableExportMotion(False)
    s.EnableBakeSubdivision(False)
    return s

fbx_setting = make_fbx_setting()

with open(CSV_PATH, "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

total    = len(rows)
exported = skipped = 0
log(f"Başlıyor: {total} row")

for i, row in enumerate(rows):
    char_id  = row["char_id"]
    gender   = row["gender"]
    fbx_path = os.path.join(OUTPUT_DIR, f"{char_id}.fbx")

    if os.path.exists(fbx_path):
        skipped += 1
        continue

    log(f"[{i+1}/{total}] {char_id} ({gender}) — LoadFile...")
    RLPy.RFileIO.LoadFile(PROJECT_FILES[gender])

    avatar  = RLPy.RScene.GetAvatars()[0]
    shaping = avatar.GetAvatarShapingComponent()

    weights = compute_all_weights(
        fat                    = float(row["fat_score"]),
        muscle                 = float(row["muscle_score"]),
        height_score           = float(row["height_score"]),
        chest_height_score     = float(row["chest_height_score"]),
        hip_length_score       = float(row["hip_length_score"]),
        thigh_length_score     = float(row["thigh_length_score"]),
        lower_leg_length_score = float(row["lower_leg_length_score"]),
        pattern                = row.get("training_pattern", "balanced"),
        gender                 = gender,
    )

    for mid, w in weights.items():
        shaping.SetShapingMorphWeight(mid, w)

    RLPy.RScene.SelectObject(avatar)
    log(f"[{i+1}/{total}] {char_id} — ExportFbxFile...")
    RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, fbx_setting)
    log(f"[{i+1}/{total}] {char_id} — OK ({os.path.getsize(fbx_path):,} bytes)")

    exported += 1

log(f"\nTamamlandi: {exported} exported, {skipped} skipped")
log_file.close()

"""
Extremes Export Probe
Outlier karakterleri CC5'ten FBX olarak export eder.
CC5 Script Editor'da çalıştır.
"""

import RLPy
import csv
import os
import sys
sys.path.insert(0, r"C:\Users\aliya\workspace\cc5-scripts")
from cc5_helpers import compute_all_weights, ALL_MORPHS, PROJECT_FILES

TARGET_IDS = [
    "char_11256",  # obese — max fat + min height
    "char_14274",  # athletic_hyper — max muscle + max height
    "char_00017",  # athletic_hyper — kaslı + uzun kadın
    "char_00037",  # athletic_hyper — kaslı + min height (eski sorunlu)
    "char_00048",  # underweight — min fat+muscle + min height (adolescent)
    "char_00005",  # underweight — en ince + max height
    "char_00033",  # obese — kilolu + min height kadın
]

CSV_PATH   = r"C:\Users\aliya\workspace\cc5-scripts\dataset.csv"
OUTPUT_DIR = r"C:\Users\aliya\workspace\cc5-scripts\fbx_export\extremes"
LOG_PATH   = r"C:\Users\aliya\workspace\cc5-scripts\logs\extremes_export_probe.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
log_file = open(LOG_PATH, "w", encoding="utf-8", buffering=1)

def log(msg=""):
    print(msg)
    log_file.write(msg + "\n")

with open(CSV_PATH, "r", encoding="utf-8") as f:
    all_rows = {r["char_id"]: r for r in csv.DictReader(f)}

fbx_setting = RLPy.RExportFbxSetting()
fbx_setting.SetOption(RLPy.EExportFbxOptions__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2_ResetBoneScale)
fbx_setting.EnableExportMotion(False)
fbx_setting.EnableBakeSubdivision(False)

total = len(TARGET_IDS)
for i, char_id in enumerate(TARGET_IDS):
    row = all_rows[char_id]
    gender   = row["gender"]
    fbx_path = os.path.join(OUTPUT_DIR, f"{char_id}.fbx")

    log(f"[{i+1}/{total}] {char_id} | {row['group']} | {gender} | "
        f"fat={row['fat_score']} muscle={row['muscle_score']} height={row['height_score']}")

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
        upper_arm_length_score = float(row["upper_arm_length_score"]),
        forearm_length_score   = float(row["forearm_length_score"]),
        neck_length_score      = float(row["neck_length_score"]),
        pattern                = row.get("training_pattern", "balanced"),
        gender                 = gender,
    )

    for mid in ALL_MORPHS:
        shaping.SetShapingMorphWeight(mid, 0.0)
    for mid, w in weights.items():
        shaping.SetShapingMorphWeight(mid, w)

    RLPy.RScene.SelectObject(avatar)
    RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, fbx_setting)

    size = os.path.getsize(fbx_path) if os.path.exists(fbx_path) else -1
    log(f"  -> {fbx_path} ({size:,} bytes)")
    log()

log("Tamamlandi.")
log_file.close()

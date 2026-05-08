"""
calibration_export.py — Kalibrasyon alt kumesini CC5'ten FBX olarak export eder.
CC5 Script Editor'da calistir.

Kaynak: analysis/calibration_probe.csv  (1009 satir)
Cikti:  fbx_export/calib/<char_id>.fbx
"""

import RLPy
import csv
import gc
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from cc5_helpers import compute_all_weights, ALL_MORPHS, PROJECT_FILES

CSV_PATH   = str(_ROOT / "analysis" / "calibration_probe.csv")
OUTPUT_DIR = str(_ROOT / "fbx_export" / "calib")
LOG_PATH   = str(_ROOT / "logs" / "calibration_export.log")

OVERWRITE  = False

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)

def log(msg=""):
    print(msg)
    log_file.write(msg + "\n")

with open(CSV_PATH, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

total = len(rows)
log(f"=== calibration_export START {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
log(f"Toplam: {total} karakter | OVERWRITE={OVERWRITE}")

fbx_setting = RLPy.RExportFbxSetting()
fbx_setting.SetOption(RLPy.EExportFbxOptions__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2_ResetBoneScale)
fbx_setting.EnableExportMotion(False)
fbx_setting.EnableBakeSubdivision(False)

done    = 0
skipped = 0
failed  = 0
errors  = []
current_gender = None

for i, row in enumerate(rows):
    char_id  = row["char_id"]
    gender   = row["gender"]
    fbx_path = os.path.join(OUTPUT_DIR, f"{char_id}.fbx")

    if not OVERWRITE and os.path.exists(fbx_path):
        skipped += 1
        continue

    if gender != current_gender:
        RLPy.RFileIO.LoadFile(PROJECT_FILES[gender])
        current_gender = gender
        log(f"  [project] {gender} yuklendi")

    try:
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
            hip_score              = float(row.get("hip_score") or 0.5),
            waist_def_score        = float(row.get("waist_def_score") or 0.5),
        )

        for mid in ALL_MORPHS:
            shaping.SetShapingMorphWeight(mid, 0.0)
        for mid, w in weights.items():
            shaping.SetShapingMorphWeight(mid, w)

        RLPy.RScene.SelectObject(avatar)
        RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, fbx_setting)

        size = os.path.getsize(fbx_path) if os.path.exists(fbx_path) else -1
        if size < 1000:
            raise RuntimeError(f"FBX cok kucuk ({size} bytes)")

        done += 1
        if done % 50 == 0 or i == total - 1:
            log(f"[{i+1}/{total}] {done} export, {skipped} atlandi, {failed} hata | son: {char_id}")

    except Exception as e:
        failed += 1
        errors.append(char_id)
        log(f"  [HATA] {char_id}: {e}")

    finally:
        try:
            del shaping, avatar
        except NameError:
            pass
        if (done + failed) % 500 == 0:
            gc.collect()

log()
log(f"=== TAMAMLANDI {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
log(f"Export: {done} | Atlandi: {skipped} | Hata: {failed}")
if errors:
    log(f"Hatali char_id'ler: {errors}")
log_file.close()

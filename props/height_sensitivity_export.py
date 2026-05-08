"""
height_sensitivity_export.py — CC5 Script Editor'da çalıştır.
Height morphlarını 0.1 adımlarla probe eder; FBX export eder.

Her satır için: tüm morphları 0 yap, sadece ilgili height morphunu set et, export et.
Çıktı: fbx_export_height_sensitivity/hprob_*.fbx

Kullanım: CC5 Script Editor > Run Script
"""

import RLPy
import csv
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from cc5_helpers import ALL_MORPHS, PROJECT_FILES

PROBE_CSV  = str(_ROOT / "logs" / "height_sensitivity_probe.csv")
OUTPUT_DIR = str(_ROOT / "fbx_export_height_sensitivity")
LOG_PATH   = str(_ROOT / "logs" / "height_sensitivity_export.log")
OVERWRITE  = False

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
def log(msg=""):
    print(msg)
    log_file.write(msg + "\n")

with open(PROBE_CSV, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

fbx_setting = RLPy.RExportFbxSetting()
fbx_setting.SetOption(RLPy.EExportFbxOptions__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2_ResetBoneScale)
fbx_setting.EnableExportMotion(False)
fbx_setting.EnableBakeSubdivision(False)

total = len(rows); done = 0; skipped = 0; failed = 0
current_gender = None

log(f"=== height_sensitivity_export START {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
log(f"Toplam: {total} probe | cikti: {OUTPUT_DIR}")

for i, row in enumerate(rows):
    char_id   = row["char_id"]
    gender    = row["gender"]
    morph_id  = row["morph_id"]
    morph_val = float(row["morph_value"])
    fbx_path  = os.path.join(OUTPUT_DIR, f"{char_id}.fbx")

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

        for mid in ALL_MORPHS:
            shaping.SetShapingMorphWeight(mid, 0.0)

        if morph_id:
            shaping.SetShapingMorphWeight(morph_id, morph_val)

        RLPy.RScene.SelectObject(avatar)
        RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, fbx_setting)

        size = os.path.getsize(fbx_path) if os.path.exists(fbx_path) else -1
        if size < 1000:
            raise RuntimeError(f"FBX cok kucuk ({size} bytes)")

        done += 1
        if done % 50 == 0 or i == total - 1:
            log(f"[{i+1}/{total}] {done} export, {skipped} atlandi, {failed} hata")

    except Exception as e:
        failed += 1
        log(f"  [HATA] {char_id}: {e}")

log(f"\nBitti: {done} OK, {skipped} SKIP, {failed} HATA")
log_file.close()

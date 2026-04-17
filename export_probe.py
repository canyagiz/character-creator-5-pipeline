"""
Tek bir karakter için export probe.
CC5 Script Editor'da çalıştır.
"""

import RLPy
import csv
import os
import sys
sys.path.insert(0, r"C:\Users\aliya\workspace\cc5-scripts")
from cc5_helpers import compute_all_weights, ALL_MORPHS, PROJECT_FILES

TARGET_ID  = "char_00037"
CSV_PATH   = r"C:\Users\aliya\workspace\cc5-scripts\dataset.csv"
OUTPUT_DIR = r"C:\Users\aliya\workspace\cc5-scripts\fbx_export"
LOG_PATH   = r"C:\Users\aliya\workspace\cc5-scripts\logs\export_probe.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)
log_file = open(LOG_PATH, "w", encoding="utf-8", buffering=1)

def log(msg):
    print(msg)
    log_file.write(msg + "\n")

# ── Row bul ───────────────────────────────────────────────────────────────────
with open(CSV_PATH, "r", encoding="utf-8") as f:
    row = next(r for r in csv.DictReader(f) if r["char_id"] == TARGET_ID)
log(f"Row: {dict(row)}")

gender   = row["gender"]
fbx_path = os.path.join(OUTPUT_DIR, f"{TARGET_ID}.fbx")

# ── Proje yükle ───────────────────────────────────────────────────────────────
log(f"LoadFile başlıyor ({gender})...")
RLPy.RFileIO.LoadFile(PROJECT_FILES[gender])
log("LoadFile döndü.")

# ── Avatar al ─────────────────────────────────────────────────────────────────
avatar  = RLPy.RScene.GetAvatars()[0]
shaping = avatar.GetAvatarShapingComponent()
log(f"Avatar: {avatar.GetName()}")

# ── Morphlar ──────────────────────────────────────────────────────────────────
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
for mid in ALL_MORPHS:
    shaping.SetShapingMorphWeight(mid, 0.0)
for mid, w in weights.items():
    shaping.SetShapingMorphWeight(mid, w)
log(f"Morphlar uygulandı: {len(weights)} adet")

# ── Export ────────────────────────────────────────────────────────────────────
s = RLPy.RExportFbxSetting()
s.SetOption(RLPy.EExportFbxOptions__None)
s.SetOption2(RLPy.EExportFbxOptions2__None)
s.SetOption2(RLPy.EExportFbxOptions2_ResetBoneScale)
s.EnableExportMotion(False)
s.EnableBakeSubdivision(False)
log("Export ayarları: ResetBoneScale, texture yok")

RLPy.RScene.SelectObject(avatar)
log("ExportFbxFile başlıyor...")
RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, s)
log("ExportFbxFile döndü.")
log(f"Dosya var mı: {os.path.exists(fbx_path)}")
if os.path.exists(fbx_path):
    log(f"Dosya boyutu: {os.path.getsize(fbx_path):,} bytes")

log_file.close()

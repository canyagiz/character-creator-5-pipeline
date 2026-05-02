"""
batch_export.py — Tüm dataset.csv satırlarını CC5'ten FBX olarak export eder.
CC5 Script Editor'da çalıştır.

Özellikler:
  - Mevcut FBX varsa atlar (--overwrite ile yeniden üretir)
  - Her 100 karakterde log yazar
  - Hata durumunda devam eder, hatalı char_id'leri loglar
  - START_IDX ile kaldığın yerden devam edebilirsin

Kullanım:
  1. START_IDX = 0 ile tüm dataset
  2. START_IDX = N ile N. satırdan başla (resume)
  3. OVERWRITE = True ile mevcut FBX'leri yeniden üret
  4. GENDER_FILTER = "male" / "female" / None ile sadece o cinsiyet
"""

import RLPy
import csv
import os
import sys
import time

sys.path.insert(0, r"C:\Users\aliya\workspace\cc5-scripts")
from cc5_helpers import compute_all_weights, ALL_MORPHS, PROJECT_FILES

# ── Ayarlar ───────────────────────────────────────────────────────────────────
CSV_PATH      = r"C:\Users\aliya\workspace\cc5-scripts\dataset.csv"
OUTPUT_DIR    = r"C:\Users\aliya\workspace\cc5-scripts\fbx_export"
LOG_PATH      = r"C:\Users\aliya\workspace\cc5-scripts\logs\batch_export.log"

START_IDX     = 0       # Kaçıncı satırdan başla (0 = en baştan)
OVERWRITE     = False   # True → mevcut FBX'leri yeniden üret
GENDER_FILTER = None    # "male" / "female" / None (hepsi)

# ── Hazırlık ──────────────────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)

def log(msg=""):
    print(msg)
    log_file.write(msg + "\n")

with open(CSV_PATH, "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

if GENDER_FILTER:
    rows = [r for r in rows if r["gender"] == GENDER_FILTER]

rows = rows[START_IDX:]
total = len(rows)

log(f"=== batch_export START {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
log(f"Toplam: {total} karakter | START_IDX={START_IDX} | OVERWRITE={OVERWRITE}")
log()

# ── FBX export ayarları ───────────────────────────────────────────────────────
fbx_setting = RLPy.RExportFbxSetting()
fbx_setting.SetOption(RLPy.EExportFbxOptions__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2_ResetBoneScale)
fbx_setting.EnableExportMotion(False)
fbx_setting.EnableBakeSubdivision(False)

# ── Ana döngü ─────────────────────────────────────────────────────────────────
done    = 0
skipped = 0
failed  = 0
errors  = []

current_gender = None  # Gereksiz project reload'u önle

for i, row in enumerate(rows):
    char_id  = row["char_id"]
    gender   = row["gender"]
    fbx_path = os.path.join(OUTPUT_DIR, f"{char_id}.fbx")

    global_idx = START_IDX + i + 1

    # Mevcut dosyayı atla
    if not OVERWRITE and os.path.exists(fbx_path):
        skipped += 1
        continue

    # Proje yükle (sadece cinsiyet değiştiğinde)
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
        )

        for mid in ALL_MORPHS:
            shaping.SetShapingMorphWeight(mid, 0.0)
        for mid, w in weights.items():
            shaping.SetShapingMorphWeight(mid, w)

        RLPy.RScene.SelectObject(avatar)
        RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, fbx_setting)

        size = os.path.getsize(fbx_path) if os.path.exists(fbx_path) else -1
        if size < 1000:
            raise RuntimeError(f"FBX cok kucuk ({size} bytes), export basarisiz olabilir")

        done += 1

        # Her 100 karakterde ilerleme raporu
        if done % 100 == 0 or i == total - 1:
            log(f"[{global_idx}/{START_IDX + total}] {done} export, "
                f"{skipped} atlandi, {failed} hata | son: {char_id}")

    except Exception as e:
        failed += 1
        errors.append(char_id)
        log(f"  [HATA] {char_id}: {e}")
        # Proje reload yap ki bozuk state'den kurtar
        current_gender = None

log()
log(f"=== TAMAMLANDI {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
log(f"Export: {done} | Atlandi: {skipped} | Hata: {failed}")
if errors:
    log(f"Hatali char_id'ler: {errors}")
log_file.close()

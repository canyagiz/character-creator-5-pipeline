"""
batch_export.py — dataset_inverted.csv satirlarini CC5'ten FBX olarak export eder.
CC5 Script Editor'da calistir.

dataset_inverted.csv her satirinda hazir morph agirliklari var (morph_* kolonlari).
compute_all_weights kullanilmaz — dogrudan CC5 morph ID'leri set edilir.

Ozellikler:
  - Mevcut FBX varsa atlar (OVERWRITE=True ile yeniden uretir)
  - Resume destekli
  - Her 100 karakterde log yazar
"""

import RLPy
import csv
import gc
import os
import sys
import time

# ── Ayarlar ───────────────────────────────────────────────────────────────────
_BASE         = os.path.dirname(os.path.abspath(__file__))
_ROOT         = os.path.dirname(_BASE)          # cc5-scripts/
CSV_PATH      = os.path.join(_ROOT, "logs", "dataset_inverted_combined.csv")
OUTPUT_DIR    = os.path.join(_ROOT, "fbx_export")
LOG_PATH      = os.path.join(_ROOT, "logs", "batch_export.log")

START_IDX     = 0       # Kacinci satirdan basla (0 = bu node'un kendi sirasinda)
OVERWRITE     = False   # True -> mevcut FBX'leri yeniden uret
GENDER_FILTER = None    # "male" / "female" / None (hepsi)

from local_config import NODE_ID, NODE_COUNT

# Her FORCE_RELOAD_EVERY exporttan sonra proje zorla yeniden yuklenir.
# Log analizi: karakter basina ~250-300 MB kalici RAM birikimi var, reload
# yalnizca undo stack'i temizliyor (~1-2 GB). 150 cok gec — ~110 karakterde
# sistem RAM'i dolup cokuyor. 15'te bir reload bu birikimi kontrol altinda tutar.
FORCE_RELOAD_EVERY = 15

# ── morph_key -> CC5 morph ID eslemesi ───────────────────────────────────────
# sensitivity_probe.csv'den turetildi (morph_key -> ilk gecerli morph_id)
MORPH_ID_MAP = {
    "abdomen_depth":   "cc embed morphs/embed_torso111",
    "abdomen_scale":   "cc embed morphs/embed_torso113",
    "abs_line":        "cc embed morphs/embed_torso106",
    "body_builder":    "cc embed morphs/embed_full_body1",
    "body_fat":        "cc embed morphs/embed_full_body3",
    "body_muscular":   "cc embed morphs/embed_full_body6",
    "body_thin":       "cc embed morphs/embed_full_body5",
    "breast_prox":     "cc embed morphs/embed_torso101",
    "breast_scale":    "cc embed morphs/embed_torso102",
    "chest_depth":     "cc embed morphs/embed_torso103",
    "chest_height":    "cc embed morphs/embed_torso112",
    "chest_scale":     "cc embed morphs/embed_torso104",
    "chest_width":     "cc embed morphs/embed_torso105",
    "forearm_len":     "cc embed morphs/embed_arm5",
    "forearm_scale":   "cc embed morphs/embed_arm2",
    "glute_scale":     "cc embed morphs/embed_torso1",
    "hip_len":         "cc embed morphs/embed_torso4",
    "hip_love_handles":"cc embed morphs/embed_torso107",
    "hip_scale":       "cc embed morphs/embed_torso2",
    "lower_leg_len":   "cc embed morphs/embed_leg5",
    "lower_leg_scale": "cc embed morphs/embed_leg2",
    "musc_abs":        "2025-05-08-15-26-33_embed_athetic_abs_iso_01",
    "musc_arm":        "2025-05-05-12-31-36_embed_athetic_arn_01",
    "musc_back":       "2025-05-05-12-31-03_embed_athetic_back_01",
    "musc_calf":       "2025-05-05-12-33-02_embed_athetic_calf_01",
    "musc_chest_a":    "2025-05-05-12-07-08_embed_athetic_chest_01",
    "musc_chest_b":    "2025-05-08-11-32-58_embed_athetic_chest_02",
    "musc_chest_c":    "2025-06-10-15-34-47_embed_athetic_chest_c",
    "musc_neck":       "2025-05-05-13-47-33_embed_athetic_chest_01",
    "musc_obliques":   "2025-05-08-15-29-44_embed_athetic_side_abs_01",
    "musc_shoulder":   "2025-05-05-12-22-16_embed_athetic_shoulder_01",
    "musc_thigh":      "2025-05-05-12-32-25_embed_athetic_thigh_01",
    "musc_waist":      "2025-05-05-12-18-34_embed_athetic_abs_01",
    "neck_len":        "cc embed morphs/embed_torso109",
    "neck_scale":      "cc embed morphs/embed_torso110",
    "pectoral_height": "cc embed morphs/embed_torso115",
    "pectoral_scale":  "cc embed morphs/embed_torso114",
    "shoulder_scale":  "cc embed morphs/embed_arm101",
    "skin_abs":        "2025-05-07-13-43-26_pack_skinny_abs_01",
    "skin_arm":        "2025-05-07-14-12-07_pack_skinny_arm_01",
    "skin_back":       "2025-06-10-17-08-24_pack_skinny_back_02",
    "skin_buttocks":   "2025-06-10-17-01-51_pack_skinny_bottom_02",
    "skin_calf":       "2025-05-07-14-35-43_pack_skinny_calf_01",
    "skin_chest":      "2025-05-08-14-58-30_pack_skinny_chest_03",
    "skin_neck":       "2025-05-07-12-04-51_pack_skinny_neck_01",
    "skin_ribcage":    "2025-05-07-12-27-17_pack_skinny_rib_01",
    "skin_shoulder":   "2025-05-07-12-21-11_pack_skinny_shoulder_01",
    "skin_spine":      "2025-05-07-14-17-56_pack_skinny_spine_01",
    "skin_thigh":      "2025-06-10-17-18-17_pack_skinny_thigh_02",
    "thigh_len":       "cc embed morphs/embed_leg4",
    "thigh_scale":     "cc embed morphs/embed_leg3",
    "upperarm_len":    "cc embed morphs/embed_arm4",
    "upperarm_scale":  "cc embed morphs/embed_arm3",
}

ALL_MORPH_IDS = list(MORPH_ID_MAP.values())

sys.path.insert(0, _ROOT)
sys.path.insert(0, _BASE)
from cc5_helpers import PROJECT_FILES

# ── Hazirlik ──────────────────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# ── Resource monitor: yeni konsolda otomatik baslat ──────────────────────────
# CC5 Script Editor kendi Python'unu kullanir; sistem Python'unu ac.
import subprocess as _sp
_SYSTEM_PYTHON  = r"C:\Users\HP\AppData\Local\Programs\Python\Python313\python.exe"
_monitor_script = os.path.join(_ROOT, "monitor_resources.py")
if os.path.exists(_monitor_script) and os.path.exists(_SYSTEM_PYTHON):
    try:
        _sp.Popen(
            [_SYSTEM_PYTHON, _monitor_script, "--interval", "10"],
            creationflags=_sp.CREATE_NEW_CONSOLE,
        )
    except Exception as _e:
        print(f"[monitor] baslatilamadi: {_e}")

log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)

def log(msg=""):
    print(msg)
    log_file.write(msg + "\n")

with open(CSV_PATH, "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

if GENDER_FILTER:
    rows = [r for r in rows if r["gender"] == GENDER_FILTER]
else:
    # Once male sonra female: gender switch reload sayisini ~4000'den ~1'e indirir
    rows = sorted(rows, key=lambda r: r["gender"], reverse=True)  # "male" > "female" → m once

if NODE_COUNT > 1:
    rows = rows[NODE_ID::NODE_COUNT]

rows = rows[START_IDX:]
total = len(rows)

# CSV'deki morph kolonlarini bul (morph_ prefix'li)
sample_row = rows[0]
morph_cols = {
    col[6:]: col          # "morph_body_fat" -> key="body_fat", col="morph_body_fat"
    for col in sample_row
    if col.startswith("morph_") and col[6:] in MORPH_ID_MAP
}

log(f"=== batch_export START {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
log(f"Node: {NODE_ID}/{NODE_COUNT} | Toplam: {total} karakter | Morph kolon sayisi: {len(morph_cols)}")
log()

# ── FBX export ayarlari ───────────────────────────────────────────────────────
fbx_setting = RLPy.RExportFbxSetting()
fbx_setting.SetOption(RLPy.EExportFbxOptions__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2_ResetBoneScale)
fbx_setting.EnableExportMotion(False)
fbx_setting.EnableBakeSubdivision(False)

# ── Ana dongu ──────────────────────────────────────────────────────────────────
done    = 0
skipped = 0
failed  = 0
errors  = []

current_gender = None

for i, row in enumerate(rows):
    char_id  = row["char_id"]
    gender   = row["gender"]
    fbx_path = os.path.join(OUTPUT_DIR, f"{char_id}.fbx")
    global_idx = START_IDX + i + 1

    render_done = os.path.exists(
        os.path.join(_ROOT, "renders", "silhouettes", char_id, f"{char_id}_front.png")
    )
    if not OVERWRITE and (os.path.exists(fbx_path) or render_done):
        skipped += 1
        continue

    force_reload = (done > 0 and done % FORCE_RELOAD_EVERY == 0)
    if gender != current_gender or force_reload:
        RLPy.RFileIO.LoadFile(PROJECT_FILES[gender])
        current_gender = gender
        reason = "zorla temizlik" if force_reload else gender
        log(f"  [project] yuklendi ({reason})")

    try:
        avatar  = RLPy.RScene.GetAvatars()[0]
        shaping = avatar.GetAvatarShapingComponent()

        # Tum morphlari sifirla (HD skin/muscle dahil)
        for mid in ALL_MORPH_IDS:
            shaping.SetShapingMorphWeight(mid, 0.0)

        # Sekil morphlarini set et
        for key, col in morph_cols.items():
            val = float(row.get(col, 0.0))
            if val != 0.0 and not key.startswith("skin_") and not key.startswith("musc_"):
                mid = MORPH_ID_MAP[key]
                shaping.SetShapingMorphWeight(mid, val)

        # ── Refinement: skin/muscle detay (US Navy BF%'e gore) ───────────────
        # Olcumlere etkisi dusuk — solver disinda uygulanir.
        navy_bfp  = float(row.get("navy_bfp",  0.0))
        gender_r  = row.get("gender", "female")
        muscular  = float(row.get("morph_body_muscular", 0.0))

        # Cinsiyet bazli esikler (tipik atletik BF araliklar)
        LEAN_HI   = 22.0 if gender_r == "female" else 13.0   # BF% alti: skinny detay
        MUSCLE_HI = 28.0 if gender_r == "female" else 18.0   # BF% alti + kasli: kas detay

        # Skinny detail: dusuk BF → kemik/damar gorunumu (maks 0.40)
        if navy_bfp < LEAN_HI:
            skin_w = round(min((LEAN_HI - navy_bfp) / LEAN_HI * 0.55, 0.40), 3)
        else:
            skin_w = 0.0

        # Muscle detail: dusuk/orta BF + yuksek muscular morph (maks 0.35)
        if navy_bfp < MUSCLE_HI and muscular > 0.15:
            muscle_w = round(min(muscular * 0.45, 0.35), 3)
        else:
            muscle_w = 0.0

        SKIN_MORPHS = [
            "skin_abs", "skin_arm", "skin_back", "skin_buttocks", "skin_calf",
            "skin_chest", "skin_neck", "skin_ribcage", "skin_shoulder",
            "skin_spine", "skin_thigh",
        ]
        MUSC_MORPHS = [
            "musc_abs", "musc_arm", "musc_back", "musc_calf",
            "musc_chest_a", "musc_chest_b", "musc_chest_c",
            "musc_neck", "musc_obliques", "musc_shoulder",
            "musc_thigh", "musc_waist",
        ]

        if skin_w > 0.01:
            for k in SKIN_MORPHS:
                if k in MORPH_ID_MAP:
                    shaping.SetShapingMorphWeight(MORPH_ID_MAP[k], skin_w)

        if muscle_w > 0.01:
            for k in MUSC_MORPHS:
                if k in MORPH_ID_MAP:
                    shaping.SetShapingMorphWeight(MORPH_ID_MAP[k], muscle_w)

        RLPy.RScene.SelectObject(avatar)
        RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, fbx_setting)

        size = os.path.getsize(fbx_path) if os.path.exists(fbx_path) else -1
        if size < 1000:
            raise RuntimeError(f"FBX cok kucuk ({size} bytes)")

        done += 1

        if done % 100 == 0 or i == total - 1:
            log(f"[{global_idx}/{START_IDX + total}] {done} export, "
                f"{skipped} atlandi, {failed} hata | son: {char_id}")

    except Exception as e:
        failed += 1
        errors.append(char_id)
        log(f"  [HATA] {char_id}: {e}")

    finally:
        try:
            del shaping, avatar
        except NameError:
            pass
        if (done + failed) % 100 == 0:
            gc.collect()

log()
log(f"=== TAMAMLANDI {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
log(f"Export: {done} | Atlandi: {skipped} | Hata: {failed}")
if errors:
    log(f"Hatali char_id'ler: {errors}")
log_file.close()

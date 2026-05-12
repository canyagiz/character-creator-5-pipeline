"""
bmi_probe_export.py — BMI Spektrum Probe Exporter
CC5 Script Editor'da calistir.

Normal ANSUR + extreme BMI dataseti birlestirip her BMI grubundan
3 karakter secer ve FBX export eder. Her grupta kadin/erkek dengesi
ve BMI icinde maksimum yayilim hedeflenir.

BMI gruplari:
  underweight  < 18.5
  normal       18.5 - 25
  overweight   25 - 30
  obese_I      30 - 35
  obese_II     35 - 40
  obese_III    40+

Cikti:
  fbx_export/probe_<grup>_<idx>.fbx
  logs/bmi_probe_list.csv
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
from cc5_helpers import PROJECT_FILES

INVERTED_MAIN    = str(_ROOT / "logs" / "dataset_inverted.csv")
INVERTED_EXTREME = str(_ROOT / "logs" / "dataset_inverted_extreme.csv")
OUTPUT_DIR       = str(_ROOT / "fbx_export")
PROBE_CSV        = str(_ROOT / "logs" / "bmi_probe_list.csv")
N_PER_GROUP      = 3
OVERWRITE        = True

os.makedirs(OUTPUT_DIR, exist_ok=True)

MORPH_ID_MAP = {
    "abdomen_depth":   "cc embed morphs/embed_torso111",
    "abdomen_scale":   "cc embed morphs/embed_torso113",
    "abs_line":        "cc embed morphs/embed_torso106",
    "body_builder":    "cc embed morphs/embed_full_body1",
    "body_fat":        "cc embed morphs/embed_full_body3",
    "body_muscular":   "cc embed morphs/embed_full_body6",
    "body_thin":       "cc embed morphs/embed_full_body5",
    "breast_scale":    "cc embed morphs/embed_torso102",
    "breast_prox":     "cc embed morphs/embed_torso101",
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

BMI_GROUPS = [
    ("underweight", 0.0,   20.0),
    ("normal",      20.0,  25.0),
    ("overweight",  25.0,  30.0),
    ("obese_I",     30.0,  35.0),
    ("obese_II",    35.0,  40.0),
    ("obese_III",   40.0, 999.0),
]


# ── Veri yukle ve birlestir ───────────────────────────────────────────────────
def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

rows_main    = load_csv(INVERTED_MAIN)
rows_extreme = load_csv(INVERTED_EXTREME)
all_rows     = rows_main + rows_extreme
print(f"Yuklendi: {len(rows_main)} ANSUR + {len(rows_extreme)} extreme = {len(all_rows)} toplam")

# BMI hesapla
def get_bmi(row):
    try:
        h = float(row.get("target_height_cm", 0))
        w = float(row.get("weight_kg", 0))
        if h > 0 and w > 0:
            return w / (h / 100) ** 2
    except (ValueError, ZeroDivisionError):
        pass
    return 0.0

for row in all_rows:
    row["_bmi"] = get_bmi(row)


# ── Her grup icin 3 karakter sec ──────────────────────────────────────────────
def select_group(candidates, n):
    """
    n karakter sec: once kadin+erkek dengesini kur,
    sonra BMI icinde maksimum yayilim sagla.
    """
    if not candidates:
        return []

    females = [r for r in candidates if r["gender"] == "female"]
    males   = [r for r in candidates if r["gender"] == "male"]

    # Her iki cinsiyetten en az 1 al (varsa), sonra BMI spread'e gore doldur
    chosen = []

    for pool in [females, males]:
        if pool:
            # Pool'u BMI'ya gore sirala, ortadan sec
            pool_sorted = sorted(pool, key=lambda r: r["_bmi"])
            mid = pool_sorted[len(pool_sorted) // 2]
            chosen.append(mid)

    # Kalan yerleri BMI extremlerinden doldur
    chosen_ids = {r["char_id"] for r in chosen}
    remaining  = sorted(
        [r for r in candidates if r["char_id"] not in chosen_ids],
        key=lambda r: r["_bmi"]
    )
    while len(chosen) < n and remaining:
        # Mevcut chosen'a uzakligi en fazla olani ekle
        best = max(remaining, key=lambda r: min(
            abs(r["_bmi"] - c["_bmi"]) for c in chosen
        ))
        chosen.append(best)
        chosen_ids.add(best["char_id"])
        remaining = [r for r in remaining if r["char_id"] not in chosen_ids]

    return chosen[:n]


probe_rows = []
for group_name, bmi_lo, bmi_hi in BMI_GROUPS:
    candidates = [r for r in all_rows if bmi_lo <= r["_bmi"] < bmi_hi]
    selected   = select_group(candidates, N_PER_GROUP)
    print(f"\n{group_name.upper()} (BMI {bmi_lo}-{bmi_hi}): {len(candidates)} aday -> {len(selected)} secildi")
    for r in selected:
        print(f"  {r['char_id']:<20} gender={r['gender']:<7} BMI={r['_bmi']:.1f}  "
              f"bel={float(r.get('target_waist_circ_cm',0)):.0f}  "
              f"kalca={float(r.get('target_hip_circ_cm',0)):.0f}  "
              f"MAE={float(r.get('inversion_mae_cm',0)):.2f}")
        r["_group"] = group_name
        probe_rows.append(r)

print(f"\nToplam probe: {len(probe_rows)} karakter")

# Probe listesi CSV'ye kaydet
fieldnames = ["char_id", "gender", "_group", "_bmi", "somatotype",
              "inversion_mae_cm", "weight_kg", "navy_bfp",
              "target_height_cm", "target_waist_circ_cm", "target_hip_circ_cm",
              "target_chest_circ_cm", "target_shoulder_width_cm"]
with open(PROBE_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(probe_rows)
print(f"Probe listesi kaydedildi: {PROBE_CSV}")


# ── FBX Export ────────────────────────────────────────────────────────────────
fbx_setting = RLPy.RExportFbxSetting()
fbx_setting.SetOption(RLPy.EExportFbxOptions__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2_ResetBoneScale)
fbx_setting.EnableExportMotion(False)
fbx_setting.EnableBakeSubdivision(False)

# Hangi kolonlarin morph agirligi icerdigini bul
sample = probe_rows[0]
morph_cols = {
    col[6:]: col
    for col in sample
    if col.startswith("morph_") and col[6:] in MORPH_ID_MAP
}

done = 0
failed = 0
current_gender = None

for i, row in enumerate(probe_rows):
    group    = row["_group"]
    char_id  = row["char_id"]
    gender   = row["gender"]

    # Probe icin yeni bir isim ver: probe_<grup>_<idx>
    probe_id = f"probe_{group}_{i:02d}"
    fbx_path = os.path.join(OUTPUT_DIR, f"{probe_id}.fbx")

    if not OVERWRITE and os.path.exists(fbx_path):
        print(f"  SKIP {probe_id}")
        continue

    if gender != current_gender:
        RLPy.RFileIO.LoadFile(PROJECT_FILES[gender])
        current_gender = gender
        print(f"  [project] {gender} yuklendi")

    try:
        avatar  = RLPy.RScene.GetAvatars()[0]
        shaping = avatar.GetAvatarShapingComponent()

        for mid in ALL_MORPH_IDS:
            shaping.SetShapingMorphWeight(mid, 0.0)

        for key, col in morph_cols.items():
            val = float(row.get(col, 0.0))
            if val != 0.0 and not key.startswith("skin_") and not key.startswith("musc_"):
                shaping.SetShapingMorphWeight(MORPH_ID_MAP[key], val)

        # Skin / muscle detay (navy BFP bazli, batch_export.py ile ayni mantik)
        navy_bfp = float(row.get("navy_bfp", 0.0))
        muscular = float(row.get("morph_body_muscular", 0.0))
        LEAN_HI   = 22.0 if gender == "female" else 13.0
        MUSCLE_HI = 28.0 if gender == "female" else 18.0

        skin_w = round(min((LEAN_HI - navy_bfp) / LEAN_HI * 0.55, 0.40), 3) \
                 if navy_bfp < LEAN_HI else 0.0
        muscle_w = round(min(muscular * 0.45, 0.35), 3) \
                   if navy_bfp < MUSCLE_HI and muscular > 0.15 else 0.0

        SKIN_MORPHS = ["skin_abs","skin_arm","skin_back","skin_buttocks","skin_calf",
                       "skin_chest","skin_neck","skin_ribcage","skin_shoulder","skin_spine","skin_thigh"]
        MUSC_MORPHS = ["musc_abs","musc_arm","musc_back","musc_calf","musc_chest_a",
                       "musc_chest_b","musc_chest_c","musc_neck","musc_obliques",
                       "musc_shoulder","musc_thigh","musc_waist"]

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
        print(f"  OK  {probe_id} | {group:<12} BMI={row['_bmi']:.1f} {gender}")

    except Exception as e:
        failed += 1
        print(f"  HATA {probe_id}: {e}")

    finally:
        try:
            del shaping, avatar
        except NameError:
            pass
        gc.collect()

print(f"\n=== TAMAMLANDI: {done} OK, {failed} hata ===")
print(f"Simdi pipeline.py'yi baslat: python pipeline.py --fbx-dir fbx_export")

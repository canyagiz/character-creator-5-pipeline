"""
somatotype_probe_export.py — Somatotype Gorsel Dogrulama Probe'u
CC5 Script Editor'da calistir.

Her somatotype icin 2 kadin + 2 erkek = 20 karakter export eder.
Secim kriterleri:
  - Somatotype'in en tipik ornekleri (WHR/SHR skoruna gore)
  - 2 karakter BMI'da farkli olacak (lean + heavier) — ayni seklin
    farkli kilolarda tutarli gorunup gorundugunu test etmek icin

Cikti: fbx_export/soma_<somatotype>_<gender>_<idx>.fbx
       logs/somatotype_probe_list.csv
"""

import RLPy
import csv
import gc
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from cc5_helpers import PROJECT_FILES

COMBINED_CSV = str(_ROOT / "logs" / "dataset_inverted_combined.csv")
OUTPUT_DIR   = str(_ROOT / "fbx_export")
PROBE_CSV    = str(_ROOT / "logs" / "somatotype_probe_list.csv")
N_PER_GENDER = 2   # her somatotype x her cinsiyet
OVERWRITE    = True

os.makedirs(OUTPUT_DIR, exist_ok=True)

MORPH_ID_MAP = {
    "abdomen_depth":   "cc embed morphs/embed_torso111",
    "abdomen_scale":   "cc embed morphs/embed_torso113",
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

SOMATOTYPES = ["apple", "hourglass", "pear", "rectangle", "v_shape"]

# Somatotype tipiklik skoru: bu skor ne kadar yuksekse o karakter
# somatotype'ini o kadar net temsil ediyor.
def typicality_score(soma, row):
    try:
        whr = float(row.get("target_WHR", 0))      # bel / kalca
        shr = float(row.get("target_SHR", 0))      # omuz / kalca_gen
        hc  = float(row.get("target_hip_chest", 0)) # kalca / gogus
        hw  = float(row.get("target_hip_width_circ", 0))
    except (ValueError, TypeError):
        return 0.0

    if soma == "apple":
        return whr                          # yuksek WHR = net elma
    if soma == "hourglass":
        return hc * (1.0 - whr)            # kalca > gogus + ince bel
    if soma == "pear":
        return hc - whr                    # kalca > gogus, bel dar degil
    if soma == "rectangle":
        return -(abs(whr - 0.87) + abs(hc - 1.0))  # her sey dengeli
    if soma == "v_shape":
        return shr                          # genis omuz / dar kalca
    return 0.0


# ── Veri yukle ────────────────────────────────────────────────────────────────
with open(COMBINED_CSV, encoding="utf-8") as f:
    all_rows = list(csv.DictReader(f))

def get_bmi(row):
    try:
        h = float(row.get("target_height_cm", 0))
        w = float(row.get("weight_kg", 0))
        if h > 0 and w > 0:
            return w / (h / 100) ** 2
    except (ValueError, ZeroDivisionError):
        pass
    return 0.0

for r in all_rows:
    r["_bmi"]   = get_bmi(r)
    r["_score"] = 0.0


# ── Secim ────────────────────────────────────────────────────────────────────
def select_for_soma(soma, gender, n):
    """
    Somatotype + cinsiyet eslesenleri arasından:
      - Her birinin tipiklik skoru hesaplanir
      - En tipik yarıdan (top 50%) sec
      - BMI'ya gore sirala, alt yarisini ve ust yarisini al
        (lean + heavier — ayni seklin iki kilosu)
    """
    pool = [r for r in all_rows
            if r["somatotype"] == soma and r["gender"] == gender]
    if not pool:
        print(f"  UYARI: {soma}/{gender} icin aday yok")
        return []

    for r in pool:
        r["_score"] = typicality_score(soma, r)

    # En tipik %50
    pool.sort(key=lambda r: r["_score"], reverse=True)
    top_half = pool[:max(n * 10, len(pool) // 2)]

    # BMI'ya gore sirala, lean + heavier sec
    top_half.sort(key=lambda r: r["_bmi"])
    if len(top_half) < n:
        return top_half

    # n=2: en dusuk BMI ve en yuksek BMI
    if n == 2:
        return [top_half[0], top_half[-1]]

    # n>2: esit aralikli ornekleme
    step = (len(top_half) - 1) / (n - 1)
    return [top_half[round(i * step)] for i in range(n)]


probe_rows = []
print("Secim:")
for soma in SOMATOTYPES:
    for gender in ["female", "male"]:
        selected = select_for_soma(soma, gender, N_PER_GENDER)
        print(f"\n  {soma.upper()} / {gender}:")
        for r in selected:
            print(f"    {r['char_id']:<22} BMI={r['_bmi']:.1f}  "
                  f"WHR={float(r.get('target_WHR',0)):.3f}  "
                  f"SHR={float(r.get('target_SHR',0)):.3f}  "
                  f"score={r['_score']:.3f}")
            r["_soma_group"] = soma
            probe_rows.append(r)

print(f"\nToplam: {len(probe_rows)} karakter")

# Probe CSV kaydet
with open(PROBE_CSV, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["char_id", "gender", "_soma_group", "_bmi", "somatotype",
                  "target_WHR", "target_SHR", "target_hip_chest",
                  "target_waist_circ_cm", "target_hip_circ_cm",
                  "target_chest_circ_cm", "target_shoulder_width_cm",
                  "inversion_mae_cm", "weight_kg"]
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

sample = probe_rows[0]
morph_cols = {
    col[6:]: col
    for col in sample
    if col.startswith("morph_") and col[6:] in MORPH_ID_MAP
}

SKIN_MORPHS = ["skin_abs","skin_arm","skin_back","skin_buttocks","skin_calf",
               "skin_chest","skin_neck","skin_ribcage","skin_shoulder","skin_spine","skin_thigh"]
MUSC_MORPHS = ["musc_abs","musc_arm","musc_back","musc_calf","musc_chest_a",
               "musc_chest_b","musc_chest_c","musc_neck","musc_obliques",
               "musc_shoulder","musc_thigh","musc_waist"]

done = 0
failed = 0
current_gender = None

for i, row in enumerate(probe_rows):
    soma    = row["_soma_group"]
    gender  = row["gender"]
    bmi_tag = "lean" if i % 2 == 0 else "heavy"
    probe_id = f"soma_{soma}_{gender[0]}_{bmi_tag}"
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

        navy_bfp = float(row.get("navy_bfp", 0.0))
        muscular = float(row.get("morph_body_muscular", 0.0))
        LEAN_HI   = 22.0 if gender == "female" else 13.0
        MUSCLE_HI = 28.0 if gender == "female" else 18.0

        skin_w = round(min((LEAN_HI - navy_bfp) / LEAN_HI * 0.55, 0.40), 3) \
                 if navy_bfp < LEAN_HI else 0.0
        muscle_w = round(min(muscular * 0.45, 0.35), 3) \
                   if navy_bfp < MUSCLE_HI and muscular > 0.15 else 0.0

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
        print(f"  OK  {probe_id:<32} BMI={row['_bmi']:.1f}  "
              f"WHR={float(row.get('target_WHR',0)):.3f}  "
              f"SHR={float(row.get('target_SHR',0)):.3f}")

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

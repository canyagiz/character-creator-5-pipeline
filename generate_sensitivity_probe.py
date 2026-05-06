"""
generate_sensitivity_probe.py
Her CC5 morph'unu tek tek min→max tarayarak sensitivity probe CSV'si üretir.
Tüm diğer morphlar 0'da tutulur.

Çıktı: logs/sensitivity_probe.csv
       → props/sensitivity_export.py ile CC5'te export edilir.

Çalıştır: python generate_sensitivity_probe.py
"""

import csv
import os
import sys
sys.path.insert(0, r"C:\Users\aliya\workspace\cc5-scripts")
from cc5_helpers import (
    M_BODY_FAT, M_BODY_THIN, M_BODY_MUSCULAR, M_BODY_BUILDER,
    M_SHOULDER_SCALE, M_UPPER_ARM_SCALE, M_UPPER_ARM_LENGTH,
    M_FOREARM_SCALE, M_FOREARM_LENGTH,
    M_CHEST_SCALE, M_CHEST_HEIGHT, M_CHEST_WIDTH, M_CHEST_DEPTH,
    M_BREAST_SCALE_B, M_BREAST_PROXIMITY,
    M_PECTORAL_SCALE, M_PECTORAL_HEIGHT,
    M_NECK_SCALE, M_NECK_LENGTH,
    M_ABDOMEN_SCALE, M_ABDOMEN_DEPTH, M_ABS_LINE_DEPTH,
    M_HIP_LOVE_HANDLES, M_HIP_SCALE, M_HIP_LENGTH,
    M_GLUTE_SCALE,
    M_THIGH_SCALE, M_THIGH_LENGTH,
    M_LOWER_LEG_SCALE, M_LOWER_LEG_LENGTH,
    M_MUSC_ARM, M_MUSC_SHOULDER, M_MUSC_BACK,
    M_MUSC_CHEST_A, M_MUSC_CHEST_B, M_MUSC_CHEST_C,
    M_MUSC_ABS, M_MUSC_OBLIQUES, M_MUSC_THIGH, M_MUSC_CALF,
    M_MUSC_NECK, M_MUSC_WAIST,
    M_SKIN_ARM, M_SKIN_SHOULDER, M_SKIN_BACK, M_SKIN_CHEST,
    M_SKIN_ABS, M_SKIN_RIBCAGE, M_SKIN_THIGH, M_SKIN_CALF,
    M_SKIN_BUTTOCKS, M_SKIN_NECK, M_SKIN_SPINE,
    ALL_MORPHS,
)

OUT_PATH = r"C:\Users\aliya\workspace\cc5-scripts\logs\sensitivity_probe.csv"
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

# ── Her morph için kısa isim ve test aralığı ──────────────────────────────────
# (kisa_isim, morph_id, lo, hi)
# lo/hi: CC5'te mantıklı aralık. Negatif aralıklar "incelme" yönü.
MORPHS_TO_PROBE = [
    # Full body presetler
    ("body_fat",       M_BODY_FAT,       0.0,  1.0),
    ("body_thin",      M_BODY_THIN,      0.0,  1.0),
    ("body_muscular",  M_BODY_MUSCULAR,  0.0,  1.0),
    ("body_builder",   M_BODY_BUILDER,   0.0,  1.0),

    # Omuz / kol
    ("shoulder_scale", M_SHOULDER_SCALE, -0.5, 1.0),
    ("upperarm_scale", M_UPPER_ARM_SCALE,-1.0, 1.0),
    ("upperarm_len",   M_UPPER_ARM_LENGTH,-1.0,1.0),
    ("forearm_scale",  M_FOREARM_SCALE,  -1.0, 1.0),
    ("forearm_len",    M_FOREARM_LENGTH, -1.0, 1.0),

    # Göğüs
    ("chest_scale",    M_CHEST_SCALE,    -0.5, 1.0),
    ("chest_width",    M_CHEST_WIDTH,    -0.5, 1.0),
    ("chest_depth",    M_CHEST_DEPTH,    -0.5, 1.0),
    ("chest_height",   M_CHEST_HEIGHT,   -1.0, 1.0),
    ("breast_scale",   M_BREAST_SCALE_B,  0.0, 1.0),
    ("breast_prox",    M_BREAST_PROXIMITY,0.0, 1.0),
    ("pectoral_scale", M_PECTORAL_SCALE,  0.0, 1.0),
    ("pectoral_height",M_PECTORAL_HEIGHT, 0.0, 1.0),

    # Boyun
    ("neck_scale",     M_NECK_SCALE,      0.0, 1.0),
    ("neck_len",       M_NECK_LENGTH,    -1.0, 1.0),

    # Karın / bel
    ("abdomen_scale",  M_ABDOMEN_SCALE,  -1.0, 1.0),
    ("abdomen_depth",  M_ABDOMEN_DEPTH,  -1.0, 1.0),
    ("abs_line",       M_ABS_LINE_DEPTH,  0.0, 1.0),

    # Kalça / glute
    ("hip_love_handles",M_HIP_LOVE_HANDLES,0.0,1.0),
    ("hip_scale",      M_HIP_SCALE,      -0.3, 1.0),
    ("hip_len",        M_HIP_LENGTH,     -1.0, 1.0),
    ("glute_scale",    M_GLUTE_SCALE,    -1.0, 1.0),

    # Bacak
    ("thigh_scale",    M_THIGH_SCALE,    -1.0, 1.0),
    ("thigh_len",      M_THIGH_LENGTH,   -1.0, 1.0),
    ("lower_leg_scale",M_LOWER_LEG_SCALE,-1.0, 1.0),
    ("lower_leg_len",  M_LOWER_LEG_LENGTH,-1.0,1.0),

    # HD kas morphları
    ("musc_arm",       M_MUSC_ARM,        0.0, 1.0),
    ("musc_shoulder",  M_MUSC_SHOULDER,   0.0, 1.0),
    ("musc_back",      M_MUSC_BACK,       0.0, 1.0),
    ("musc_chest_a",   M_MUSC_CHEST_A,    0.0, 1.0),
    ("musc_chest_b",   M_MUSC_CHEST_B,    0.0, 1.0),
    ("musc_chest_c",   M_MUSC_CHEST_C,    0.0, 1.0),
    ("musc_abs",       M_MUSC_ABS,        0.0, 1.0),
    ("musc_obliques",  M_MUSC_OBLIQUES,   0.0, 1.0),
    ("musc_thigh",     M_MUSC_THIGH,      0.0, 1.0),
    ("musc_calf",      M_MUSC_CALF,       0.0, 1.0),
    ("musc_neck",      M_MUSC_NECK,       0.0, 1.0),
    ("musc_waist",     M_MUSC_WAIST,      0.0, 1.0),

    # HD ince deri morphları
    ("skin_arm",       M_SKIN_ARM,        0.0, 1.0),
    ("skin_shoulder",  M_SKIN_SHOULDER,   0.0, 1.0),
    ("skin_back",      M_SKIN_BACK,       0.0, 1.0),
    ("skin_chest",     M_SKIN_CHEST,      0.0, 1.0),
    ("skin_abs",       M_SKIN_ABS,        0.0, 1.0),
    ("skin_ribcage",   M_SKIN_RIBCAGE,    0.0, 1.0),
    ("skin_thigh",     M_SKIN_THIGH,      0.0, 1.0),
    ("skin_calf",      M_SKIN_CALF,       0.0, 1.0),
    ("skin_buttocks",  M_SKIN_BUTTOCKS,   0.0, 1.0),
    ("skin_neck",      M_SKIN_NECK,       0.0, 1.0),
    ("skin_spine",     M_SKIN_SPINE,      0.0, 1.0),
]

N_STEPS = 11   # 0→max arası 11 nokta (min, 10%, 20%, ..., 100%)
GENDERS = ["female", "male"]

rows = []

for gender in GENDERS:
    g = gender[0]

    # Baseline: tüm morphlar 0
    rows.append({
        "char_id":     f"sens_baseline_{g}",
        "gender":      gender,
        "morph_key":   "baseline",
        "morph_id":    "",
        "morph_value": 0.0,
    })

    for key, morph_id, lo, hi in MORPHS_TO_PROBE:
        for step in range(N_STEPS):
            t   = step / (N_STEPS - 1)          # 0.0 → 1.0
            val = round(lo + t * (hi - lo), 4)  # lo → hi
            rows.append({
                "char_id":     f"sens_{key}_{step:02d}_{g}",
                "gender":      gender,
                "morph_key":   key,
                "morph_id":    morph_id,
                "morph_value": val,
            })

with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["char_id","gender","morph_key","morph_id","morph_value"])
    writer.writeheader()
    writer.writerows(rows)

n_morphs = len(MORPHS_TO_PROBE)
total    = len(rows)
print(f"Yazildi: {OUT_PATH}")
print(f"Morph sayisi : {n_morphs}")
print(f"Adim / morph : {N_STEPS}  ({MORPHS_TO_PROBE[0][2]:.1f} -> max)")
print(f"Gender       : {len(GENDERS)}")
print(f"Toplam FBX   : {total}  ({n_morphs} x {N_STEPS} x {len(GENDERS)} + {len(GENDERS)} baseline)")
print()
print("Sonraki adim:")
print("  CC5 Script Editor -> props/sensitivity_export.py calistir")

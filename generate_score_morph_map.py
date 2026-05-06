"""
generate_score_morph_map.py
Her input score kombinasyonu icin compute_all_weights ciktisini kayit eder.
CC5 gerektirmez - saf Python.

Cikti: logs/score_to_morph_map.csv
  Satirlar : score probe kombinasyonlari (her slider ayri ayri 0->1 taraniyor)
  Sutunlar  : tum CC5 morph agirliklari (compute_all_weights ciktisi)

Calistir: python generate_score_morph_map.py
"""

import csv
import os
import sys
sys.path.insert(0, r"C:\Users\aliya\workspace\cc5-scripts")
from cc5_helpers import compute_all_weights, ALL_MORPHS

OUT_PATH = r"C:\Users\aliya\workspace\cc5-scripts\logs\score_to_morph_map.csv"
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

# Baseline deger (degistirilmeyen sliderlar bu degerle tutulur)
BASELINE = {
    "fat":                    0.0,
    "muscle":                 0.0,
    "height_score":           0.5,
    "chest_height_score":     0.5,
    "hip_length_score":       0.5,
    "thigh_length_score":     0.5,
    "lower_leg_length_score": 0.5,
    "upper_arm_length_score": 0.5,
    "forearm_length_score":   0.5,
    "neck_length_score":      0.5,
    "hip_score":              0.0,
    "waist_def_score":        0.0,
    "pattern":                "balanced",
}

# Hangi input skorlari taranacak
PROBE_SCORES = [
    "fat", "muscle", "height_score",
    "chest_height_score", "hip_length_score", "thigh_length_score",
    "lower_leg_length_score", "upper_arm_length_score", "forearm_length_score",
    "neck_length_score", "hip_score", "waist_def_score",
]

N_STEPS = 11   # 0.0, 0.1, ..., 1.0
GENDERS = ["female", "male"]

# Morph ID'leri kisa isimlerle eslestir (okunabilirlik icin)
MORPH_SHORT = {m: m.split("/")[-1].replace("embed_", "").replace("_embed_", "_") for m in ALL_MORPHS}

rows = []

for gender in GENDERS:
    g = gender[0]

    # Baseline satiri
    b = dict(BASELINE)
    weights = compute_all_weights(**b, gender=gender)
    row = {"char_id": f"score_baseline_{g}", "gender": gender, "varied_score": "baseline", "score_value": 0.0}
    row.update({MORPH_SHORT[m]: round(weights.get(m, 0.0), 4) for m in ALL_MORPHS})
    rows.append(row)

    for score_key in PROBE_SCORES:
        for step in range(N_STEPS):
            val = round(step / (N_STEPS - 1), 1)
            params = dict(BASELINE)
            params[score_key] = val
            weights = compute_all_weights(**params, gender=gender)

            row = {
                "char_id":      f"score_{score_key}_{step:02d}_{g}",
                "gender":       gender,
                "varied_score": score_key,
                "score_value":  val,
            }
            # Input skorlarin anlık degerleri
            row["fat"]            = params["fat"]
            row["muscle"]         = params["muscle"]
            row["hip_score"]      = params["hip_score"]
            row["waist_def_score"]= params["waist_def_score"]
            row["height_score"]   = params["height_score"]
            # Morph ciktilari
            row.update({MORPH_SHORT[m]: round(weights.get(m, 0.0), 4) for m in ALL_MORPHS})
            rows.append(row)

# Fieldnames
meta_cols   = ["char_id", "gender", "varied_score", "score_value",
               "fat", "muscle", "hip_score", "waist_def_score", "height_score"]
morph_cols  = [MORPH_SHORT[m] for m in ALL_MORPHS]
fieldnames  = meta_cols + morph_cols

with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

print(f"Yazildi : {OUT_PATH}")
print(f"Satirlar : {len(rows)}")
print(f"Sutunlar : {len(fieldnames)}  ({len(morph_cols)} morph + {len(meta_cols)} meta)")
print()
print("Icerik:")
print("  - Her satirda: hangi score degistirildi + o anki deger")
print("  - Tum morph agirlik ciktilari yan yana")
print("  - compute_all_weights formulunun tam kaydi")

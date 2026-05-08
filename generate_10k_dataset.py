"""
generate_10k_dataset.py
Jacobian matrisi + ANSUR aralik kisitlari ile 10K karakter veri seti uretir.

Her satir icin:
  - LHS ile morph agirliklari orneklenir
  - Jacobian ile olcumler tahmin edilir
  - ANSUR P5-P95 bandinda olanlar kabul edilir
  - Olcumlerden somatotype etiketi atanir

Cikti: logs/dataset_10k.csv

Calistir: python generate_10k_dataset.py
"""

import pandas as pd
import numpy as np
from scipy.stats import qmc
import os, json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

JAC_CSV    = str(_ROOT / "logs" / "jacobian.csv")
RANGES_CSV = str(_ROOT / "logs" / "ansur_ranges.csv")
SENS_CSV   = str(_ROOT / "logs" / "sensitivity_measurements.csv")
OUT_CSV    = str(_ROOT / "logs" / "dataset_10k.csv")
os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

TARGET_N = 5000   # cinsiyet basina

# ── Veri yukle ────────────────────────────────────────────────────────────────
jac_full = pd.read_csv(JAC_CSV, index_col="morph_key")

MEASUREMENTS = [
    "shoulder_width_cm", "hip_width_cm",
    "chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
    "neck_circ_cm", "bicep_circ_cm", "mid_thigh_circ_cm", "calf_circ_cm",
]   # height_cm Jacobian'da 0 — ayri handle edilecek

# Baseline (tum morphlar 0 hali)
sens = pd.read_csv(SENS_CSV)
baseline = {}
for gender in ["female", "male"]:
    b = sens[(sens.morph_key == "baseline") & (sens.gender == gender)]
    if b.empty:
        b = sens[(sens.morph_value == 0.0) & (sens.gender == gender)].head(1)
    baseline[gender] = {m: b[m].values[0] for m in MEASUREMENTS if m in b.columns}

# ANSUR aralik kisitlari
ranges = pd.read_csv(RANGES_CSV)
def get_range(gender, meas):
    r = ranges[(ranges.gender == gender) & (ranges.measurement == meas)]
    if r.empty:
        return None, None
    return float(r["P5"].values[0]), float(r["P95"].values[0])

# ── Ornekleme uzayi — key morphlar ────────────────────────────────────────────
# Sadece Jacobian'da anlamli etkisi olan morphlar
# (morph_adi, lo, hi)
KEY_MORPHS = [
    # Genel vucut hacmi — en buyuk etki
    ("body_fat",        0.0,  1.0),
    ("body_muscular",   0.0,  1.0),
    ("body_thin",       0.0,  1.0),
    ("body_builder",    0.0,  0.5),

    # Ust vucut genisligi (shoulder_width bunlardan geliyor)
    ("chest_scale",    -0.3,  1.0),
    ("chest_width",    -0.3,  1.0),

    # Bel / karin
    ("abdomen_scale",  -0.5,  1.0),
    ("abdomen_depth",  -0.5,  1.0),

    # Kalca / alt vucut
    ("hip_scale",      -0.2,  1.0),
    ("glute_scale",    -0.5,  1.0),
    ("thigh_scale",    -0.5,  1.0),

    # Uzuvlar
    ("upperarm_scale", -0.5,  1.0),
    ("lower_leg_scale",-0.5,  1.0),
]

MORPH_NAMES = [m[0] for m in KEY_MORPHS]
MORPH_LO    = np.array([m[1] for m in KEY_MORPHS])
MORPH_HI    = np.array([m[2] for m in KEY_MORPHS])

# Probe CSV'deki morph aralik bilgisi (Jacobian normalizasyonu icin)
# Jacobian = total_delta / full_range, biz birim basina etkiye cevirmek icin
# morph deger araligini bilmemiz lazim
MORPH_FULL_RANGE = {
    "body_fat": 1.0, "body_muscular": 1.0, "body_thin": 1.0, "body_builder": 1.0,
    "chest_scale": 1.5, "chest_width": 1.5,
    "abdomen_scale": 2.0, "abdomen_depth": 2.0,
    "hip_scale": 1.3, "glute_scale": 2.0, "thigh_scale": 2.0,
    "upperarm_scale": 2.0, "lower_leg_scale": 2.0,
}

# Jacobian'i cm/birim'e donustur
jac = jac_full.loc[jac_full.index.isin(MORPH_NAMES), MEASUREMENTS].copy()
for morph in jac.index:
    full_range = MORPH_FULL_RANGE.get(morph, 1.0)
    jac.loc[morph] = jac.loc[morph] / full_range

# ── Somatotype kurallari ──────────────────────────────────────────────────────
def derive_somatotype(meas, gender):
    shoulder = meas.get("shoulder_width_cm", 0)
    hip_w    = meas.get("hip_width_cm", 0)
    waist    = meas.get("waist_circ_cm", 0)
    hip_c    = meas.get("hip_circ_cm", 0)
    chest    = meas.get("chest_circ_cm", 0)

    if hip_c == 0:
        return "unknown"

    whr = waist / hip_c
    shr = shoulder / hip_w if hip_w > 0 else 1.0

    whr_apple    = 0.90 if gender == "female" else 0.97
    whr_hourglass= 0.77 if gender == "female" else 0.87
    shr_vshape   = 1.32 if gender == "male"   else 1.22
    hip_pear     = chest + 4

    if shr > shr_vshape:
        return "v_shape"
    if hip_c > hip_pear and whr < whr_hourglass:
        return "hourglass"
    if hip_c > hip_pear:
        return "pear"
    if whr > whr_apple:
        return "apple"
    return "rectangle"

# ── Uretim donguleri ──────────────────────────────────────────────────────────
rng = np.random.default_rng(42)
all_rows = []

for gender in ["female", "male"]:
    base = baseline[gender]
    accepted = 0
    sampled  = 0
    batch_sz = TARGET_N * 4   # oversample, kisittan gec
    seed_offset = 0

    print(f"\n{gender.upper()} uretiliyor (hedef: {TARGET_N})...")

    while accepted < TARGET_N:
        # LHS ornekleme
        sampler = qmc.LatinHypercube(d=len(KEY_MORPHS), seed=seed_offset)
        unit = sampler.random(n=batch_sz)
        morphs_raw = qmc.scale(unit, MORPH_LO, MORPH_HI)
        seed_offset += 1

        for w in morphs_raw:
            if accepted >= TARGET_N:
                break
            sampled += 1

            morph_vals = dict(zip(MORPH_NAMES, w))

            # Biyolojik kisit: fat + thin + builder toplami < 1.4
            vol_sum = morph_vals["body_fat"] + morph_vals["body_thin"] + morph_vals["body_builder"]
            if vol_sum > 1.4:
                continue

            # fat + muscular birlikte max olamaz
            if morph_vals["body_fat"] > 0.7 and morph_vals["body_muscular"] > 0.7:
                continue

            # Olcum tahmini: baseline + Jacobian * morph_val
            pred = dict(base)
            for morph, val in morph_vals.items():
                if morph not in jac.index:
                    continue
                for meas in MEASUREMENTS:
                    pred[meas] = pred.get(meas, 0) + jac.loc[morph, meas] * val

            # ANSUR P5-P95 kisit kontrolu
            valid = True
            for meas in MEASUREMENTS:
                lo, hi = get_range(gender, meas)
                if lo is None:
                    continue
                if not (lo <= pred.get(meas, 0) <= hi):
                    valid = False
                    break
            if not valid:
                continue

            # Somatotype
            somatotype = derive_somatotype(pred, gender)

            row = {
                "char_id":    f"{gender[0]}_{accepted:05d}",
                "gender":     gender,
                "somatotype": somatotype,
            }
            row.update({f"morph_{k}": round(v, 4) for k, v in morph_vals.items()})
            row.update({f"pred_{m}": round(pred[m], 2) for m in MEASUREMENTS})
            all_rows.append(row)
            accepted += 1

        print(f"  orneklenen: {sampled:6d}  kabul: {accepted:5d}  oran: {accepted/sampled*100:.1f}%")

# ── Kaydet ve ozet ────────────────────────────────────────────────────────────
df = pd.DataFrame(all_rows)
df.to_csv(OUT_CSV, index=False, encoding="utf-8")

print(f"\n=== SONUC ===")
print(f"Toplam: {len(df)} satir")
print(f"\nSomatotype dagilimi:")
print(df.groupby(["gender","somatotype"]).size().unstack(fill_value=0).to_string())
print(f"\nPred olcum ozeti (female):")
pred_cols = [f"pred_{m}" for m in MEASUREMENTS]
print(df[df.gender=="female"][pred_cols].describe().round(1).to_string())
print(f"\nKaydedildi: {OUT_CSV}")

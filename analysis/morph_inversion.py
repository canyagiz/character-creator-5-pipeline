"""
morph_inversion.py
Her ANSUR satiri icin: hedef olcumler -> CC5 morph agirliklarini bul.

Yontem: J * w ≈ target_delta = ansur_measurement - cc5_baseline
        scipy.optimize.lsq_linear ile coz (bounds dahil)

Oran kisitlari (9 vücut oranı + 2 segment oranı): her ANSUR satiri icin gercek
oran hedef olarak Jacobian'a ek satirlar halinde eklenir.

Segment uzunluklari (arm + leg) ayri hedef olarak kullanılır:
  - upper_arm_length_cm, forearm_length_cm: ANSUR shoulderelbowlength/radialestylionlength
  - upper_leg_length_cm: (trochanterionheight - tibialheight) / 10
  - lower_leg_length_cm: tibialheight / 10

Cikti: logs/dataset_inverted.csv

Calistir: python analysis/morph_inversion.py
"""

import pandas as pd
import numpy as np
from scipy.optimize import lsq_linear
import math
import os

def navy_body_fat_pct(gender, waist_cm, hip_cm, neck_cm, height_cm):
    """US Navy body fat formulu (inch cinsinden hesaplar)."""
    CM_TO_IN = 1 / 2.54
    h = height_cm * CM_TO_IN
    w = waist_cm  * CM_TO_IN
    n = neck_cm   * CM_TO_IN
    if gender == "female":
        val = 163.205 * math.log10(w + hip_cm * CM_TO_IN - n) \
              - 97.684 * math.log10(h) - 78.387
    else:
        val = 86.010 * math.log10(w - n) - 70.041 * math.log10(h) + 36.76
    return round(max(0.0, val), 2)

ANSUR_CSV  = r"C:\Users\aliya\workspace\cc5-scripts\logs\ansur_samples_10k.csv"
JAC_CSV    = r"C:\Users\aliya\workspace\cc5-scripts\logs\jacobian.csv"
SENS_CSV   = r"C:\Users\aliya\workspace\cc5-scripts\logs\sensitivity_measurements.csv"
PROBE_CSV  = r"C:\Users\aliya\workspace\cc5-scripts\logs\sensitivity_probe.csv"
OUT_CSV    = r"C:\Users\aliya\workspace\cc5-scripts\logs\dataset_inverted.csv"
os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

# Inversion hedef olcumleri
# total_leg_length_cm kaldirildi — upper + lower ayri hedef olarak var
MEASUREMENTS = [
    "height_cm",
    "shoulder_width_cm", "hip_width_cm",
    "chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
    "neck_circ_cm", "bicep_circ_cm", "forearm_circ_cm", "mid_thigh_circ_cm", "calf_circ_cm",
    "upper_arm_length_cm", "forearm_length_cm",
    "upper_leg_length_cm", "lower_leg_length_cm",
]

# Oran kisitlari: (isim, pay_kolonu, payda_kolonu)
RATIO_CONSTRAINTS = [
    # Vücut sekli oranları
    ("WHR",            "waist_circ_cm",     "hip_circ_cm"),
    ("SHR",            "shoulder_width_cm", "hip_width_cm"),
    ("leg_taper",      "mid_thigh_circ_cm", "calf_circ_cm"),
    ("chest_waist",    "chest_circ_cm",     "waist_circ_cm"),
    ("hip_chest",      "hip_circ_cm",       "chest_circ_cm"),
    ("neck_chest",     "neck_circ_cm",      "chest_circ_cm"),
    ("bicep_thigh",    "bicep_circ_cm",     "mid_thigh_circ_cm"),
    ("shoulder_chest", "shoulder_width_cm", "chest_circ_cm"),
    ("hip_width_circ", "hip_width_cm",      "hip_circ_cm"),
    # Segment oranları — bunlar olmadan solver üst/alt uzuvları dengesiz karıştırır
    ("arm_ratio",        "forearm_length_cm",   "upper_arm_length_cm"),
    ("leg_ratio",        "lower_leg_length_cm", "upper_leg_length_cm"),
    # Kol vs bacak simetrisi ve koniklik
    ("bicep_calf",       "bicep_circ_cm",       "calf_circ_cm"),
    ("forearm_bicep",    "forearm_circ_cm",     "bicep_circ_cm"),
    ("shoulder_hip_circ","shoulder_width_cm",   "hip_circ_cm"),
]

RATIO_WEIGHT = 1.5

# ANSUR -> CC5 segment hedefleri icin
# trochanterionheight - tibialheight = ust bacak (her ikisi de /10 ile cm'e cevrilmis)
# tibialheight = alt bacak hedefi
TROCH_RATIO = {"female": 0.519, "male": 0.513}   # stature'dan tahmin icin (fallback)

# ── Veri yukle ────────────────────────────────────────────────────────────────
print("Veriler yukleniyor...")
ansur   = pd.read_csv(ANSUR_CSV)
jac_full= pd.read_csv(JAC_CSV, index_col="morph_key")
sens    = pd.read_csv(SENS_CSV)
probe   = pd.read_csv(PROBE_CSV)

# Baseline (tum morphlar 0 hali — sensitivity CSV'nin baseline satirindan)
baseline = {}
for gender in ["female", "male"]:
    b = sens[(sens.morph_key == "baseline") & (sens.gender == gender)]
    base = {m: float(b[m].values[0]) for m in MEASUREMENTS if m in b.columns}
    baseline[gender] = base

print(f"  ANSUR: {len(ansur)} satir")
print(f"  Jacobian: {jac_full.shape}")
print(f"  Baseline female: shoulder={baseline['female'].get('shoulder_width_cm','?')}  "
      f"upper_arm={baseline['female'].get('upper_arm_length_cm','?')}  "
      f"upper_leg={baseline['female'].get('upper_leg_length_cm','?')}")

# ── Morph sinirlari (probe CSV'den lo/hi) ────────────────────────────────────
morph_bounds = {}
for morph_key, grp in probe.groupby("morph_key"):
    morph_bounds[morph_key] = (grp["morph_value"].min(), grp["morph_value"].max())

# Jacobian: sadece MEASUREMENTS kolonlarini al, per-unit'e cevir
jac = jac_full[[m for m in MEASUREMENTS if m in jac_full.columns]].copy()

# Eksik kolon varsa 0 ile doldur (eski Jacobian'da segment uzunluklari yoksa)
for m in MEASUREMENTS:
    if m not in jac.columns:
        jac[m] = 0.0

for morph in jac.index:
    if morph in morph_bounds:
        lo, hi = morph_bounds[morph]
        full_range = hi - lo
        if full_range > 1e-6:
            jac.loc[morph] = jac.loc[morph] / full_range

jac = jac[MEASUREMENTS]

# Sadece gorsel olarak dogal vucut sekli morphlari
# upperarm_len ve forearm_len eklendi (arm segment uzunlukları icin)
SHAPE_MORPHS = [
    "body_fat", "body_thin", "body_muscular", "body_builder",
    "chest_scale", "chest_width", "chest_depth",
    "breast_scale",
    "abdomen_scale", "abdomen_depth",
    "hip_scale", "glute_scale",
    "thigh_scale", "lower_leg_scale",
    "upperarm_scale", "forearm_scale",
    "neck_scale",
    "thigh_len", "lower_leg_len",
    "hip_len", "chest_height", "neck_len",
    "upperarm_len", "forearm_len",
]
jac = jac.loc[jac.index.isin(SHAPE_MORPHS)]

ALL_MORPHS = jac.index.tolist()
print(f"  Morph sayisi: {len(ALL_MORPHS)} | Olcum sayisi: {len(MEASUREMENTS)}")
print(f"  Oran kisiti: {len(RATIO_CONSTRAINTS)} (agirlik: {RATIO_WEIGHT})")

MEAS_IDX = {m: i for i, m in enumerate(MEASUREMENTS)}
valid_ratios = [
    (name, num, den)
    for name, num, den in RATIO_CONSTRAINTS
    if num in MEAS_IDX and den in MEAS_IDX
]

# ── Somatotype kurali ─────────────────────────────────────────────────────────
def derive_somatotype(row):
    sh = row.get("shoulder_width_cm", 0)
    hw = row.get("hip_width_cm", 0)
    w  = row.get("waist_circ_cm", 0)
    hc = row.get("hip_circ_cm", 0)
    ch = row.get("chest_circ_cm", 0)
    gender = row.get("gender", "female")
    if hc == 0 or hw == 0:
        return "unknown"
    whr = w / hc
    shr = sh / hw
    if gender == "female":
        if shr > 1.36 and sh > 47:          return "v_shape"
        if hc > ch + 5 and whr < 0.77:      return "hourglass"
        if hc > ch + 5:                      return "pear"
        if whr > 0.92:                       return "apple"
        return "rectangle"
    else:
        if shr > 1.50:                       return "v_shape"
        if hc > ch + 4 and whr < 0.87:      return "hourglass"
        if hc > ch + 4:                      return "pear"
        if whr > 0.97:                       return "apple"
        return "rectangle"

# ── Inversion ─────────────────────────────────────────────────────────────────
J = jac.values  # (n_morphs, n_meas)

bounds_lo = np.array([morph_bounds.get(m, (0, 1))[0] for m in ALL_MORPHS])
bounds_hi = np.array([morph_bounds.get(m, (0, 1))[1] for m in ALL_MORPHS])

rows_out = []
n_total  = len(ansur)
errors   = []
ratio_errors = {name: [] for name, _, _ in valid_ratios}

print(f"\nInversion basliyor: {n_total} satir...")

for i, ansur_row in ansur.iterrows():
    gender = ansur_row["gender"]
    base   = baseline[gender]

    # Bacak segment hedefleri: ANSUR trochanterion + tibial height'tan turet
    troch_cm  = ansur_row.get("trochanterion_height_cm", None)
    tibial_cm = ansur_row.get("tibial_height_cm", None)

    if troch_cm and troch_cm > 0 and tibial_cm and tibial_cm > 0:
        target_upper_leg = troch_cm - tibial_cm
        target_lower_leg = tibial_cm
    else:
        # Fallback: stature oranından tahmin
        stature_cm = ansur_row.get("height_cm", 170)
        total_leg  = stature_cm * TROCH_RATIO[gender]
        base_total = base.get("upper_leg_length_cm", 46.0) + base.get("lower_leg_length_cm", 47.15)
        # Varsayılan oran: 46/(46+47.15) = 0.494 üst bacak
        target_upper_leg = total_leg * 0.494
        target_lower_leg = total_leg * 0.506

    # Hedef delta: ANSUR olcumu - CC5 baseline
    target_delta = np.array([
        (target_upper_leg - base.get("upper_leg_length_cm", 46.0)) if m == "upper_leg_length_cm"
        else (target_lower_leg - base.get("lower_leg_length_cm", 47.15)) if m == "lower_leg_length_cm"
        else float(ansur_row.get(m, base.get(m, 0))) - base.get(m, 0)
        for m in MEASUREMENTS
    ])

    # Oran kisiti satirlarini ekle
    extra_rows = []
    extra_b    = []

    for name, num_col, den_col in valid_ratios:
        # Segment oranları için ANSUR'daki hedef değerleri kullan
        if name == "arm_ratio":
            num_val = ansur_row.get("forearm_length_cm", 0)
            den_val = ansur_row.get("upper_arm_length_cm", 1)
        elif name == "leg_ratio":
            num_val = target_lower_leg
            den_val = target_upper_leg if target_upper_leg > 1e-6 else 1.0
        else:
            num_val = float(ansur_row.get(num_col, 0))
            den_val = float(ansur_row.get(den_col, 0))

        if den_val < 1e-6:
            continue
        R = num_val / den_val

        num_i = MEAS_IDX[num_col]
        den_i = MEAS_IDX[den_col]
        new_row = (J.T[num_i, :] - R * J.T[den_i, :]) * RATIO_WEIGHT
        new_b   = (R * base.get(den_col, 0) - base.get(num_col, 0)) * RATIO_WEIGHT
        extra_rows.append(new_row)
        extra_b.append(new_b)

    if extra_rows:
        A_aug = np.vstack([J.T] + extra_rows)
        b_aug = np.concatenate([target_delta, extra_b])
    else:
        A_aug, b_aug = J.T, target_delta

    result = lsq_linear(
        A_aug, b_aug,
        bounds=(bounds_lo, bounds_hi),
        method="bvls",
        max_iter=300,
    )

    w = result.x
    pred_delta = J.T @ w
    pred = {m: round(base.get(m, 0) + pred_delta[j], 2) for j, m in enumerate(MEASUREMENTS)}
    mae  = float(np.mean(np.abs(pred_delta - target_delta)))

    ansur_meas = {m: ansur_row.get(m, 0) for m in MEASUREMENTS}
    ansur_meas["gender"] = gender
    somatotype = derive_somatotype(ansur_meas)

    # US Navy body fat %
    navy_bfp = navy_body_fat_pct(
        gender,
        waist_cm  = float(ansur_row.get("waist_circ_cm",  0)),
        hip_cm    = float(ansur_row.get("hip_circ_cm",    0)),
        neck_cm   = float(ansur_row.get("neck_circ_cm",   0)),
        height_cm = float(ansur_row.get("height_cm",      0)),
    )

    row = {
        "char_id":          ansur_row["char_id"],
        "gender":           gender,
        "somatotype":       somatotype,
        "inversion_mae_cm": round(mae, 3),
        "weight_kg":        round(float(ansur_row.get("weight_kg", 0)), 2),
        "navy_bfp":         navy_bfp,
    }
    for m in MEASUREMENTS:
        if m == "upper_leg_length_cm":
            row["target_upper_leg_length_cm"] = round(target_upper_leg, 2)
        elif m == "lower_leg_length_cm":
            row["target_lower_leg_length_cm"] = round(target_lower_leg, 2)
        else:
            row[f"target_{m}"] = round(float(ansur_row.get(m, 0)), 2)

    for morph, val in zip(ALL_MORPHS, w):
        row[f"morph_{morph}"] = round(float(val), 4)

    for m, v in pred.items():
        row[f"pred_{m}"] = v

    for name, num_col, den_col in valid_ratios:
        if name == "leg_ratio":
            t_num, t_den = target_lower_leg, target_upper_leg
        elif name == "arm_ratio":
            t_num = float(ansur_row.get("forearm_length_cm", 0))
            t_den = float(ansur_row.get("upper_arm_length_cm", 1))
        else:
            t_num = float(ansur_row.get(num_col, 0))
            t_den = float(ansur_row.get(den_col, 0))
        p_den = pred.get(den_col, 0)
        row[f"target_{name}"] = round(t_num / t_den, 4) if t_den > 1e-6 else 0.0
        row[f"pred_{name}"]   = round(pred.get(num_col, 0) / p_den, 4) if p_den > 1e-6 else 0.0
        ratio_errors[name].append(abs(row[f"target_{name}"] - row[f"pred_{name}"]))

    rows_out.append(row)
    errors.append(mae)

    if (i + 1) % 500 == 0:
        print(f"  {i+1}/{n_total}  MAE: {np.mean(errors):.2f} cm")

# ── Kaydet ve ozet ────────────────────────────────────────────────────────────
df = pd.DataFrame(rows_out)
df.to_csv(OUT_CSV, index=False, encoding="utf-8")

print(f"\n=== INVERSION SONUCU ===")
print(f"Toplam: {len(df)} satir")
print(f"Ortalama olcum MAE: {np.mean(errors):.2f} cm  (max: {np.max(errors):.2f})")

print(f"\nSomatotype dagilimi:")
print(df.groupby(["gender","somatotype"]).size().unstack(fill_value=0).to_string())

print(f"\nOlcum MAE dagilimi:")
mae_ser = pd.Series(errors)
for p in [25, 50, 75, 90, 95]:
    print(f"  P{p}: {mae_ser.quantile(p/100):.2f} cm")

print(f"\nOran hatalari (ort. mutlak fark):")
for name, errs in ratio_errors.items():
    if errs:
        print(f"  {name:<20} {np.mean(errs):.4f}")

print(f"\nKaydedildi: {OUT_CSV}")

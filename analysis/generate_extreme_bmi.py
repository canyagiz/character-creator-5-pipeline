"""
generate_extreme_bmi.py
Underweight (BMI 13.5–18.4) ve Obese II+ (BMI 35–47) için
sentetik antropometrik ölçümler üretir.

Yöntem:
  1. ANSUR II'ye per-gender lineer regresyon fit et (weight + height → her ölçüm)
  2. Hedef BMI aralığından BMI örnekle, ANSUR yükseklik dağılımından height örnekle
  3. Regresyon ile ölçümleri tahmin et + ANSUR artık vektörlerini bootstrap örnekle
     (artık bootstrap: aynı weight/height için şekil varyasyonunu korur —
      elma vs armut obez, uzun bacaklı vs kısa bacaklı zayıf gibi kombinasyonlar)
  4. Biyolojik sınırlarla clip, fiziksel tutarlılık kontrolü
  5. Navy BFP hesapla

Çıktı: logs/ansur_extreme_bmi.csv  (ansur_samples_10k.csv ile aynı kolon formatı)
Çalıştır: python analysis/generate_extreme_bmi.py
"""

import pandas as pd
import numpy as np
import math
import os
from pathlib import Path
from sklearn.linear_model import LinearRegression

_ROOT = Path(__file__).resolve().parent.parent
ANSUR_CSV = str(_ROOT / "logs" / "ansur_samples_10k.csv")
OUT_CSV   = str(_ROOT / "logs" / "ansur_extreme_bmi.csv")
os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

MEAS_COLS = [
    "neck_circ_cm", "chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
    "mid_thigh_circ_cm", "calf_circ_cm", "bicep_circ_cm",
    "forearm_circ_cm", "wrist_circ_cm",
    "shoulder_width_cm", "hip_width_cm",
    "upper_arm_length_cm", "forearm_length_cm",
    "trochanterion_height_cm", "tibial_height_cm",
]

# (bmi_lo, bmi_hi, n_samples)
BMI_RANGES = {
    "underweight": {
        "female": (13.5, 18.4, 300),
        "male":   (13.5, 18.4, 150),
    },
    "obese2": {
        "female": (35.0, 47.0, 400),
        "male":   (35.0, 47.0, 300),
    },
}

# Biyolojik ölçüm sınırları (cm)
BOUNDS = {
    "neck_circ_cm":            (25.0,  58.0),
    "chest_circ_cm":           (63.0, 168.0),
    "waist_circ_cm":           (52.0, 170.0),
    "hip_circ_cm":             (68.0, 178.0),
    "mid_thigh_circ_cm":       (33.0,  98.0),
    "calf_circ_cm":            (24.0,  62.0),
    "bicep_circ_cm":           (18.0,  62.0),
    "forearm_circ_cm":         (17.0,  46.0),
    "wrist_circ_cm":           (12.5,  24.0),
    "shoulder_width_cm":       (30.0,  67.0),
    "hip_width_cm":            (24.0,  57.0),
    "upper_arm_length_cm":     (24.0,  46.0),
    "forearm_length_cm":       (17.0,  35.0),
    "trochanterion_height_cm": (68.0, 112.0),
    "tibial_height_cm":        (33.0,  62.0),
}

ID_PREFIXES = {
    ("underweight", "female"): "bmi_lo_f",
    ("underweight", "male"):   "bmi_lo_m",
    ("obese2",      "female"): "bmi_hi_f",
    ("obese2",      "male"):   "bmi_hi_m",
}


def navy_bfp(gender, waist_cm, hip_cm, neck_cm, height_cm):
    CM2IN = 1 / 2.54
    h = height_cm * CM2IN
    w = waist_cm  * CM2IN
    n = neck_cm   * CM2IN
    if gender == "female":
        val = (163.205 * math.log10(w + hip_cm * CM2IN - n)
               - 97.684 * math.log10(h) - 78.387)
    else:
        val = (86.010 * math.log10(max(w - n, 0.01))
               - 70.041 * math.log10(h) + 36.76)
    return round(max(2.0, min(70.0, val)), 2)


def fit_models(df_gender):
    """
    Her ölçüm için weight_kg + height_cm üzerine lineer regresyon fit et.
    Dönüş: model dict + artık array (n_samples x n_meas).
    """
    X = df_gender[["weight_kg", "height_cm"]].values
    models   = {}
    residuals = np.zeros((len(df_gender), len(MEAS_COLS)))
    for j, col in enumerate(MEAS_COLS):
        y = df_gender[col].values
        reg = LinearRegression().fit(X, y)
        models[col]      = reg
        residuals[:, j]  = y - reg.predict(X)
    return models, residuals


def generate_group(df_ansur, gender, category, bmi_lo, bmi_hi, n, rng):
    """Tek bir (gender, category) grubu için sentetik satırlar üret."""
    df_g = df_ansur[df_ansur["gender"] == gender].copy()
    models, residuals = fit_models(df_g)

    heights = df_g["height_cm"].values

    rows = []
    attempts = 0
    max_attempts = n * 8

    while len(rows) < n and attempts < max_attempts:
        attempts += 1

        # 1. Boy: ANSUR dağılımından bootstrap
        h = float(rng.choice(heights))

        # 2. BMI: hedef aralıktan uniform (küçük jitter ile)
        bmi = rng.uniform(bmi_lo, bmi_hi)

        # 3. Ağırlık
        w = bmi * (h / 100) ** 2

        # 4. Regresyon tahmini
        X_new = np.array([[w, h]])
        pred = {col: float(models[col].predict(X_new)[0]) for col in MEAS_COLS}

        # 5. Artık bootstrap: ANSUR'dan rastgele bir artık vektörü örnekle
        #    → aynı weight/height'taki iki kişi farklı şekil gösterir
        res_idx = int(rng.integers(0, len(residuals)))
        for j, col in enumerate(MEAS_COLS):
            pred[col] += residuals[res_idx, j]

        # 6. Biyolojik sınırlar
        for col in MEAS_COLS:
            lo, hi = BOUNDS[col]
            pred[col] = round(float(np.clip(pred[col], lo, hi)), 2)

        # 7. Fiziksel tutarlılık: waist <= hip, bel/boyun oranı mantıklı
        if pred["waist_circ_cm"] > pred["hip_circ_cm"] * 1.20:
            continue  # aşırı elma şekli, reddedildi
        if pred["neck_circ_cm"] > pred["chest_circ_cm"] * 0.65:
            continue
        if pred["tibial_height_cm"] >= pred["trochanterion_height_cm"]:
            continue  # alt bacak üst bacaktan uzun olamaz

        # 8. BMI kontrolü (artık ekledikten sonra hâlâ kabul edilebilir mi?)
        pred_bmi = w / (h / 100) ** 2
        if category == "underweight" and pred_bmi > 19.5:
            continue
        if category == "obese2" and pred_bmi < 33.0:
            continue

        bfp = navy_bfp(
            gender,
            waist_cm  = pred["waist_circ_cm"],
            hip_cm    = pred["hip_circ_cm"],
            neck_cm   = pred["neck_circ_cm"],
            height_cm = h,
        )

        row = {
            "height_cm": round(h, 1),
            "weight_kg": round(w, 1),
            "gender":    gender,
            "navy_bfp":  bfp,
        }
        row.update(pred)
        rows.append(row)

    if len(rows) < n:
        print(f"  UYARI: {gender} {category} → {len(rows)}/{n} üretildi "
              f"({attempts} deneme)")
    return rows


# ── Ana akış ──────────────────────────────────────────────────────────────────
rng = np.random.default_rng(seed=2025)

print("ANSUR II yükleniyor...")
df_ansur = pd.read_csv(ANSUR_CSV)
df_ansur["BMI"] = df_ansur["weight_kg"] / (df_ansur["height_cm"] / 100) ** 2
print(f"  {len(df_ansur)} satır | "
      f"Female: {(df_ansur.gender=='female').sum()} | "
      f"Male: {(df_ansur.gender=='male').sum()}")

all_rows = []
id_counters = {}

for category, gender_cfg in BMI_RANGES.items():
    for gender, (bmi_lo, bmi_hi, n) in gender_cfg.items():
        prefix = ID_PREFIXES[(category, gender)]
        print(f"\n{category.upper()} | {gender} | BMI {bmi_lo}–{bmi_hi} | hedef: {n}")
        rows = generate_group(df_ansur, gender, category, bmi_lo, bmi_hi, n, rng)
        for i, row in enumerate(rows):
            row["char_id"] = f"{prefix}_{i:04d}"
        print(f"  Üretildi: {len(rows)}")
        all_rows.extend(rows)

# ── Kolon sırası ansur_samples_10k.csv ile aynı ──────────────────────────────
COL_ORDER = (
    ["char_id", "height_cm"]
    + MEAS_COLS
    + ["trochanterion_height_cm", "tibial_height_cm", "weight_kg", "gender", "navy_bfp"]
)
# trochanterion ve tibial zaten MEAS_COLS içinde, duplikasyonu önle
seen = set()
final_cols = []
for c in COL_ORDER:
    if c not in seen:
        final_cols.append(c)
        seen.add(c)

df_out = pd.DataFrame(all_rows)
# Eksik kolon varsa 0 ile doldur
for c in final_cols:
    if c not in df_out.columns:
        df_out[c] = 0.0
df_out = df_out[final_cols]

df_out.to_csv(OUT_CSV, index=False, encoding="utf-8")

# ── Özet ─────────────────────────────────────────────────────────────────────
print(f"\n=== SONUÇ ===")
print(f"Toplam üretilen: {len(df_out)} satır")
df_out["BMI"] = df_out["weight_kg"] / (df_out["height_cm"] / 100) ** 2

for gender in ["female", "male"]:
    g = df_out[df_out.gender == gender]
    print(f"\n{gender.upper()} (n={len(g)}):")
    print(f"  BMI  : {g.BMI.min():.1f} – {g.BMI.max():.1f}  (ort: {g.BMI.mean():.1f})")
    print(f"  waist: {g.waist_circ_cm.min():.0f} – {g.waist_circ_cm.max():.0f} cm")
    print(f"  hip  : {g.hip_circ_cm.min():.0f} – {g.hip_circ_cm.max():.0f} cm")
    print(f"  bicep: {g.bicep_circ_cm.min():.0f} – {g.bicep_circ_cm.max():.0f} cm")
    print(f"  thigh: {g.mid_thigh_circ_cm.min():.0f} – {g.mid_thigh_circ_cm.max():.0f} cm")

print(f"\nKaydedildi: {OUT_CSV}")
print("\nSonraki adım:")
print("  1. Bu dosyayı morph_inversion.py'ye yönlendir (ANSUR_CSV değişkenini güncelle)")
print("     ya da mevcut dataset ile birleştir:")
print("     pd.concat([ansur_samples, extreme_bmi]).to_csv('logs/combined_samples.csv')")
print("  2. morph_inversion.py calistir -> logs/dataset_inverted_extreme.csv")
print("  3. batch_export.py ile FBX uret")

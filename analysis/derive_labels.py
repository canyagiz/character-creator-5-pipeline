"""
derive_labels.py — Kalibrasyon verisinden ogrenilmis modeli kullanarak
tum dataset icin gercek cm tahmini uretir ve somatotip labellarini yeniden atar.

Calistir: python analysis/derive_labels.py

Cikti:
  dataset.csv            — somatotype kolonu guncellenir
  analysis/dataset_with_preds.csv  — tahmin edilen cm degerleri de eklenir
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score

CALIB_CSV   = r"C:\Users\aliya\workspace\cc5-scripts\analysis\calib_merged.csv"
DATASET_CSV = r"C:\Users\aliya\workspace\cc5-scripts\dataset.csv"
OUT_PREDS   = r"C:\Users\aliya\workspace\cc5-scripts\analysis\dataset_with_preds.csv"

FEATURES = ["fat_score", "muscle_score", "hip_score", "waist_def_score", "height_score"]
TARGETS  = ["chest_circ_cm", "waist_circ_cm", "hip_circ_cm"]

# ── Model fit ─────────────────────────────────────────────────────────────────
calib = pd.read_csv(CALIB_CSV)
df    = pd.read_csv(DATASET_CSV)

models = {}
print("=== Model fit ===")
for gender in ["male", "female"]:
    sub = calib[calib["gender"] == gender]
    Xg  = sub[FEATURES].values
    models[gender] = {}
    for t in TARGETS:
        y = sub[t].values
        m = make_pipeline(PolynomialFeatures(degree=2, include_bias=False), Ridge(alpha=1.0))
        m.fit(Xg, y)
        r2 = r2_score(y, m.predict(Xg))
        models[gender][t] = m
        print(f"  {gender:<7} {t:<20} R2={r2:.3f}")

# ── Tum dataset icin tahmin ───────────────────────────────────────────────────
print("\n=== 30K tahmin uretiliyor ===")
for t in TARGETS:
    col = t.replace("_cm", "_pred_cm")
    df[col] = np.nan
    for gender in ["male", "female"]:
        mask = df["gender"] == gender
        X = df.loc[mask, FEATURES].values
        df.loc[mask, col] = models[gender][t].predict(X)

# Makul araliga clip et
df["chest_circ_pred_cm"] = df["chest_circ_pred_cm"].clip(60, 180)
df["waist_circ_pred_cm"] = df["waist_circ_pred_cm"].clip(50, 200)
df["hip_circ_pred_cm"]   = df["hip_circ_pred_cm"].clip(60, 200)

# ── Somatotip siniflandirma (gercek cm uzerinde) ──────────────────────────────
# Oranlar
df["_hip_chest"] = df["hip_circ_pred_cm"] / df["chest_circ_pred_cm"]
df["_wst_chest"] = df["waist_circ_pred_cm"] / df["chest_circ_pred_cm"]
df["_wst_hip"]   = df["waist_circ_pred_cm"] / df["hip_circ_pred_cm"]
df["_ch_diff"]   = (df["chest_circ_pred_cm"] - df["hip_circ_pred_cm"]).abs() / df[["chest_circ_pred_cm","hip_circ_pred_cm"]].max(axis=1)

def classify(row):
    wh         = row["_wst_hip"]      # waist / hip        — R2=0.99, guvenilir
    hip_score  = row["hip_score"]     # CC5 slider         — kaynak gercek
    waist_def  = row["waist_def_score"]
    fat        = row["fat_score"]

    # Apple: bel kalcaya yakin — fat baskisi yuksek (R2=0.99 ile guvenilir)
    if wh >= 0.90:
        return "apple"

    # V-Shape: dar kalca + dusuk fat + erkek (anatomik v-shape kadinlarda nadiren olusur)
    # Kadinlarda sadece cok yuksek muscle + cok dar kalca kombinasyonunda
    is_male = row["gender"] == "male"
    muscle  = row["muscle_score"]
    if hip_score < 0.45 and fat < 0.25 and (is_male or muscle > 0.60):
        return "v_shape"

    # Hourglass: orta kalca (gogus~kalca) + dar bel
    # Ust sinir 0.57: pear esigi 0.58 ile kesismiyor, iki kural mutually exclusive
    if 0.48 <= hip_score <= 0.57 and waist_def >= 0.70 and wh < 0.83:
        return "hourglass"

    # Pear: genis kalca + bel dar + dusuk kas
    # Yuksek muscle gogsü büyütür, hip avantajini ezer — pear görsel olarak kaybolur
    if hip_score >= 0.58 and wh < 0.89 and muscle < 0.65:
        return "pear"

    return "rectangle"

df["somatotype"] = df.apply(classify, axis=1)

# ── Sonuc ─────────────────────────────────────────────────────────────────────
print("\n=== Yeni somatotip dagilimi ===")
print(df["somatotype"].value_counts())
print()
print(df.groupby(["gender", "somatotype"]).size().unstack(fill_value=0))

# Tahmin edilen cm degerleri ozet
print("\n=== Tahmin edilen cm degerleri ===")
for g in ["male", "female"]:
    sub = df[df["gender"] == g]
    print(f"\n{g}:")
    for col in ["chest_circ_pred_cm", "waist_circ_pred_cm", "hip_circ_pred_cm"]:
        print(f"  {col:<25} [{sub[col].min():.1f}, {sub[col].max():.1f}]  mean={sub[col].mean():.1f}")

# dataset.csv guncelle — sadece somatotype kolonu
original = pd.read_csv(DATASET_CSV)
original["somatotype"] = df["somatotype"].values
original.to_csv(DATASET_CSV, index=False)
print(f"\ndataset.csv guncellendi: {DATASET_CSV}")

# Tahminli versiyon ayri kaydet
pred_cols = ["char_id", "gender", "group", "fat_score", "muscle_score",
             "hip_score", "waist_def_score", "height_score",
             "chest_circ_pred_cm", "waist_circ_pred_cm", "hip_circ_pred_cm",
             "_hip_chest", "_wst_chest", "_wst_hip", "somatotype"]
df[pred_cols].to_csv(OUT_PREDS, index=False)
print(f"Tahminli versiyon kaydedildi: {OUT_PREDS}")

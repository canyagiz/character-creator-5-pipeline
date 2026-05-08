"""
fit_circ_model.py — Kalibrasyon meta JSON'larindan slider -> olcum modeli kurar.

Calistir: python analysis/fit_circ_model.py
Gereksinim: scikit-learn, pandas, numpy

Cikti:
  analysis/calib_merged.csv   — probe CSV + olcumler birlestirme
  analysis/calib_report.txt   — model katsayilari + R2 skorlari
"""

import os, json, re
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

PROBE_CSV  = str(_ROOT / "analysis" / "calibration_probe.csv")
META_DIR   = str(_ROOT / "renders" / "meta")
OUT_CSV    = str(_ROOT / "analysis" / "calib_merged.csv")
OUT_REPORT = str(_ROOT / "analysis" / "calib_report.txt")

# ── Meta JSON'lari yukle ───────────────────────────────────────────────────────
probe = pd.read_csv(PROBE_CSV)

meta_rows = []
for fname in os.listdir(META_DIR):
    if not fname.endswith("_meta.json"):
        continue
    char_id = fname.replace("_meta.json", "")
    with open(os.path.join(META_DIR, fname), encoding="utf-8") as f:
        d = json.load(f)
    d["char_id"] = char_id
    meta_rows.append(d)

meta = pd.DataFrame(meta_rows)
print(f"Probe: {len(probe)} satir | Meta JSON: {len(meta)} satir")

merged = probe.merge(meta, on="char_id", how="inner")
print(f"Eslesen: {len(merged)} satir")

if len(merged) == 0:
    print("Hic eslesen satir yok — meta JSON'lar henuz olusturulmamis olabilir.")
    exit()

merged.to_csv(OUT_CSV, index=False)
print(f"Birlestirme kaydedildi: {OUT_CSV}")

# ── Ozellikler ────────────────────────────────────────────────────────────────
FEATURES = ["fat_score", "muscle_score", "hip_score", "waist_def_score", "height_score"]
TARGETS  = ["chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
            "mid_thigh_circ_cm", "bicep_circ_cm", "neck_circ_cm"]

# gender dummy
merged["is_female"] = (merged["gender"] == "female").astype(float)
feat_cols = FEATURES + ["is_female"]

X = merged[feat_cols].values
lines = []

for gender in ["male", "female"]:
    sub = merged[merged["gender"] == gender]
    Xg  = sub[FEATURES].values

    lines.append(f"\n{'='*60}")
    lines.append(f"GENDER: {gender.upper()}  (n={len(sub)})")
    lines.append(f"{'='*60}")

    for target in TARGETS:
        if target not in sub.columns:
            continue
        y = sub[target].values
        if np.isnan(y).any():
            continue

        model = make_pipeline(PolynomialFeatures(degree=2, include_bias=False), Ridge(alpha=1.0))
        model.fit(Xg, y)
        y_pred = model.predict(Xg)
        r2 = r2_score(y, y_pred)

        # Lineer katsayilari poly'nin ilk n_features terimi
        coef = model.named_steps["ridge"].coef_
        feat_names = model.named_steps["polynomialfeatures"].get_feature_names_out(FEATURES)

        lines.append(f"\n  {target}  (R2={r2:.3f})")
        # Sadece anlamli terimler (|coef| > 0.5 cm)
        for fn, c in sorted(zip(feat_names, coef), key=lambda x: -abs(x[1])):
            if abs(c) < 0.5:
                break
            lines.append(f"    {fn:<40s}  {c:+.2f} cm")

    # ── Olcum bazli somatotip esikleri onerisi ─────────────────────────────────
    lines.append(f"\n  -- Gercek olcum dagilimi ({gender}) --")
    if all(c in sub.columns for c in ["chest_circ_cm", "waist_circ_cm", "hip_circ_cm"]):
        sub2 = sub.copy()
        sub2["hip_chest_ratio"] = sub2["hip_circ_cm"] / sub2["chest_circ_cm"]
        sub2["waist_chest_pct"] = sub2["waist_circ_cm"] / sub2["chest_circ_cm"]
        sub2["waist_hip_pct"]   = sub2["waist_circ_cm"] / sub2["hip_circ_cm"]

        for soma in ["hourglass", "pear", "apple", "v_shape", "rectangle"]:
            ss = sub2[sub2["somatotype"] == soma]
            if len(ss) < 3:
                continue
            lines.append(f"    {soma:<12} n={len(ss):>3} | "
                         f"hip/chest={ss['hip_chest_ratio'].mean():.3f}±{ss['hip_chest_ratio'].std():.3f}  "
                         f"waist/chest={ss['waist_chest_pct'].mean():.3f}±{ss['waist_chest_pct'].std():.3f}  "
                         f"waist/hip={ss['waist_hip_pct'].mean():.3f}±{ss['waist_hip_pct'].std():.3f}")

report = "\n".join(lines)
print(report)
with open(OUT_REPORT, "w", encoding="utf-8") as f:
    f.write(report)
print(f"\nRapor kaydedildi: {OUT_REPORT}")

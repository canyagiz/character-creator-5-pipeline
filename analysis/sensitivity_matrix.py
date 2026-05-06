"""
sensitivity_matrix.py
Sensitivity probe sonuçlarından:
  1. Her slider'in her ölçüme etkisini grafik olarak gösterir
  2. Sensitivity matrix (delta cm / delta slider) çıkarır
  3. shoulder_width'in neden sabit kaldığını diagnose eder

Calistir: python analysis/sensitivity_matrix.py
Cikti:    analysis/sensitivity_plots/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

IN_CSV  = r"C:\Users\aliya\workspace\cc5-scripts\logs\sensitivity_measurements.csv"
OUT_DIR = r"C:\Users\aliya\workspace\cc5-scripts\analysis\sensitivity_plots"
os.makedirs(OUT_DIR, exist_ok=True)

df = pd.read_csv(IN_CSV)
print(f"Yuklendi: {len(df)} satir")
print(df.head())

SLIDERS = ["fat_score", "muscle_score", "hip_score", "waist_def_score"]
MEASUREMENTS = [
    "shoulder_width_cm", "hip_width_cm",
    "chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
    "bicep_circ_cm", "mid_thigh_circ_cm", "height_cm",
]
COLORS = {"female": "#e05a8a", "male": "#4a90d9"}

# ── 1. Her slider için: ölçüm vs slider değeri grafikleri ────────────────────
for slider in SLIDERS:
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    fig.suptitle(f"Slider: {slider}  (diğerleri = baseline)", fontsize=14, fontweight="bold")

    for ax, meas in zip(axes.flat, MEASUREMENTS):
        for gender, grp in df.groupby("gender"):
            # Bu slider'ı tararken diğerleri 0 olan satırlar
            other_sliders = [s for s in SLIDERS if s != slider]
            mask = grp.apply(
                lambda r: all(r[s] == 0.0 for s in other_sliders), axis=1
            )
            sub = grp[mask].sort_values(slider)
            if sub.empty:
                continue
            ax.plot(sub[slider], sub[meas],
                    marker="o", label=gender, color=COLORS[gender], linewidth=2)

        ax.set_title(meas, fontsize=9)
        ax.set_xlabel(slider)
        ax.set_ylabel("cm")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUT_DIR, f"slider_{slider}.png")
    plt.savefig(path, dpi=130)
    plt.close()
    print(f"  Kaydedildi: {path}")

# ── 2. Sensitivity matrix: Δmeasurement / Δslider (0→1 toplam değişim) ──────
print("\n=== SENSITIVITY MATRIX (cm / full slider range) ===")
matrix = {}

for slider in SLIDERS:
    matrix[slider] = {}
    other_sliders = [s for s in SLIDERS if s != slider]

    for meas in MEASUREMENTS:
        deltas = []
        for gender, grp in df.groupby("gender"):
            mask = grp.apply(
                lambda r: all(r[s] == 0.0 for s in other_sliders), axis=1
            )
            sub = grp[mask].sort_values(slider)
            if len(sub) < 2:
                continue
            lo = sub[meas].iloc[0]
            hi = sub[meas].iloc[-1]
            if pd.notna(lo) and pd.notna(hi):
                deltas.append(hi - lo)
        matrix[slider][meas] = round(np.mean(deltas), 2) if deltas else 0.0

mat_df = pd.DataFrame(matrix).T   # rows=sliders, cols=measurements
print(mat_df.to_string())

# Matrix heatmap
fig, ax = plt.subplots(figsize=(12, 4))
im = ax.imshow(mat_df.values, cmap="RdYlGn", aspect="auto")
ax.set_xticks(range(len(mat_df.columns)))
ax.set_xticklabels(mat_df.columns, rotation=30, ha="right", fontsize=9)
ax.set_yticks(range(len(mat_df.index)))
ax.set_yticklabels(mat_df.index)
for i in range(len(mat_df.index)):
    for j in range(len(mat_df.columns)):
        v = mat_df.values[i, j]
        ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=8,
                color="black" if abs(v) < 20 else "white")
plt.colorbar(im, ax=ax, label="Δcm (0→1 slider)")
ax.set_title("Sensitivity Matrix: Her slider 0→1 gittiğinde ölçüm kaç cm değişiyor?")
plt.tight_layout()
path = os.path.join(OUT_DIR, "sensitivity_matrix.png")
plt.savefig(path, dpi=130)
plt.close()
print(f"\nMatrix heatmap: {path}")

# ── 3. Shoulder diagnosis ─────────────────────────────────────────────────────
print("\n=== SHOULDER WIDTH DIAGNOSIS ===")
print(f"shoulder_width_cm range: {df['shoulder_width_cm'].min():.1f} – {df['shoulder_width_cm'].max():.1f} cm")
print(f"shoulder_width_cm std:   {df['shoulder_width_cm'].std():.2f} cm")
print()
for slider in SLIDERS:
    other_sliders = [s for s in SLIDERS if s != slider]
    sub = df[df.apply(lambda r: all(r[s] == 0.0 for s in other_sliders), axis=1)]
    sub = sub.sort_values(slider)
    if sub.empty:
        continue
    lo = sub["shoulder_width_cm"].min()
    hi = sub["shoulder_width_cm"].max()
    print(f"  {slider:20s}: {lo:.2f} → {hi:.2f} cm  (delta={hi-lo:.2f})")

"""
sensitivity_matrix.py
Sensitivity probe sonuclarindan Jacobian matrisi cikarir.

Cikti:
  logs/jacobian.csv                 -- 53 morph x 10 olcum, her hucre: cm/birim
  analysis/sensitivity_plots/       -- heatmap + per-morph grafikleri

Calistir: python analysis/sensitivity_matrix.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

IN_CSV        = r"C:\Users\aliya\workspace\cc5-scripts\logs\sensitivity_measurements.csv"
HEIGHT_CSV    = r"C:\Users\aliya\workspace\cc5-scripts\logs\height_sensitivity_measurements.csv"
OUT_DIR       = r"C:\Users\aliya\workspace\cc5-scripts\analysis\sensitivity_plots"
JAC_CSV       = r"C:\Users\aliya\workspace\cc5-scripts\logs\jacobian.csv"
os.makedirs(OUT_DIR, exist_ok=True)

MEASUREMENTS = [
    "height_cm", "shoulder_width_cm", "hip_width_cm",
    "chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
    "neck_circ_cm", "bicep_circ_cm", "forearm_circ_cm", "mid_thigh_circ_cm", "calf_circ_cm",
    "upper_arm_length_cm", "forearm_length_cm",
    "upper_leg_length_cm", "lower_leg_length_cm",
]

# Height probe'daki morphlar için 0.1 adım daha ince örnekleme sağlar.
# Her iki CSV'yi birleştir; polyfit tüm noktaları kullanır.
HEIGHT_MORPHS = {"thigh_len", "lower_leg_len", "hip_len", "chest_height", "neck_len",
                 "upperarm_len", "forearm_len"}

df_main = pd.read_csv(IN_CSV)
frames  = [df_main]
if os.path.exists(HEIGHT_CSV):
    df_h = pd.read_csv(HEIGHT_CSV)
    # Main probe'da zaten olan height morphlarının kaba verisini kaldır,
    # yerine 0.1 adımlı height probe verisini kullan.
    df_main = df_main[~df_main["morph_key"].isin(HEIGHT_MORPHS)]
    frames  = [df_main, df_h]
    print(f"Height probe yuklendi: {len(df_h)} satir")

df = pd.concat(frames, ignore_index=True)
print(f"Yuklendi: {len(df)} satir, {df['morph_key'].nunique()} morph")

# Baseline
baseline = {}
for gender in ["female", "male"]:
    b = df[(df.morph_key == "baseline") & (df.gender == gender)]
    if b.empty:
        b = df[(df.morph_value == 0.0) & (df.gender == gender)].head(1)
    baseline[gender] = b[MEASUREMENTS].iloc[0].to_dict()

print(f"\nBaseline female: height={baseline['female']['height_cm']}, shoulder={baseline['female']['shoulder_width_cm']}")
print(f"Baseline male:   height={baseline['male']['height_cm']}, shoulder={baseline['male']['shoulder_width_cm']}")

# Jacobian: her morph icin lineer regresyon egimi x tam aralik
morphs = sorted([m for m in df["morph_key"].unique() if m != "baseline"])
jac_rows = []

for morph in morphs:
    sub = df[df["morph_key"] == morph].copy()
    row = {"morph_key": morph}

    for meas in MEASUREMENTS:
        deltas = []
        for gender in ["female", "male"]:
            g = sub[sub.gender == gender].dropna(subset=[meas]).sort_values("morph_value")
            if len(g) < 2:
                continue
            x = g["morph_value"].values
            y = g[meas].values
            if x.max() - x.min() < 1e-6:
                continue
            slope = np.polyfit(x, y, 1)[0]
            total_delta = slope * (x.max() - x.min())
            deltas.append(total_delta)

        row[meas] = round(np.mean(deltas), 3) if deltas else 0.0

    jac_rows.append(row)

jac_df = pd.DataFrame(jac_rows).set_index("morph_key")
jac_df.to_csv(JAC_CSV)
print(f"\nJacobian kaydedildi: {JAC_CSV}")

# Konsol ozeti
print("\n=== JACOBIAN MATRISI (cm / tam aralik degisimi) ===")
print(f"{'Morph':<22}", end="")
for m in MEASUREMENTS:
    short = m.replace("_cm","").replace("_circ","").replace("mid_","")
    print(f"{short:>9}", end="")
print()
print("-" * (22 + 9*len(MEASUREMENTS)))

for morph, row in jac_df.iterrows():
    print(f"{morph:<22}", end="")
    for m in MEASUREMENTS:
        v = row[m]
        marker = "*" if abs(v) > 3 else " "
        print(f"{v:>8.1f}{marker}", end="")
    print()

# Shoulder width ozeli
print("\n=== SHOULDER WIDTH ANALIZI ===")
sh_col = jac_df["shoulder_width_cm"].sort_values(ascending=False)
print("En cok etkileyen morphlar (shoulder_width_cm delta cm):")
for morph, val in sh_col.head(10).items():
    bar = "+" * max(0, int(abs(val)*2))
    print(f"  {morph:<25} {val:+6.2f} cm  {bar}")

# Heatmap
fig, ax = plt.subplots(figsize=(14, 16))
data = jac_df[MEASUREMENTS].values
vmax = max(np.percentile(np.abs(data), 95), 1.0)

im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=-vmax, vmax=vmax)

col_labels = [m.replace("_cm","").replace("_circ","").replace("mid_","") for m in MEASUREMENTS]
ax.set_xticks(range(len(MEASUREMENTS)))
ax.set_xticklabels(col_labels, rotation=30, ha="right", fontsize=9)
ax.set_yticks(range(len(morphs)))
ax.set_yticklabels(morphs, fontsize=8)

for i in range(len(morphs)):
    for j in range(len(MEASUREMENTS)):
        v = data[i, j]
        if abs(v) > 0.3:
            ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=6,
                    color="black" if abs(v) < vmax*0.6 else "white")

plt.colorbar(im, ax=ax, label="Delta cm (tam aralik)")
ax.set_title("Sensitivity Matrix: Her morph tam araligindan gecince olcum kac cm degisiyor?",
             fontsize=11, fontweight="bold")
plt.tight_layout()
path = os.path.join(OUT_DIR, "sensitivity_matrix.png")
plt.savefig(path, dpi=130)
plt.close()
print(f"\nHeatmap: {path}")

# Key morph cizgi grafikleri
KEY_MORPHS = [
    "shoulder_scale", "musc_shoulder", "musc_back",
    "body_fat", "body_muscular", "hip_scale", "glute_scale",
    "abdomen_scale", "chest_scale", "thigh_scale",
]
COLORS = {"female": "#e05a8a", "male": "#4a90d9"}

fig, axes = plt.subplots(2, 5, figsize=(22, 9))
fig.suptitle("Secili Morphlarin Shoulder ve Hip Width Uzerindeki Etkisi", fontweight="bold")

for ax, morph in zip(axes.flat, KEY_MORPHS):
    sub = df[df.morph_key == morph]
    for gender, grp in sub.groupby("gender"):
        g = grp.sort_values("morph_value")
        ax.plot(g["morph_value"], g["shoulder_width_cm"],
                marker="o", markersize=3, label=f"{gender} shoulder",
                color=COLORS[gender], linewidth=2)
        ax.plot(g["morph_value"], g["hip_width_cm"],
                marker="s", markersize=3, linestyle="--",
                label=f"{gender} hip", color=COLORS[gender], alpha=0.5)
    ax.set_title(morph, fontsize=9)
    ax.set_xlabel("morph value")
    ax.set_ylabel("cm")
    ax.legend(fontsize=6)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
path = os.path.join(OUT_DIR, "key_morphs_shoulder_hip.png")
plt.savefig(path, dpi=130)
plt.close()
print(f"Key morph grafikleri: {path}")

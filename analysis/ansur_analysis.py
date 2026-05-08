"""
ansur_analysis.py
ANSUR II'den pipeline için kullanılacak üç şeyi çıkarır:
  1. Gerçekçi ölçüm aralıkları (P5–P95 bandı) — morph inversion için constraint
  2. Temel oranlar (WHR, SHR, vs.) — somatotype eşiklerini kalibrate etmek için
  3. Korelasyon yapısı — hangi ölçümler birlikte hareket ediyor

Çıktılar:
  logs/ansur_ranges.csv       — cinsiyet × ölçüm → P5/P25/P50/P75/P95
  logs/ansur_ratios.csv       — her satır için oranlar + bunların dağılımı
  logs/ansur_correlations.csv — ölçümler arası Pearson r matrisi
  analysis/ansur_plots/       — görselleştirmeler

Çalıştır: python analysis/ansur_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

ANSUR_CSV = r"C:\Users\aliya\workspace\cc5-scripts\logs\ansur_samples_10k.csv"
OUT_DIR   = r"C:\Users\aliya\workspace\cc5-scripts\analysis\ansur_plots"
LOG_DIR   = r"C:\Users\aliya\workspace\cc5-scripts\logs"
os.makedirs(OUT_DIR, exist_ok=True)

MEAS_COLS = [
    "height_cm", "weight_kg",
    "neck_circ_cm", "chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
    "mid_thigh_circ_cm", "calf_circ_cm", "bicep_circ_cm",
    "forearm_circ_cm", "wrist_circ_cm",
    "shoulder_width_cm", "hip_width_cm",
    "upper_arm_length_cm", "forearm_length_cm",
]

df = pd.read_csv(ANSUR_CSV)
print(f"Yuklendi: {len(df)} satir ({df.gender.value_counts().to_dict()})")

# ── 1. Ölçüm aralıkları ────────────────────────────────────────────────────
percs = [5, 10, 25, 50, 75, 90, 95]
ranges_rows = []
for gender, grp in df.groupby("gender"):
    for col in MEAS_COLS:
        row = {"gender": gender, "measurement": col}
        for p in percs:
            row[f"P{p}"] = round(grp[col].quantile(p/100), 2)
        row["mean"] = round(grp[col].mean(), 2)
        row["std"]  = round(grp[col].std(), 2)
        ranges_rows.append(row)

df_ranges = pd.DataFrame(ranges_rows)
df_ranges.to_csv(os.path.join(LOG_DIR, "ansur_ranges.csv"), index=False)
print(f"\nAralik tablosu: {os.path.join(LOG_DIR, 'ansur_ranges.csv')}")

print("\n=== ÖLÇÜM ARALIKLARI (P5 – P95) ===")
print(f"{'Ölçüm':<25} {'Female P5':>10} {'Female P95':>11} {'Male P5':>9} {'Male P95':>10}")
print("-" * 68)
for col in MEAS_COLS:
    f_p5  = df_ranges[(df_ranges.gender=="female") & (df_ranges.measurement==col)]["P5"].values[0]
    f_p95 = df_ranges[(df_ranges.gender=="female") & (df_ranges.measurement==col)]["P95"].values[0]
    m_p5  = df_ranges[(df_ranges.gender=="male")   & (df_ranges.measurement==col)]["P5"].values[0]
    m_p95 = df_ranges[(df_ranges.gender=="male")   & (df_ranges.measurement==col)]["P95"].values[0]
    print(f"{col:<25} {f_p5:>10.1f} {f_p95:>11.1f} {m_p5:>9.1f} {m_p95:>10.1f}")

# ── 2. Oranlar ────────────────────────────────────────────────────────────
df["WHR"]  = (df["waist_circ_cm"]    / df["hip_circ_cm"]).round(3)
df["SHR"]  = (df["shoulder_width_cm"]/ df["hip_width_cm"]).round(3)   # omuz/kalça genişliği
df["CHR"]  = (df["chest_circ_cm"]    / df["hip_circ_cm"]).round(3)    # göğüs/kalça çevresi
df["WCR"]  = (df["waist_circ_cm"]    / df["chest_circ_cm"]).round(3)  # bel/göğüs
df["BMI"]  = (df["weight_kg"] / (df["height_cm"]/100)**2).round(1)

RATIO_COLS = ["WHR", "SHR", "CHR", "WCR", "BMI"]

ratio_rows = []
for gender, grp in df.groupby("gender"):
    for col in RATIO_COLS:
        row = {"gender": gender, "ratio": col}
        for p in percs:
            row[f"P{p}"] = round(grp[col].quantile(p/100), 3)
        row["mean"] = round(grp[col].mean(), 3)
        row["std"]  = round(grp[col].std(), 3)
        ratio_rows.append(row)

df_ratios = pd.DataFrame(ratio_rows)
df_ratios.to_csv(os.path.join(LOG_DIR, "ansur_ratios.csv"), index=False)

print("\n=== ORAN DAĞILIMLARI ===")
print(f"{'Oran':<6} {'Anlam':<30} {'F-P10':>7} {'F-P50':>7} {'F-P90':>7} {'M-P10':>7} {'M-P50':>7} {'M-P90':>7}")
print("-" * 75)
RATIO_LABELS = {
    "WHR": "waist / hip_circ",
    "SHR": "shoulder_w / hip_w",
    "CHR": "chest_circ / hip_circ",
    "WCR": "waist / chest",
    "BMI": "kg / m²",
}
for col in RATIO_COLS:
    fp10 = df_ratios[(df_ratios.gender=="female") & (df_ratios.ratio==col)]["P10"].values[0]
    fp50 = df_ratios[(df_ratios.gender=="female") & (df_ratios.ratio==col)]["P50"].values[0]
    fp90 = df_ratios[(df_ratios.gender=="female") & (df_ratios.ratio==col)]["P90"].values[0]
    mp10 = df_ratios[(df_ratios.gender=="male")   & (df_ratios.ratio==col)]["P10"].values[0]
    mp50 = df_ratios[(df_ratios.gender=="male")   & (df_ratios.ratio==col)]["P50"].values[0]
    mp90 = df_ratios[(df_ratios.gender=="male")   & (df_ratios.ratio==col)]["P90"].values[0]
    print(f"{col:<6} {RATIO_LABELS[col]:<30} {fp10:>7.3f} {fp50:>7.3f} {fp90:>7.3f} {mp10:>7.3f} {mp50:>7.3f} {mp90:>7.3f}")

# ── 3. Korelasyon matrisi ─────────────────────────────────────────────────
print("\n=== GÜÇLÜ KORELASYONLAR (|r| > 0.80, Female) ===")
corr_f = df[df.gender=="female"][MEAS_COLS].corr()
corr_m = df[df.gender=="male"][MEAS_COLS].corr()

for i in range(len(MEAS_COLS)):
    for j in range(i+1, len(MEAS_COLS)):
        r = corr_f.iloc[i,j]
        if abs(r) > 0.80:
            print(f"  {MEAS_COLS[i]:<25} <-> {MEAS_COLS[j]:<25}  r={r:.2f}")

corr_f.to_csv(os.path.join(LOG_DIR, "ansur_correlations_female.csv"))
corr_m.to_csv(os.path.join(LOG_DIR, "ansur_correlations_male.csv"))

# ── 4. Görselleştirmeler ──────────────────────────────────────────────────
COLORS = {"female": "#e05a8a", "male": "#4a90d9"}

# WHR ve SHR dağılımları — somatotype eşikleri buradan gelecek
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Oran Dağılımları — Somatotype Eşikleri için Referans", fontweight="bold")

for ax, ratio, title in zip(axes, ["WHR", "SHR"],
                             ["WHR (waist/hip) — apple/hourglass ayrımı",
                              "SHR (shoulder_w/hip_w) — v_shape ayrımı"]):
    for gender, grp in df.groupby("gender"):
        vals = grp[ratio].dropna()
        ax.hist(vals, bins=50, alpha=0.5, label=gender, color=COLORS[gender], density=True)
        # P10, P50, P90 çizgisi
        for p, ls in [(10,"--"),(50,"-"),(90,"--")]:
            v = vals.quantile(p/100)
            ax.axvline(v, color=COLORS[gender], linestyle=ls, linewidth=1, alpha=0.8)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel(ratio)
    ax.legend()
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "ratio_distributions.png"), dpi=130)
plt.close()

# Ölçüm box plot — cinsiyet karşılaştırması
fig, axes = plt.subplots(3, 5, figsize=(20, 12))
fig.suptitle("ANSUR II Ölçüm Dağılımları (gerçek insan aralıkları)", fontweight="bold")
for ax, col in zip(axes.flat, MEAS_COLS):
    data = [df[df.gender=="female"][col].dropna(), df[df.gender=="male"][col].dropna()]
    bp = ax.boxplot(data, labels=["F", "M"], patch_artist=True)
    bp["boxes"][0].set_facecolor("#e05a8a")
    bp["boxes"][1].set_facecolor("#4a90d9")
    ax.set_title(col, fontsize=8)
    ax.set_ylabel("cm", fontsize=7)
    ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "measurement_distributions.png"), dpi=130)
plt.close()

print(f"\nGörselleştirmeler: {OUT_DIR}")
print(f"Kaydedilen dosyalar:")
print(f"  logs/ansur_ranges.csv")
print(f"  logs/ansur_ratios.csv")
print(f"  logs/ansur_correlations_female.csv")
print(f"  logs/ansur_correlations_male.csv")
print(f"  analysis/ansur_plots/ratio_distributions.png")
print(f"  analysis/ansur_plots/measurement_distributions.png")

print("\n=== PIPELINE'DA NASIL KULLANILACAK ===")
print("1. ansur_ranges.csv → morph inversion hedeflerini P5-P95 bandına clip'le")
print("   Örnek: female waist_circ hedefi [61, 104] cm dışına çıkmasın")
print("2. ansur_ratios.csv → somatotype eşiklerini kalibrate et")
print("   Örnek: female WHR P50=0.84 → hourglass eşiği bu değerin altı")
print("3. ansur_correlations.csv → inversion'da tutarsız kombinasyonları filtrele")
print("   Örnek: hip_circ yüksekse thigh_circ da yüksek olmalı (r=0.94)")

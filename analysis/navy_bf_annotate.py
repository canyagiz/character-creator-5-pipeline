"""
ansur_samples_10k.csv'e navy_bfp kolonu ekler ve BF% dağılım histogramını gösterir.
Skinny ve muscular refinement alan aralıkları highlight eder.
"""

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

CSV_IN  = str(_ROOT / "logs" / "ansur_samples_10k.csv")
CSV_OUT = str(_ROOT / "logs" / "ansur_samples_10k.csv")

# ── US Navy BF% ──────────────────────────────────────────────────────────────
CM_TO_IN = 1 / 2.54

def navy_bfp(gender, waist_cm, hip_cm, neck_cm, height_cm):
    h = height_cm * CM_TO_IN
    w = waist_cm  * CM_TO_IN
    n = neck_cm   * CM_TO_IN
    if gender == "female":
        val = 163.205 * math.log10(w + hip_cm * CM_TO_IN - n) - 97.684 * math.log10(h) - 78.387
    else:
        val = 86.010 * math.log10(w - n) - 70.041 * math.log10(h) + 36.76
    return round(max(0.0, val), 2)

df = pd.read_csv(CSV_IN, encoding="utf-8")

df["navy_bfp"] = df.apply(
    lambda r: navy_bfp(r["gender"], r["waist_circ_cm"], r["hip_circ_cm"],
                       r["neck_circ_cm"], r["height_cm"]),
    axis=1,
)

df.to_csv(CSV_OUT, index=False, encoding="utf-8")
print(f"Kaydedildi: {CSV_OUT}")
print(f"Toplam: {len(df)} satir")

# ── Özet ─────────────────────────────────────────────────────────────────────
for g in ["female", "male"]:
    sub = df[df.gender == g]["navy_bfp"]
    print(f"\n{g.upper()} navy_bfp:")
    print(f"  mean={sub.mean():.1f}%  std={sub.std():.1f}%  "
          f"min={sub.min():.1f}%  max={sub.max():.1f}%")

# Refinement eşikleri
LEAN_HI   = {"female": 22.0, "male": 13.0}
MUSCLE_HI = {"female": 28.0, "male": 18.0}

for g in ["female", "male"]:
    sub = df[df.gender == g]
    n_skin   = (sub["navy_bfp"] < LEAN_HI[g]).sum()
    n_muscle = (sub["navy_bfp"] < MUSCLE_HI[g]).sum()
    print(f"\n{g}: skinny refinement (<{LEAN_HI[g]}%) = {n_skin}/{len(sub)} "
          f"({100*n_skin/len(sub):.1f}%)")
    print(f"{g}: muscle refinement (<{MUSCLE_HI[g]}%) = {n_muscle}/{len(sub)} "
          f"({100*n_muscle/len(sub):.1f}%)")

# ── Plot ─────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("ANSUR II — US Navy Body Fat % Distribution", fontsize=14, fontweight="bold")

BINS = np.arange(0, 55, 1.0)

for ax, g, color in zip(axes, ["female", "male"], ["#e07b9e", "#6baed6"]):
    sub = df[df.gender == g]["navy_bfp"]
    lean_thr   = LEAN_HI[g]
    muscle_thr = MUSCLE_HI[g]

    # Ana histogram
    counts, edges = np.histogram(sub, bins=BINS)
    bar_colors = []
    for left in edges[:-1]:
        if left < lean_thr:
            bar_colors.append("#e74c3c")       # skinny zone (kırmızı)
        elif left < muscle_thr:
            bar_colors.append("#f39c12")       # muscle-only zone (turuncu)
        else:
            bar_colors.append(color)           # normal

    ax.bar(edges[:-1], counts, width=1.0, color=bar_colors, edgecolor="none", alpha=0.85)

    # Eşik çizgileri
    ax.axvline(lean_thr,   color="#e74c3c", lw=2, linestyle="--",
               label=f"Skinny eşiği {lean_thr}%")
    ax.axvline(muscle_thr, color="#f39c12", lw=2, linestyle="--",
               label=f"Muscle eşiği {muscle_thr}%")

    # Arka plan bölgeleri
    ax.axvspan(0,          lean_thr,   alpha=0.08, color="#e74c3c")
    ax.axvspan(lean_thr,   muscle_thr, alpha=0.08, color="#f39c12")

    # İstatistik kutusu
    n_skin   = (sub < lean_thr).sum()
    n_muscle = (sub < muscle_thr).sum() - n_skin
    total    = len(sub)
    textstr  = (f"n={total}\nmean={sub.mean():.1f}%\nstd={sub.std():.1f}%\n\n"
                f"Skinny: {n_skin} ({100*n_skin/total:.1f}%)\n"
                f"Muscle zone: {n_muscle} ({100*n_muscle/total:.1f}%)")
    ax.text(0.97, 0.97, textstr, transform=ax.transAxes, fontsize=8.5,
            verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.8))

    ax.set_title(f"{g.capitalize()}", fontsize=12)
    ax.set_xlabel("Body Fat %")
    ax.set_ylabel("Kişi sayısı")
    ax.set_xlim(0, 52)

    patches = [
        mpatches.Patch(color="#e74c3c", alpha=0.7, label=f"Skinny refinement (<{lean_thr}%)"),
        mpatches.Patch(color="#f39c12", alpha=0.7, label=f"Muscle zone (<{muscle_thr}%)"),
        mpatches.Patch(color=color,     alpha=0.7, label="Normal"),
    ]
    ax.legend(handles=patches, fontsize=8, loc="upper left")

plt.tight_layout()
plt.savefig(str(_ROOT / "analysis" / "navy_bf_distribution.png"),
            dpi=150, bbox_inches="tight")
print("\nPlot kaydedildi: analysis/navy_bf_distribution.png")
plt.show()

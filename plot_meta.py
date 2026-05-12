"""
renders/meta/ altındaki *_meta.json dosyalarını okuyup
her sayısal key için dağılım grafiği üretir.
Çıktı: docs/plots/meta_<key>.png + docs/plots/meta_overview.png
"""

import json
from pathlib import Path
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

META_DIR = Path("renders/meta")
OUT_DIR  = Path("docs/plots")

# ── stil ────────────────────────────────────────────────────────────────────
sns.set_theme(style="darkgrid", palette="muted")
ACCENT   = "#4C9BE8"
STAT_CLR = {"mean": "#E8624C", "median": "#4CE8A0", "p5_p95": "#E8D44C"}
FIG_BG   = "#1A1A2E"
AX_BG    = "#16213E"
TEXT_CLR = "#E0E0E0"

plt.rcParams.update({
    "figure.facecolor":  FIG_BG,
    "axes.facecolor":    AX_BG,
    "axes.edgecolor":    "#3A3A5C",
    "axes.labelcolor":   TEXT_CLR,
    "axes.titlecolor":   TEXT_CLR,
    "xtick.color":       TEXT_CLR,
    "ytick.color":       TEXT_CLR,
    "grid.color":        "#2A2A4A",
    "text.color":        TEXT_CLR,
    "font.family":       "sans-serif",
    "font.size":         11,
})

# ── yardımcı ────────────────────────────────────────────────────────────────
LABELS = {
    "height_cm":           "Boy (cm)",
    "neck_circ_cm":        "Boyun çevresi (cm)",
    "chest_circ_cm":       "Göğüs çevresi (cm)",
    "waist_circ_cm":       "Bel çevresi (cm)",
    "hip_circ_cm":         "Kalça çevresi (cm)",
    "mid_thigh_circ_cm":   "Uyluk ortası çevresi (cm)",
    "calf_circ_cm":        "Baldır çevresi (cm)",
    "bicep_circ_cm":       "Bicep çevresi (cm)",
    "elbow_circ_cm":       "Dirsek çevresi (cm)",
    "forearm_circ_cm":     "Ön kol çevresi (cm)",
    "wrist_circ_cm":       "Bilek çevresi (cm)",
    "shoulder_width_cm":   "Omuz genişliği (cm)",
    "hip_width_cm":        "Kalça genişliği (cm)",
    "upper_arm_length_cm": "Üst kol uzunluğu (cm)",
    "forearm_length_cm":   "Ön kol uzunluğu (cm)",
    "total_arm_length_cm": "Toplam kol uzunluğu (cm)",
    "upper_leg_length_cm": "Üst bacak uzunluğu (cm)",
    "lower_leg_length_cm": "Alt bacak uzunluğu (cm)",
    "total_leg_length_cm": "Toplam bacak uzunluğu (cm)",
    "seg_foot_cm":         "Ayak segmenti (cm)",
    "seg_lower_leg_cm":    "Alt bacak segmenti (cm)",
    "seg_upper_leg_cm":    "Üst bacak segmenti (cm)",
    "seg_torso_cm":        "Gövde segmenti (cm)",
    "seg_neck_cm":         "Boyun segmenti (cm)",
    "seg_head_cm":         "Baş segmenti (cm)",
    "volume_L":            "Hacim (L)",
}


def stat_lines(ax, vals, ymax):
    mean   = np.mean(vals)
    median = np.median(vals)
    p5     = np.percentile(vals, 5)
    p95    = np.percentile(vals, 95)

    ax.axvline(mean,   color=STAT_CLR["mean"],   lw=1.8, ls="--",  label=f"Ort. {mean:.1f}")
    ax.axvline(median, color=STAT_CLR["median"], lw=1.8, ls="-.",  label=f"Med. {median:.1f}")
    ax.axvspan(p5, p95, alpha=0.10, color=STAT_CLR["p5_p95"],
               label=f"p5–p95 [{p5:.1f}–{p95:.1f}]")

    ax.legend(fontsize=9, framealpha=0.25, loc="upper right",
              labelcolor=TEXT_CLR, facecolor=AX_BG, edgecolor="#3A3A5C")


def single_plot(key, vals, out_path):
    fig, (ax_hist, ax_box) = plt.subplots(
        2, 1, figsize=(10, 6),
        gridspec_kw={"height_ratios": [4, 1], "hspace": 0.05},
        facecolor=FIG_BG,
    )

    label = LABELS.get(key, key)

    # histogram + KDE
    sns.histplot(vals, bins=40, color=ACCENT, alpha=0.75, kde=True, ax=ax_hist)
    ax_hist.lines[-1].set(linewidth=2, color="#7DC8F0")
    stat_lines(ax_hist, vals, ax_hist.get_ylim()[1])

    ax_hist.set_title(label, fontsize=14, fontweight="bold", pad=10)
    ax_hist.set_xlabel("")
    ax_hist.set_ylabel("Frekans", labelpad=8)
    ax_hist.tick_params(labelbottom=False)

    # box plot
    ax_box.set_facecolor(AX_BG)
    bp = ax_box.boxplot(
        vals, vert=False, patch_artist=True, widths=0.5,
        medianprops=dict(color=STAT_CLR["median"], linewidth=2),
        boxprops=dict(facecolor="#2A4A7A", edgecolor=ACCENT),
        whiskerprops=dict(color=ACCENT, linewidth=1.2),
        capprops=dict(color=ACCENT, linewidth=1.2),
        flierprops=dict(marker=".", color=ACCENT, alpha=0.3, markersize=4),
    )
    ax_box.set_yticks([])
    ax_box.set_xlabel(label, labelpad=8)
    ax_box.spines["left"].set_visible(False)

    fig.text(0.98, 0.02,
             f"n={len(vals):,}   std={np.std(vals):.2f}   "
             f"[{min(vals):.1f} – {max(vals):.1f}]",
             ha="right", va="bottom", fontsize=9, color="#888899")

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def overview_plot(data):
    keys = list(data.keys())
    n    = len(keys)
    cols = 4
    rows = (n + cols - 1) // cols

    fig = plt.figure(figsize=(cols * 5, rows * 3.5), facecolor=FIG_BG)
    fig.suptitle("Meta JSON — Tüm Değişkenler", fontsize=16,
                 fontweight="bold", color=TEXT_CLR, y=1.01)

    for i, key in enumerate(keys):
        ax = fig.add_subplot(rows, cols, i + 1)
        ax.set_facecolor(AX_BG)
        vals = data[key]

        sns.histplot(vals, bins=30, color=ACCENT, alpha=0.7, kde=True, ax=ax)
        if ax.lines:
            ax.lines[-1].set(linewidth=1.5, color="#7DC8F0")

        ax.axvline(np.mean(vals),   color=STAT_CLR["mean"],   lw=1.4, ls="--")
        ax.axvline(np.median(vals), color=STAT_CLR["median"], lw=1.4, ls="-.")

        ax.set_title(LABELS.get(key, key), fontsize=9, fontweight="bold")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(labelsize=7)

    fig.tight_layout()
    overview_path = OUT_DIR / "meta_overview.png"
    fig.savefig(overview_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  overview -> {overview_path}")


def correlation_heatmap(data):
    keys = list(data.keys())
    mat  = np.array([data[k] for k in keys]).T          # (n_samples, n_keys)
    # trim to common length
    min_len = min(len(data[k]) for k in keys)
    mat = np.array([data[k][:min_len] for k in keys]).T

    corr = np.corrcoef(mat.T)

    short = [LABELS.get(k, k).replace(" (cm)", "").replace(" (L)", "")
             for k in keys]

    fig, ax = plt.subplots(figsize=(14, 12), facecolor=FIG_BG)
    ax.set_facecolor(AX_BG)

    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr, mask=mask, annot=True, fmt=".2f", linewidths=0.3,
        cmap="coolwarm", center=0, vmin=-1, vmax=1,
        xticklabels=short, yticklabels=short,
        annot_kws={"size": 7},
        cbar_kws={"shrink": 0.7},
        ax=ax,
    )
    ax.set_title("Korelasyon Matrisi", fontsize=14, fontweight="bold", pad=12)
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.tick_params(axis="y", rotation=0,  labelsize=8)

    fig.tight_layout()
    path = OUT_DIR / "meta_correlation.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  correlation -> {path}")


# ── main ────────────────────────────────────────────────────────────────────
def main():
    json_files = sorted(META_DIR.glob("*_meta.json"))
    if not json_files:
        raise FileNotFoundError(f"Hiç meta.json bulunamadı: {META_DIR}")

    print(f"{len(json_files)} meta.json okunuyor...")
    data: dict[str, list] = defaultdict(list)
    for f in json_files:
        obj = json.loads(f.read_text(encoding="utf-8"))
        for k, v in obj.items():
            if isinstance(v, (int, float)):
                data[k].append(v)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Tek tek grafikler üretiliyor...")
    for key, vals in data.items():
        out = OUT_DIR / f"meta_{key}.png"
        single_plot(key, vals, out)
        print(f"  {key} -> {out}")

    print("Overview grafiği üretiliyor...")
    overview_plot(data)

    print("Korelasyon ısı haritası üretiliyor...")
    correlation_heatmap(data)

    print(f"\nTamamlandı. {len(data) + 2} grafik -> {OUT_DIR}/")


if __name__ == "__main__":
    main()

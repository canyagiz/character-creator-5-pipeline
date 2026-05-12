"""
Tum karakterler icin hip_circ / chest_circ oranini hesaplar,
histogram + ornekli bin analizi uretir ve
docs/hip_chest_ratio.md olarak yazar.
"""

import json
import math
import random
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from PIL import Image

# ── yollar ──────────────────────────────────────────────────────────────────
META_DIR  = Path("renders/meta")
DEBUG_DIR = Path("renders/debug")
OUT_MD    = Path("docs/hip_chest_ratio.md")
PLOTS_DIR = Path("docs/plots")
THUMB_DIR = PLOTS_DIR / "hip_chest_samples"

BINS        = 10
SAMPLES     = 5
THUMB_W     = 180
RANDOM_SEED = 42

# ── stil ────────────────────────────────────────────────────────────────────
FIG_BG  = "#1A1A2E"
AX_BG   = "#16213E"
ACCENT  = "#4C9BE8"
CLR_MEAN   = "#E8624C"
CLR_MEDIAN = "#4CE8A0"
CLR_REF    = "#E8D44C"
TEXT_CLR   = "#E0E0E0"

plt.rcParams.update({
    "figure.facecolor": FIG_BG, "axes.facecolor": AX_BG,
    "axes.edgecolor": "#3A3A5C", "axes.labelcolor": TEXT_CLR,
    "axes.titlecolor": TEXT_CLR, "xtick.color": TEXT_CLR,
    "ytick.color": TEXT_CLR, "grid.color": "#2A2A4A",
    "text.color": TEXT_CLR, "font.family": "sans-serif", "font.size": 11,
})

# ── yardimcilar ──────────────────────────────────────────────────────────────
def percentile(sv, p):
    idx = (len(sv) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(sv) - 1)
    return sv[lo] * (1 - (idx - lo)) + sv[hi] * (idx - lo)

def make_bins(sv):
    lo, hi = sv[0], sv[-1]
    step = (hi - lo) / BINS
    edges = [lo + step * i for i in range(BINS + 1)]
    edges[-1] = hi
    return [(edges[i], edges[i+1]) for i in range(BINS)]

def bin_index(val, bins):
    for i, (lo, hi) in enumerate(bins):
        if val <= hi:
            return i
    return len(bins) - 1

def save_thumb(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(src)
    ratio = THUMB_W / img.width
    img = img.resize((THUMB_W, int(img.height * ratio)), Image.LANCZOS)
    img.save(dst, optimize=True)

def img_tag(rel, alt="", w=THUMB_W):
    return f'<img src="{rel}" alt="{alt}" width="{w}">'

# ── plot ─────────────────────────────────────────────────────────────────────
def make_plot(ratios, out_path):
    sv = sorted(ratios)
    mean   = np.mean(sv)
    median = np.median(sv)
    p5, p95 = np.percentile(sv, 5), np.percentile(sv, 95)

    fig, (ax_hist, ax_box) = plt.subplots(
        2, 1, figsize=(11, 6),
        gridspec_kw={"height_ratios": [4, 1], "hspace": 0.05},
        facecolor=FIG_BG,
    )

    sns.histplot(sv, bins=50, color=ACCENT, alpha=0.75, kde=True, ax=ax_hist)
    if ax_hist.lines:
        ax_hist.lines[-1].set(linewidth=2, color="#7DC8F0")

    ax_hist.axvline(mean,   color=CLR_MEAN,   lw=1.8, ls="--", label=f"Ort. {mean:.3f}")
    ax_hist.axvline(median, color=CLR_MEDIAN, lw=1.8, ls="-.", label=f"Med. {median:.3f}")
    ax_hist.axvspan(p5, p95, alpha=0.10, color=CLR_REF,
                    label=f"p5-p95 [{p5:.3f}-{p95:.3f}]")

    # gercek populasyon referans bandi
    ax_hist.axvspan(1.0, 1.2, alpha=0.12, color="#FF6B6B",
                    label="Gercek pop. normal [1.0-1.2]")
    ax_hist.axvline(1.2, color="#FF6B6B", lw=1.5, ls=":")

    ax_hist.set_title("hip_circ / chest_circ Orani", fontsize=14, fontweight="bold")
    ax_hist.set_ylabel("Frekans")
    ax_hist.tick_params(labelbottom=False)
    ax_hist.legend(fontsize=9, framealpha=0.25, facecolor=AX_BG,
                   edgecolor="#3A3A5C", labelcolor=TEXT_CLR)

    ax_box.set_facecolor(AX_BG)
    ax_box.boxplot(sv, vert=False, patch_artist=True, widths=0.5,
                   medianprops=dict(color=CLR_MEDIAN, linewidth=2),
                   boxprops=dict(facecolor="#2A4A7A", edgecolor=ACCENT),
                   whiskerprops=dict(color=ACCENT, linewidth=1.2),
                   capprops=dict(color=ACCENT, linewidth=1.2),
                   flierprops=dict(marker=".", color=ACCENT, alpha=0.3, markersize=4))
    ax_box.set_yticks([])
    ax_box.set_xlabel("hip_circ / chest_circ")
    ax_box.spines["left"].set_visible(False)
    ax_box.axvline(1.2, color="#FF6B6B", lw=1.5, ls=":")

    fig.text(0.98, 0.02,
             f"n={len(sv):,}   std={np.std(sv):.4f}   [{min(sv):.3f} - {max(sv):.3f}]",
             ha="right", va="bottom", fontsize=9, color="#888899")

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot -> {out_path}")

# ── main ─────────────────────────────────────────────────────────────────────
def main():
    rng = random.Random(RANDOM_SEED)

    json_files = sorted(META_DIR.glob("*_meta.json"))
    print(f"{len(json_files)} meta.json okunuyor...")

    records = {}
    for f in json_files:
        obj = json.loads(f.read_text(encoding="utf-8"))
        cid = obj.get("char_id") or f.stem.replace("_meta", "")
        hip   = obj.get("hip_circ_cm")
        chest = obj.get("chest_circ_cm")
        if hip and chest and chest > 0:
            records[cid] = {
                "ratio":     round(hip / chest, 4),
                "hip_circ":   hip,
                "chest_circ": chest,
            }

    ratios = sorted(records.items(), key=lambda x: x[1]["ratio"])
    sv     = [v["ratio"] for _, v in ratios]
    n      = len(sv)

    print(f"Gecerli kayit: {n:,}")

    # annotated gorseller
    annotated = {}
    for d in DEBUG_DIR.iterdir():
        if not d.is_dir():
            continue
        img = d / f"{d.name}_height_annotated_front.png"
        if img.exists():
            annotated[d.name] = img

    # plot
    plot_path = PLOTS_DIR / "hip_chest_ratio.png"
    make_plot(sv, plot_path)

    # bin'ler
    bins = make_bins(sv)
    bin_chars = [[] for _ in bins]
    for cid, v in ratios:
        bin_chars[bin_index(v["ratio"], bins)].append((cid, v))

    # istatistikler
    mean   = sum(sv) / n
    std    = math.sqrt(sum((x - mean)**2 for x in sv) / n)
    over12 = sum(1 for x in sv if x > 1.2)
    over13 = sum(1 for x in sv if x > 1.3)

    # markdown
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# hip_circ / chest_circ Oran Analizi\n\n")
    lines.append(f"**Karakter sayisi:** {n:,}  \n\n")
    lines.append("## Dagilim\n\n")
    lines.append("![hip_circ/chest_circ orani](plots/hip_chest_ratio.png)\n\n")

    lines.append("## Istatistikler\n\n")
    lines.append("| Istatistik | Deger |\n|---|---|\n")
    lines.append(f"| min | {sv[0]:.4f} |\n")
    lines.append(f"| max | {sv[-1]:.4f} |\n")
    lines.append(f"| ortalama | {mean:.4f} |\n")
    lines.append(f"| std | {std:.4f} |\n")
    lines.append(f"| p5 | {percentile(sv,5):.4f} |\n")
    lines.append(f"| p25 | {percentile(sv,25):.4f} |\n")
    lines.append(f"| p50 | {percentile(sv,50):.4f} |\n")
    lines.append(f"| p75 | {percentile(sv,75):.4f} |\n")
    lines.append(f"| p95 | {percentile(sv,95):.4f} |\n")
    lines.append(f"| oran > 1.2 | {over12:,} ({over12/n*100:.1f}%) |\n")
    lines.append(f"| oran > 1.3 | {over13:,} ({over13/n*100:.1f}%) |\n\n")

    lines.append("## Bin Ornekleri\n\n")

    for i, (lo_b, hi_b) in enumerate(bins):
        pool   = [(cid, v) for cid, v in bin_chars[i] if cid in annotated]
        sample = rng.sample(pool, min(SAMPLES, len(pool)))
        count  = len(bin_chars[i])
        pct    = count / n * 100

        # bin basliginda referansa gore yorum
        flag = ""
        if lo_b >= 1.3:
            flag = " -- **cok siktili, armut**"
        elif lo_b >= 1.2:
            flag = " -- **gercek pop. siniri asiliyor**"
        elif hi_b <= 1.05:
            flag = " -- **dengeli / atletik**"

        lines.append(
            f"**Bin {i+1:02d}** &nbsp; `{lo_b:.4f} - {hi_b:.4f}` "
            f"&nbsp; {count:,} karakter ({pct:.1f}%){flag}\n\n"
        )

        if sample:
            lines.append('<div style="display:flex;gap:6px;flex-wrap:wrap;">\n\n')
            for cid, v in sample:
                label = f"{cid} | hip={v['hip_circ']:.1f} chest={v['chest_circ']:.1f} r={v['ratio']:.3f}"
                dst = THUMB_DIR / f"bin{i:02d}_{cid}.png"
                if not dst.exists():
                    save_thumb(annotated[cid], dst)
                rel = f"plots/hip_chest_samples/bin{i:02d}_{cid}.png"
                lines.append(img_tag(rel, alt=label) + "\n\n")
            lines.append("</div>\n\n")
        else:
            lines.append("_Bu aralikta annotated gorsel yok._\n\n")

        lines.append("---\n\n")

    OUT_MD.write_text("".join(lines), encoding="utf-8")
    print(f"Yazildi -> {OUT_MD}")


if __name__ == "__main__":
    main()

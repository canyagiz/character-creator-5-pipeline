"""
WHR, chest/waist orani ve Ponderal Index uzerinden
vucut tipi siniflandirmasi yapar ve docs/body_types.md uretir.
"""

import json
import math
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from PIL import Image

# ── yollar ───────────────────────────────────────────────────────────────────
META_DIR  = Path("renders/meta")
DEBUG_DIR = Path("renders/debug")
OUT_MD    = Path("docs/body_types.md")
PLOTS_DIR = Path("docs/plots")
THUMB_DIR = PLOTS_DIR / "body_type_samples"

SAMPLES     = 5
THUMB_W     = 180
RANDOM_SEED = 42

# ── siniflandirma esikleri ───────────────────────────────────────────────────
WHR_THRESHOLDS = {
    "Armut":   (0.000, 0.800),
    "Normal":  (0.800, 0.900),
    "Elma":    (0.900, 9.999),
}

CWR_THRESHOLDS = {
    "Ters (bel>gogus)": (0.000, 1.000),
    "Dikdortgen":       (1.000, 1.200),
    "Atletik":          (1.200, 1.400),
    "V-Shape":          (1.400, 9.999),
}

PI_THRESHOLDS = {
    "Obez":        (0.000, 3.750),
    "Agir":        (3.750, 3.900),
    "Normal":      (3.900, 4.200),
    "Zayif":       (4.200, 4.500),
    "Cok Zayif":   (4.500, 9.999),
}

# ── stil ─────────────────────────────────────────────────────────────────────
FIG_BG   = "#1A1A2E"
AX_BG    = "#16213E"
ACCENT   = "#4C9BE8"
TEXT_CLR = "#E0E0E0"

plt.rcParams.update({
    "figure.facecolor": FIG_BG, "axes.facecolor": AX_BG,
    "axes.edgecolor": "#3A3A5C", "axes.labelcolor": TEXT_CLR,
    "axes.titlecolor": TEXT_CLR, "xtick.color": TEXT_CLR,
    "ytick.color": TEXT_CLR, "grid.color": "#2A2A4A",
    "text.color": TEXT_CLR, "font.family": "sans-serif", "font.size": 11,
})

CAT_COLORS = [
    "#4C9BE8", "#4CE8A0", "#E8624C", "#E8D44C",
    "#B44CE8", "#E87C4C", "#4CE8D4",
]

# ── yardimcilar ───────────────────────────────────────────────────────────────
def classify(val, thresholds):
    for label, (lo, hi) in thresholds.items():
        if lo <= val < hi:
            return label
    return list(thresholds.keys())[-1]

def save_thumb(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(src)
    ratio = THUMB_W / img.width
    img = img.resize((THUMB_W, int(img.height * ratio)), Image.LANCZOS)
    img.save(dst, optimize=True)

def img_tag(rel, alt="", w=THUMB_W):
    return f'<img src="{rel}" alt="{alt}" width="{w}">'

# ── plot: dagilim + esikler ───────────────────────────────────────────────────
def dist_plot(vals, thresholds, title, xlabel, out_path, ref_lines=None):
    sv = sorted(vals)
    fig, (ax_h, ax_b) = plt.subplots(
        2, 1, figsize=(11, 6),
        gridspec_kw={"height_ratios": [4, 1], "hspace": 0.05},
        facecolor=FIG_BG,
    )

    sns.histplot(sv, bins=50, color=ACCENT, alpha=0.7, kde=True, ax=ax_h)
    if ax_h.lines:
        ax_h.lines[-1].set(linewidth=2, color="#7DC8F0")

    ax_h.axvline(np.mean(sv),   color="#E8624C", lw=1.8, ls="--",
                 label=f"Ort. {np.mean(sv):.3f}")
    ax_h.axvline(np.median(sv), color="#4CE8A0", lw=1.8, ls="-.",
                 label=f"Med. {np.median(sv):.3f}")

    if ref_lines:
        for val, label in ref_lines:
            ax_h.axvline(val, color="#E8D44C", lw=1.4, ls=":", label=label)

    # esik bantlari
    colors = CAT_COLORS
    ymax = ax_h.get_ylim()[1]
    for ci, (cat, (lo, hi)) in enumerate(thresholds.items()):
        x0 = max(lo, min(sv) - 0.05)
        x1 = min(hi, max(sv) + 0.05)
        ax_h.axvspan(x0, x1, alpha=0.08, color=colors[ci % len(colors)])
        mid = (x0 + x1) / 2
        if x1 - x0 > (max(sv) - min(sv)) * 0.05:
            ax_h.text(mid, ymax * 0.92, cat, ha="center", fontsize=8,
                      color=colors[ci % len(colors)], fontweight="bold")

    ax_h.set_title(title, fontsize=14, fontweight="bold")
    ax_h.set_ylabel("Frekans")
    ax_h.tick_params(labelbottom=False)
    ax_h.legend(fontsize=9, framealpha=0.25, facecolor=AX_BG,
                edgecolor="#3A3A5C", labelcolor=TEXT_CLR)

    ax_b.set_facecolor(AX_BG)
    ax_b.boxplot(sv, vert=False, patch_artist=True, widths=0.5,
                 medianprops=dict(color="#4CE8A0", linewidth=2),
                 boxprops=dict(facecolor="#2A4A7A", edgecolor=ACCENT),
                 whiskerprops=dict(color=ACCENT, linewidth=1.2),
                 capprops=dict(color=ACCENT, linewidth=1.2),
                 flierprops=dict(marker=".", color=ACCENT, alpha=0.3, markersize=4))
    ax_b.set_yticks([])
    ax_b.set_xlabel(xlabel)
    ax_b.spines["left"].set_visible(False)

    fig.text(0.98, 0.02,
             f"n={len(sv):,}   std={np.std(sv):.4f}   [{min(sv):.3f} - {max(sv):.3f}]",
             ha="right", va="bottom", fontsize=9, color="#888899")

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot -> {out_path}")


# ── plot: kategori bar chart ──────────────────────────────────────────────────
def cat_bar(cat_counts, title, out_path):
    labels = list(cat_counts.keys())
    counts = list(cat_counts.values())
    total  = sum(counts)

    fig, ax = plt.subplots(figsize=(9, 4), facecolor=FIG_BG)
    ax.set_facecolor(AX_BG)

    bars = ax.bar(labels, counts,
                  color=CAT_COLORS[:len(labels)], edgecolor="#3A3A5C", linewidth=0.8)

    for bar, cnt in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + total*0.005,
                f"{cnt:,}\n({cnt/total*100:.1f}%)",
                ha="center", va="bottom", fontsize=10, color=TEXT_CLR)

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel("Karakter sayisi")
    ax.set_ylim(0, max(counts) * 1.18)
    ax.tick_params(axis="x", labelsize=10)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Cat bar -> {out_path}")


# ── plot: kombinasyon heatmap ─────────────────────────────────────────────────
def combo_heatmap(records, out_path):
    whr_cats = list(WHR_THRESHOLDS.keys())
    pi_cats  = list(PI_THRESHOLDS.keys())
    mat = np.zeros((len(pi_cats), len(whr_cats)), dtype=int)
    for r in records.values():
        ri = pi_cats.index(r["pi_cat"])
        ci = whr_cats.index(r["whr_cat"])
        mat[ri, ci] += 1

    fig, ax = plt.subplots(figsize=(8, 5), facecolor=FIG_BG)
    ax.set_facecolor(AX_BG)
    sns.heatmap(mat, annot=True, fmt="d", cmap="Blues",
                xticklabels=whr_cats, yticklabels=pi_cats,
                linewidths=0.5, ax=ax,
                annot_kws={"size": 11, "color": TEXT_CLR},
                cbar_kws={"shrink": 0.8})
    ax.set_title("WHR x Ponderal Index Kombinasyonu", fontsize=13, fontweight="bold")
    ax.set_xlabel("WHR Kategorisi (Sekil)")
    ax.set_ylabel("Ponderal Index Kategorisi (Hacim)")
    ax.tick_params(axis="x", labelsize=10)
    ax.tick_params(axis="y", labelsize=10, rotation=0)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Combo heatmap -> {out_path}")


# ── markdown yardimcisi ───────────────────────────────────────────────────────
def write_metric_section(lines, metric_key, metric_label, thresholds,
                          records, annotated, rng, plot_rel, cat_rel):
    lines.append(f"## {metric_label}\n\n")
    lines.append(f"![{metric_label} dagilimi]({plot_rel})\n\n")
    lines.append(f"![{metric_label} kategoriler]({cat_rel})\n\n")

    lines.append("### Esikler\n\n")
    lines.append("| Kategori | Aralik |\n|---|---|\n")
    for cat, (lo, hi) in thresholds.items():
        lo_s = f"{lo:.3f}" if lo > 0 else "—"
        hi_s = f"{hi:.3f}" if hi < 9 else "—"
        lines.append(f"| {cat} | {lo_s} – {hi_s} |\n")
    lines.append("\n")

    # her kategori icin ornekler
    lines.append("### Kategori Ornekleri\n\n")
    by_cat = defaultdict(list)
    for cid, r in records.items():
        by_cat[r[metric_key]].append((cid, r))

    for ci, (cat, (lo, hi)) in enumerate(thresholds.items()):
        pool   = [(cid, r) for cid, r in by_cat[cat] if cid in annotated]
        sample = rng.sample(pool, min(SAMPLES, len(pool)))
        count  = len(by_cat[cat])
        total  = len(records)

        color_tag = CAT_COLORS[ci % len(CAT_COLORS)]
        lines.append(
            f"**{cat}** &nbsp; `{lo:.3f} – {hi if hi < 9 else '∞':.3f}`"
            f" &nbsp; {count:,} karakter ({count/total*100:.1f}%)\n\n"
            if hi < 9 else
            f"**{cat}** &nbsp; `{lo:.3f} – ∞`"
            f" &nbsp; {count:,} karakter ({count/total*100:.1f}%)\n\n"
        )

        if sample:
            lines.append('<div style="display:flex;gap:6px;flex-wrap:wrap;">\n\n')
            for cid, r in sample:
                val = r[metric_key.replace("_cat", "")]
                label = f"{cid} | {metric_key.replace('_cat','')}={val:.3f}"
                safe_cat = cat.replace('/', '_').replace(' ', '_').replace('>', 'gt').replace('<', 'lt').replace('(', '').replace(')', '')
                dst = THUMB_DIR / metric_key / f"{safe_cat}_{cid}.png"
                if not dst.exists():
                    save_thumb(annotated[cid], dst)
                rel = f"plots/body_type_samples/{metric_key}/{dst.name}"
                lines.append(img_tag(rel, alt=label) + "\n\n")
            lines.append("</div>\n\n")
        else:
            lines.append("_Bu kategoride annotated gorsel yok._\n\n")

    lines.append("---\n\n")


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    rng = random.Random(RANDOM_SEED)

    json_files = sorted(META_DIR.glob("*_meta.json"))
    print(f"{len(json_files)} meta.json okunuyor...")

    records = {}
    for f in json_files:
        d   = json.loads(f.read_text(encoding="utf-8"))
        cid = d.get("char_id") or f.stem.replace("_meta", "")
        w   = d.get("waist_circ_cm")
        hip = d.get("hip_circ_cm")
        c   = d.get("chest_circ_cm")
        v   = d.get("volume_L")
        ht  = d.get("height_cm")
        if not all([w, hip, c, v, ht]):
            continue
        whr = w / hip
        cwr = c / w
        pi  = ht / (v * 1000) ** (1/3)
        records[cid] = {
            "whr": round(whr, 4), "whr_cat": classify(whr, WHR_THRESHOLDS),
            "cwr": round(cwr, 4), "cwr_cat": classify(cwr, CWR_THRESHOLDS),
            "pi":  round(pi,  4), "pi_cat":  classify(pi,  PI_THRESHOLDS),
            "waist": w, "hip": hip, "chest": c, "volume": v, "height": ht,
        }

    print(f"Gecerli kayit: {len(records):,}")

    annotated = {}
    for d in DEBUG_DIR.iterdir():
        if not d.is_dir():
            continue
        img = d / f"{d.name}_height_annotated_front.png"
        if img.exists():
            annotated[d.name] = img

    # ── plotlar ───────────────────────────────────────────────────────────────
    whrs = [r["whr"] for r in records.values()]
    cwrs = [r["cwr"] for r in records.values()]
    pis  = [r["pi"]  for r in records.values()]

    dist_plot(whrs, WHR_THRESHOLDS,
              "WHR — Waist / Hip Orani", "WHR",
              PLOTS_DIR / "bt_whr_dist.png",
              ref_lines=[(0.85, "Kadin esigi"), (0.90, "Erkek esigi")])

    dist_plot(cwrs, CWR_THRESHOLDS,
              "Chest / Waist Orani (V-Shape)", "chest / waist",
              PLOTS_DIR / "bt_cwr_dist.png",
              ref_lines=[(1.4, "V-Shape siniri")])

    dist_plot(pis, PI_THRESHOLDS,
              "Ponderal Index — height / (volume*1000)^(1/3)", "Ponderal Index",
              PLOTS_DIR / "bt_pi_dist.png")

    # kategori bar chartlar
    whr_counts = {k: sum(1 for r in records.values() if r["whr_cat"] == k)
                  for k in WHR_THRESHOLDS}
    cwr_counts = {k: sum(1 for r in records.values() if r["cwr_cat"] == k)
                  for k in CWR_THRESHOLDS}
    pi_counts  = {k: sum(1 for r in records.values() if r["pi_cat"]  == k)
                  for k in PI_THRESHOLDS}

    cat_bar(whr_counts, "WHR Kategori Dagilimi",    PLOTS_DIR / "bt_whr_cats.png")
    cat_bar(cwr_counts, "Chest/Waist Kategori Dagilimi", PLOTS_DIR / "bt_cwr_cats.png")
    cat_bar(pi_counts,  "Ponderal Index Kategori Dagilimi", PLOTS_DIR / "bt_pi_cats.png")

    combo_heatmap(records, PLOTS_DIR / "bt_combo_heatmap.png")

    # ── markdown ─────────────────────────────────────────────────────────────
    n = len(records)
    lines = []
    lines.append("# Vucut Tipi Siniflandirmasi\n\n")
    lines.append(f"**Karakter sayisi:** {n:,}  \n\n")

    lines.append("## Yontem Ozeti\n\n")
    lines.append("| Siniflandirma | Metrik | Guvenirlilk |\n|---|---|---|\n")
    lines.append("| Elma / Armut | WHR = waist / hip | Yuksek |\n")
    lines.append("| V-Shape / Dikdortgen | chest / waist orani | Orta-Yuksek |\n")
    lines.append("| Zayif / Normal / Obez | Ponderal Index = height / (volume*1000)^(1/3) | Orta |\n")
    lines.append("| Ektomorf / Endomorf | PI + WHR kombinasyonu | Orta |\n\n")

    lines.append("## WHR x Ponderal Index Kombinasyonu\n\n")
    lines.append("![Kombinasyon heatmap](plots/bt_combo_heatmap.png)\n\n")
    lines.append("---\n\n")

    write_metric_section(
        lines, "whr_cat", "WHR — Elma / Armut / Normal",
        WHR_THRESHOLDS, records, annotated, rng,
        "plots/bt_whr_dist.png", "plots/bt_whr_cats.png"
    )

    write_metric_section(
        lines, "cwr_cat", "Chest / Waist — V-Shape / Atletik / Dikdortgen",
        CWR_THRESHOLDS, records, annotated, rng,
        "plots/bt_cwr_dist.png", "plots/bt_cwr_cats.png"
    )

    write_metric_section(
        lines, "pi_cat", "Ponderal Index — Hacim / Boy Orani",
        PI_THRESHOLDS, records, annotated, rng,
        "plots/bt_pi_dist.png", "plots/bt_pi_cats.png"
    )

    OUT_MD.write_text("".join(lines), encoding="utf-8")
    print(f"\nTamamlandi -> {OUT_MD}")


if __name__ == "__main__":
    main()

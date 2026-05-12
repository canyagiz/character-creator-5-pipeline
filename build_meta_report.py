"""
Her metrik icin histogrami 10 araliga boler,
her araliktan rastgele 5 char secer, annotated debug
gorselini thumbnail olarak kaydeder ve
docs/meta_distribution.md'yi yeniden uretir.

Cikti:
  docs/plots/samples/<key>/bin<N>_<char_id>.png   -- thumbnail'lar
  docs/meta_distribution.md                        -- guncellenmis rapor
"""

import json
import math
import random
import shutil
from pathlib import Path
from collections import defaultdict

from PIL import Image

# ── yollar ──────────────────────────────────────────────────────────────────
META_DIR   = Path("renders/meta")
DEBUG_DIR  = Path("renders/debug")
OUT_MD     = Path("docs/meta_distribution.md")
PLOTS_DIR  = Path("docs/plots")
THUMB_DIR  = PLOTS_DIR / "samples"

BINS        = 10
SAMPLES     = 5
THUMB_W     = 180   # px — markdown'da yan yana 5 adet rahat gozukur
RANDOM_SEED = 42

# ── istatistik yardimcilari ─────────────────────────────────────────────────
def percentile(sv, p):
    idx = (len(sv) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(sv) - 1)
    return sv[lo] * (1 - (idx - lo)) + sv[hi] * (idx - lo)


def make_bins(sv):
    lo, hi = sv[0], sv[-1]
    if lo == hi:
        return [(lo, hi)]
    step = (hi - lo) / BINS
    edges = [lo + step * i for i in range(BINS + 1)]
    edges[-1] = hi
    return [(edges[i], edges[i + 1]) for i in range(BINS)]


def bin_index(val, bins):
    for i, (lo, hi) in enumerate(bins):
        if val <= hi:
            return i
    return len(bins) - 1


# ── thumbnail ────────────────────────────────────────────────────────────────
def save_thumb(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(src)
    ratio = THUMB_W / img.width
    new_h = int(img.height * ratio)
    img = img.resize((THUMB_W, new_h), Image.LANCZOS)
    img.save(dst, optimize=True)


# ── markdown yardimcilari ────────────────────────────────────────────────────
def img_tag(rel_path: str, alt: str = "", width: int = THUMB_W) -> str:
    return f'<img src="{rel_path}" alt="{alt}" width="{width}">'


# ── ana fonksiyon ─────────────────────────────────────────────────────────────
def main():
    rng = random.Random(RANDOM_SEED)

    # meta.json'lari oku
    json_files = sorted(META_DIR.glob("*_meta.json"))
    if not json_files:
        raise FileNotFoundError(f"Meta JSON bulunamadi: {META_DIR}")
    print(f"{len(json_files)} meta.json okunuyor...")

    # char_id -> {key: val}
    records: dict[str, dict] = {}
    for f in json_files:
        obj = json.loads(f.read_text(encoding="utf-8"))
        cid = obj.get("char_id") or f.stem.replace("_meta", "")
        records[cid] = {k: v for k, v in obj.items() if isinstance(v, (int, float))}

    # key -> sorted list of (val, char_id)
    key_vals: dict[str, list] = defaultdict(list)
    for cid, metrics in records.items():
        for k, v in metrics.items():
            key_vals[k].append((v, cid))
    for k in key_vals:
        key_vals[k].sort()

    # annotated debug gorsellerini bul
    annotated: dict[str, Path] = {}
    for d in DEBUG_DIR.iterdir():
        if not d.is_dir():
            continue
        cid = d.name
        img = d / f"{cid}_height_annotated_front.png"
        if img.exists():
            annotated[cid] = img

    print(f"Annotated gorsel bulunan char: {len(annotated)}")

    # thumbnail'lari uret + markdown'u olustur
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Meta JSON Dagilim Analizi\n\n")
    lines.append(f"**Dosya sayisi:** {len(json_files):,}  \n")
    lines.append(f"**Kaynak:** `{META_DIR}/`\n\n")
    lines.append("## Genel Bakis\n\n")
    lines.append("![Tum degiskenler](plots/meta_overview.png)\n\n")
    lines.append("## Korelasyon\n\n")
    lines.append("![Korelasyon matrisi](plots/meta_correlation.png)\n\n")
    lines.append("---\n\n")

    for key, pairs in key_vals.items():
        sv   = [v for v, _ in pairs]
        cids = [c for _, c in pairs]
        n    = len(sv)
        mean = sum(sv) / n
        std  = math.sqrt(sum((x - mean) ** 2 for x in sv) / n)

        bins = make_bins(sv)

        # bin -> [char_id]
        bin_chars: list[list[str]] = [[] for _ in bins]
        for val, cid in pairs:
            bin_chars[bin_index(val, bins)].append(cid)

        lines.append(f"## `{key}`\n\n")
        lines.append(f"![{key}](plots/meta_{key}.png)\n\n")

        # istatistik tablosu
        lines.append("| Istatistik | Deger |\n|---|---|\n")
        lines.append(f"| n | {n:,} |\n")
        lines.append(f"| min | {sv[0]:.3f} |\n")
        lines.append(f"| max | {sv[-1]:.3f} |\n")
        lines.append(f"| ortalama | {mean:.3f} |\n")
        lines.append(f"| std | {std:.3f} |\n")
        lines.append(f"| p5 | {percentile(sv, 5):.3f} |\n")
        lines.append(f"| p25 | {percentile(sv, 25):.3f} |\n")
        lines.append(f"| p50 | {percentile(sv, 50):.3f} |\n")
        lines.append(f"| p75 | {percentile(sv, 75):.3f} |\n")
        lines.append(f"| p95 | {percentile(sv, 95):.3f} |\n\n")

        # her bin icin ornekler
        lines.append("### Aralik Ornekleri\n\n")

        for i, (lo_b, hi_b) in enumerate(bins):
            pool = [c for c in bin_chars[i] if c in annotated]
            sample = rng.sample(pool, min(SAMPLES, len(pool)))
            count  = len(bin_chars[i])
            pct    = count / n * 100

            lines.append(
                f"**Bin {i+1:02d}** &nbsp; `{lo_b:.2f} – {hi_b:.2f}` "
                f"&nbsp; {count:,} karakter ({pct:.1f}%)\n\n"
            )

            if sample:
                lines.append('<div style="display:flex;gap:6px;flex-wrap:wrap;">\n\n')
                for cid in sample:
                    src = annotated[cid]
                    rel_thumb = f"samples/{key}/bin{i:02d}_{cid}.png"
                    dst = PLOTS_DIR / "samples" / key / f"bin{i:02d}_{cid}.png"
                    if not dst.exists():
                        save_thumb(src, dst)
                    lines.append(
                        img_tag(f"plots/{rel_thumb}", alt=cid) + "\n\n"
                    )
                lines.append("</div>\n\n")
            else:
                lines.append("_Bu aralikta annotated gorsel yok._\n\n")

        lines.append("---\n\n")
        print(f"  {key} islendi")

    OUT_MD.write_text("".join(lines), encoding="utf-8")
    print(f"\nTamamlandi -> {OUT_MD}")


if __name__ == "__main__":
    main()

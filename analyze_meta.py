"""
renders/meta/ altındaki tüm *_meta.json dosyalarını okuyup
her sayısal key için dağılım istatistikleri hesaplar ve
docs/meta_distribution.md olarak yazar.
"""

import json
import math
from pathlib import Path
from collections import defaultdict

META_DIR = Path("renders/meta")
OUT_FILE = Path("docs/meta_distribution.md")
HISTOGRAM_BINS = 10


def percentile(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    idx = (len(sorted_vals) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def histogram(sorted_vals, bins=HISTOGRAM_BINS):
    lo, hi = sorted_vals[0], sorted_vals[-1]
    if lo == hi:
        return [(lo, hi, len(sorted_vals))]
    step = (hi - lo) / bins
    edges = [lo + step * i for i in range(bins)] + [hi]
    counts = [0] * bins
    for v in sorted_vals:
        idx = min(int((v - lo) / step), bins - 1)
        counts[idx] += 1
    return [(edges[i], edges[i + 1], counts[i]) for i in range(bins)]


def bar(count, total, width=20):
    filled = round(count / total * width)
    return "█" * filled + "░" * (width - filled)


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

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Meta JSON Dagilim Analizi\n\n")
    lines.append(f"**Dosya sayisi:** {len(json_files):,}  \n")
    lines.append(f"**Kaynak:** `{META_DIR}/`\n\n")
    lines.append("## Genel Bakis\n\n")
    lines.append("![Tum degiskenler](plots/meta_overview.png)\n\n")
    lines.append("## Korelasyon\n\n")
    lines.append("![Korelasyon matrisi](plots/meta_correlation.png)\n\n")
    lines.append("---\n\n")

    for key, vals in data.items():
        sorted_vals = sorted(vals)
        n = len(sorted_vals)
        mean = sum(sorted_vals) / n
        variance = sum((x - mean) ** 2 for x in sorted_vals) / n
        std = math.sqrt(variance)

        p5   = percentile(sorted_vals, 5)
        p25  = percentile(sorted_vals, 25)
        p50  = percentile(sorted_vals, 50)
        p75  = percentile(sorted_vals, 75)
        p95  = percentile(sorted_vals, 95)

        lines.append(f"## `{key}`\n\n")
        lines.append(f"![{key}](plots/meta_{key}.png)\n\n")
        lines.append("| Istatistik | Deger |\n")
        lines.append("|---|---|\n")
        lines.append(f"| n | {n:,} |\n")
        lines.append(f"| min | {sorted_vals[0]:.3f} |\n")
        lines.append(f"| max | {sorted_vals[-1]:.3f} |\n")
        lines.append(f"| ortalama | {mean:.3f} |\n")
        lines.append(f"| std | {std:.3f} |\n")
        lines.append(f"| p5 | {p5:.3f} |\n")
        lines.append(f"| p25 | {p25:.3f} |\n")
        lines.append(f"| p50 (medyan) | {p50:.3f} |\n")
        lines.append(f"| p75 | {p75:.3f} |\n")
        lines.append(f"| p95 | {p95:.3f} |\n")
        lines.append("\n---\n\n")

    OUT_FILE.write_text("".join(lines), encoding="utf-8")
    print(f"Yazildi: {OUT_FILE}")


if __name__ == "__main__":
    main()

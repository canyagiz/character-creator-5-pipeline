"""
debug_widths.py — Silüet genişlik ölçümlerini görsel olarak doğrular.
Her sınıftan 3 karakter seçer, ölçüm noktalarını çizer.

Calistir: python analysis/debug_widths.py
Cikti:    analysis/debug_widths/
"""

import json
import os
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

SIL_DIR  = str(_ROOT / "calib" / "renders_calib" / "silhouettes")
OUT_DIR  = str(_ROOT / "analysis" / "debug_widths")
os.makedirs(OUT_DIR, exist_ok=True)

# Silüet analiz sonuçları
df = pd.read_csv(str(_ROOT / "analysis" / "silhouette_analysis.csv"))

def visual_label(row):
    wh  = row["waist_over_hip"]
    hos = row["hip_over_shoulder"]
    if wh > 0.88:
        return "apple"
    elif hos < 0.72 and wh < 0.82:
        return "v_shape"
    elif hos > 1.00 and wh < 0.84:
        return "pear"
    elif 0.85 <= hos <= 1.05 and wh < 0.78:
        return "hourglass"
    else:
        return "rectangle"

df["visual_label"] = df.apply(visual_label, axis=1)

# Her sınıftan 3 karakter seç (en tipik olanlar)
LABELS = ["apple", "v_shape", "pear", "hourglass", "rectangle"]
selected = {}
for label in LABELS:
    sub = df[df["visual_label"] == label].copy()
    if len(sub) == 0:
        selected[label] = []
        continue
    # En tipik: ortalamaya en yakın hip_over_shoulder değerine sahip olanlar
    sub["dist"] = (sub["hip_over_shoulder"] - sub["hip_over_shoulder"].mean()).abs()
    picks = sub.nsmallest(3, "dist")["char_id"].tolist()
    selected[label] = picks

print("Seçilen karakterler:")
for label, ids in selected.items():
    print(f"  {label}: {ids}")

# ── Ölçüm fonksiyonu (silhouette_widths.py ile aynı mantık) ──────────────────
def get_measurements(img_path):
    img_rgba = Image.open(img_path).convert("RGBA")
    arr      = np.array(img_rgba)
    gray     = arr[:, :, :3].mean(axis=2)
    body     = gray > 128

    h, w = body.shape
    row_w = body.sum(axis=1)
    body_rows = np.where(row_w > 5)[0]
    if len(body_rows) < 10:
        return None

    top = body_rows[0]
    bot = body_rows[-1]
    bh  = bot - top

    def span_at(rel):
        row = int(top + rel * bh)
        row = max(0, min(h - 1, row))
        cols = np.where(body[row])[0]
        if len(cols) < 2:
            spans = []
            for off in range(-8, 9):
                r2 = row + off
                if 0 <= r2 < h:
                    c2 = np.where(body[r2])[0]
                    if len(c2) >= 2:
                        spans.append((c2[0], c2[-1]))
            if not spans:
                return row, 0, w // 2, w // 2
            left  = int(np.mean([s[0] for s in spans]))
            right = int(np.mean([s[1] for s in spans]))
            return row, right - left, left, right
        return row, cols[-1] - cols[0], int(cols[0]), int(cols[-1])

    # Omuz: 0.08-0.22 arası en geniş
    shoulder_data = [(span_at(r)) for r in np.linspace(0.08, 0.22, 20)]
    sh_row, sh_span, sh_left, sh_right = max(shoulder_data, key=lambda x: x[1])

    # Bel: 0.35-0.55 arası en dar
    waist_data = [(span_at(r)) for r in np.linspace(0.35, 0.55, 30)]
    wa_row, wa_span, wa_left, wa_right = min(waist_data, key=lambda x: x[1])

    # Kalça: 0.52-0.72 arası en geniş
    hip_data = [(span_at(r)) for r in np.linspace(0.52, 0.72, 30)]
    hi_row, hi_span, hi_left, hi_right = max(hip_data, key=lambda x: x[1])

    return {
        "w": w, "h": h,
        "shoulder": (sh_row, sh_left, sh_right, sh_span),
        "waist":    (wa_row, wa_left, wa_right, wa_span),
        "hip":      (hi_row, hi_left, hi_right, hi_span),
    }

# ── Debug görsel üret ─────────────────────────────────────────────────────────
COLORS = {
    "shoulder": (255, 80,  80,  200),   # kırmızı
    "waist":    (80,  200, 80,  200),   # yeşil
    "hip":      (80,  80,  255, 200),   # mavi
}
LABEL_COLORS = {
    "apple":     (255, 120,  50),
    "v_shape":   (50,  150, 255),
    "pear":      (200,  80, 200),
    "hourglass": (255, 200,  50),
    "rectangle": (150, 150, 150),
}

for label, char_ids in selected.items():
    if not char_ids:
        print(f"  {label}: karakter yok, atlanıyor")
        continue

    # Yan yana 3 görsel
    panels = []
    for char_id in char_ids:
        img_path = os.path.join(SIL_DIR, char_id, f"{char_id}_front.png")
        if not os.path.exists(img_path):
            continue

        meas = get_measurements(img_path)
        if meas is None:
            continue

        # Orijinal görsel (RGBA → RGB beyaz arka plan)
        orig = Image.open(img_path).convert("RGBA")
        bg   = Image.new("RGBA", orig.size, (40, 40, 40, 255))
        comp = Image.alpha_composite(bg, orig).convert("RGB")
        draw = ImageDraw.Draw(comp, "RGBA")

        w = meas["w"]

        for part, (row, left, right, span) in [
            ("shoulder", meas["shoulder"]),
            ("waist",    meas["waist"]),
            ("hip",      meas["hip"]),
        ]:
            color = COLORS[part]
            # Yatay çizgi
            draw.line([(0, row), (w, row)], fill=(*color[:3], 80), width=1)
            # Genişlik çubuğu (kalın)
            draw.line([(left, row), (right, row)], fill=color, width=4)
            # Uç noktalar
            draw.ellipse([left-5, row-5, left+5, row+5],  fill=color)
            draw.ellipse([right-5, row-5, right+5, row+5], fill=color)
            # Genişlik yazısı
            draw.text(
                (right + 8, row - 8),
                f"{part[0].upper()}: {span}px",
                fill=(*color[:3],),
            )

        # Oranları yaz
        row_data = df[df["char_id"] == char_id].iloc[0]
        hos = row_data["hip_over_shoulder"]
        woh = row_data["waist_over_hip"]
        info = f"{char_id}\nhip/sh={hos:.2f}  wst/hip={woh:.2f}\n{row_data['gender']}  fat={row_data['fat_score']:.2f}  mu={row_data['muscle_score']:.2f}"
        lc = LABEL_COLORS[label]
        # Bilgi kutusu
        draw.rectangle([(0, 0), (w, 70)], fill=(0, 0, 0, 180))
        draw.text((8, 5), info, fill=lc)

        panels.append(comp)

    if not panels:
        continue

    # Birleştir
    pw, ph = panels[0].size
    combined = Image.new("RGB", (pw * len(panels), ph + 40), (25, 25, 25))
    for i, p in enumerate(panels):
        combined.paste(p, (i * pw, 0))

    # Başlık
    header_draw = ImageDraw.Draw(combined)
    lc = LABEL_COLORS[label]
    header_draw.rectangle([(0, ph), (pw * len(panels), ph + 40)], fill=(20, 20, 20))
    header_draw.text(
        (pw * len(panels) // 2 - 60, ph + 10),
        f"[ {label.upper()} ]  kırmızı=omuz  yeşil=bel  mavi=kalça",
        fill=lc,
    )

    out_path = os.path.join(OUT_DIR, f"debug_{label}.png")
    combined.save(out_path)
    print(f"  Kaydedildi: {out_path}")

print("\nTamamlandı.")
print(f"\nChar ID özeti:")
for label, ids in selected.items():
    print(f"  {label:<12}: {ids}")

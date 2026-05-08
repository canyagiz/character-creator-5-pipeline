"""
silhouette_widths.py — Front silüetten omuz/bel/kalça piksel genişliklerini çıkarır.
Slider değerleri ve meta ölçümleriyle birleştirir.

Calistir: python analysis/silhouette_widths.py
Cikti:    analysis/silhouette_analysis.csv
"""

import json
import os
import numpy as np
import pandas as pd
from PIL import Image
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

SIL_DIR   = str(_ROOT / "calib" / "renders_calib" / "silhouettes")
META_DIR  = str(_ROOT / "calib" / "renders_calib" / "meta")
PROBE_CSV = str(_ROOT / "analysis" / "calibration_probe.csv")
OUT_CSV   = str(_ROOT / "analysis" / "silhouette_analysis.csv")

probe = pd.read_csv(PROBE_CSV)
probe_dict = {r["char_id"]: r for _, r in probe.iterrows()}

def measure_widths(img_path):
    """
    Front silüetten piksel genişliklerini çıkarır.
    Silüet: koyu piksel = vücut, açık piksel = arka plan.

    Döndürür:
      shoulder_w  — omuz hizasındaki genişlik (relatif yükseklik ~0.20)
      waist_w     — bel hizasındaki genişlik (relatif yükseklik ~0.45)
      hip_w       — kalça hizasındaki genişlik (relatif yükseklik ~0.60)
    Tüm değerler görüntü yüksekliğine normalize edilmiş genişlik oranları.
    """
    img = Image.open(img_path).convert("L")  # grayscale
    arr = np.array(img)

    # Silüet: arka plan koyu (0), vücut açık (255)
    # RGB ortalaması > 128 olan pikseller vücut
    img_rgba = Image.open(img_path).convert("RGBA")
    arr_rgba = np.array(img_rgba)
    gray2    = arr_rgba[:, :, :3].mean(axis=2)
    body_mask = gray2 > 128

    h, w = body_mask.shape

    # Vücut olan satırları bul (en az 5 piksel genişlik)
    row_widths = body_mask.sum(axis=1)
    body_rows  = np.where(row_widths > 5)[0]
    if len(body_rows) < 10:
        return None

    body_top = body_rows[0]
    body_bot = body_rows[-1]
    body_h   = body_bot - body_top

    def width_at(rel_height):
        """rel_height: 0=tepe, 1=taban. Outer span döndürür (en sag - en sol)."""
        row = int(body_top + rel_height * body_h)
        row = max(0, min(h - 1, row))
        cols = np.where(body_mask[row])[0]
        if len(cols) < 2:
            widths = []
            for offset in range(-8, 9):
                r2 = row + offset
                if 0 <= r2 < h:
                    c2 = np.where(body_mask[r2])[0]
                    if len(c2) >= 2:
                        widths.append(c2[-1] - c2[0])
            return np.mean(widths) / w if widths else 0.0
        return (cols[-1] - cols[0]) / w

    # Omuz: boyun hemen altı ~0.10-0.18, en geniş nokta
    # Bel: gövdenin ~0.40-0.55 arası en dar nokta
    # Kalça: gövdenin ~0.55-0.70 arası en geniş nokta

    # Omuz: 0.08-0.22 arası en geniş satır
    shoulder_band = [width_at(r) for r in np.linspace(0.08, 0.22, 20)]
    shoulder_w = max(shoulder_band)

    # Bel: 0.35-0.55 arası en dar satır
    waist_band = [width_at(r) for r in np.linspace(0.35, 0.55, 30)]
    waist_w = min(waist_band)

    # Kalça: 0.52-0.72 arası en geniş satır
    hip_band = [width_at(r) for r in np.linspace(0.52, 0.72, 30)]
    hip_w = max(hip_band)

    return shoulder_w, waist_w, hip_w


# ── Ana döngü ─────────────────────────────────────────────────────────────────
rows = []
errors = 0

char_ids = sorted([
    d for d in os.listdir(SIL_DIR)
    if os.path.isdir(os.path.join(SIL_DIR, d))
])

print(f"{len(char_ids)} karakter isleniyor...")

for char_id in char_ids:
    img_path  = os.path.join(SIL_DIR, char_id, f"{char_id}_front.png")
    meta_path = os.path.join(META_DIR, f"{char_id}_meta.json")

    if not os.path.exists(img_path) or not os.path.exists(meta_path):
        errors += 1
        continue

    result = measure_widths(img_path)
    if result is None:
        errors += 1
        continue

    shoulder_w, waist_w, hip_w = result

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    probe_row = probe_dict.get(char_id)
    if probe_row is None:
        errors += 1
        continue

    rows.append({
        "char_id":         char_id,
        "gender":          probe_row["gender"],
        "fat_score":       probe_row["fat_score"],
        "muscle_score":    probe_row["muscle_score"],
        "hip_score":       probe_row["hip_score"],
        "waist_def_score": probe_row["waist_def_score"],
        "height_score":    probe_row["height_score"],
        # Piksel genişlikleri (görüntü genişliğine normalize)
        "shoulder_w":      round(shoulder_w, 4),
        "waist_w":         round(waist_w, 4),
        "hip_w":           round(hip_w, 4),
        # Görsel oranlar
        "hip_over_shoulder": round(hip_w / shoulder_w, 4) if shoulder_w > 0 else None,
        "waist_over_hip":    round(waist_w / hip_w, 4)    if hip_w > 0 else None,
        "waist_over_shoulder": round(waist_w / shoulder_w, 4) if shoulder_w > 0 else None,
        # Gerçek çevre ölçümleri
        "chest_circ_cm":     meta.get("chest_circ_cm"),
        "waist_circ_cm":     meta.get("waist_circ_cm"),
        "hip_circ_cm":       meta.get("hip_circ_cm"),
    })

df = pd.DataFrame(rows)
df.to_csv(OUT_CSV, index=False)
print(f"Kaydedildi: {OUT_CSV}  ({len(df)} satir, {errors} hata)")

# ── Özet: slider vs görsel oranlar ────────────────────────────────────────────
print("\n=== SLIDER KORELASYONLARI (gorsel genisliklerle) ===")
sliders = ["fat_score", "muscle_score", "hip_score", "waist_def_score"]
metrics = ["hip_over_shoulder", "waist_over_hip", "waist_over_shoulder"]
corr = df[sliders + metrics].corr()[metrics].loc[sliders]
print(corr.round(3).to_string())

print("\n=== GORSEL ORAN ARALIK OZETI ===")
print(df[metrics + ["gender"]].groupby("gender").describe().round(3).to_string())

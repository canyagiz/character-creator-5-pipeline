"""
calibration_select.py — dataset.csv'den kalibrasyon alt kümesi seç.

Amaç: fat × muscle × hip_score × waist_def_score × somatotype × gender uzayını
iyi kapsamak. Blender'da ölçülüp slider → gerçek ölçüm modeli kurulacak.

Çıktı: analysis/calibration_probe.csv
"""

import pandas as pd
import numpy as np

DATASET  = r"C:\Users\aliya\workspace\cc5-scripts\dataset.csv"
OUTPUT   = r"C:\Users\aliya\workspace\cc5-scripts\analysis\calibration_probe.csv"

df = pd.read_csv(DATASET)

# ── Bin tanımları ──────────────────────────────────────────────────────────────
FAT_EDGES    = [0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.01]
MUSCLE_EDGES = [0.00, 0.15, 0.30, 0.45, 0.60, 0.75, 1.01]
HIP_EDGES    = [0.20, 0.35, 0.45, 0.55, 0.65, 0.75, 0.90]
WAIST_EDGES  = [0.20, 0.35, 0.45, 0.55, 0.65, 0.75, 0.90]

df["fat_bin"]    = pd.cut(df["fat_score"],    bins=FAT_EDGES,    labels=False, right=False)
df["muscle_bin"] = pd.cut(df["muscle_score"], bins=MUSCLE_EDGES, labels=False, right=False)
df["hip_bin"]    = pd.cut(df["hip_score"],    bins=HIP_EDGES,    labels=False, right=False)
df["waist_bin"]  = pd.cut(df["waist_def_score"], bins=WAIST_EDGES, labels=False, right=False)

rng = np.random.default_rng(42)

selected_ids = set()

# ── Katman 1: fat × hip × waist grid, her gender için 1 satır ─────────────────
# Ana shape parametreleri — muscle ikincil, height nötr'e yakın olanı seç
for gender in ["male", "female"]:
    sub = df[df["gender"] == gender]
    for fb in range(len(FAT_EDGES) - 1):
        for hb in range(len(HIP_EDGES) - 1):
            for wb in range(len(WAIST_EDGES) - 1):
                cell = sub[(sub["fat_bin"] == fb) &
                           (sub["hip_bin"] == hb) &
                           (sub["waist_bin"] == wb)]
                if len(cell) == 0:
                    continue
                # height_score'u nötre en yakın olanı seç (shape izolasyonu)
                h_center = 0.4284 if gender == "male" else 0.2954
                idx = (cell["height_score"] - h_center).abs().idxmin()
                selected_ids.add(idx)

print(f"Katman 1 (fat×hip×waist grid): {len(selected_ids)} satır")

# ── Katman 2: fat × muscle grid, her gender için 1 satır ─────────────────────
# Kas etkisini izole et: hip ve waist orta değerlere yakın olanı seç
before = len(selected_ids)
for gender in ["male", "female"]:
    sub = df[df["gender"] == gender]
    for fb in range(len(FAT_EDGES) - 1):
        for mb in range(len(MUSCLE_EDGES) - 1):
            cell = sub[(sub["fat_bin"] == fb) &
                       (sub["muscle_bin"] == mb) &
                       (sub["hip_bin"].between(2, 3)) &    # hip_score ~0.45–0.65
                       (sub["waist_bin"].between(2, 3))]   # waist_def ~0.45–0.65
            if len(cell) == 0:
                # eşiği genişlet
                cell = sub[(sub["fat_bin"] == fb) &
                           (sub["muscle_bin"] == mb)]
            if len(cell) == 0:
                continue
            h_center = 0.4284 if gender == "male" else 0.2954
            idx = (cell["height_score"] - h_center).abs().idxmin()
            selected_ids.add(idx)

print(f"Katman 2 (+fat×muscle grid): {len(selected_ids)} satır (+{len(selected_ids)-before})")

# ── Katman 3: somatotip × fat_band kapsamı ────────────────────────────────────
# Her somatotip × fat_band × gender için en az 5 satır
FAT_BAND_EDGES = [0.00, 0.15, 0.35, 0.60, 1.01]
FAT_BAND_LABELS = ["lean", "normal", "overweight", "obese"]
df["fat_band"] = pd.cut(df["fat_score"], bins=FAT_BAND_EDGES,
                        labels=FAT_BAND_LABELS, right=False)

before = len(selected_ids)
for gender in ["male", "female"]:
    for soma in df["somatotype"].unique():
        for band in FAT_BAND_LABELS:
            cell = df[(df["gender"] == gender) &
                      (df["somatotype"] == soma) &
                      (df["fat_band"] == band)]
            if len(cell) == 0:
                continue
            n = min(5, len(cell))
            # shape score proxy: hip_score + waist_def_score uzaklığı merkeze
            cell = cell.copy()
            cell["_extremity"] = ((cell["hip_score"] - 0.5).abs() +
                                  (cell["waist_def_score"] - 0.5).abs())
            # en "uç" karakterleri al — somatotip özelliklerini en net yansıtanlar
            picks = cell.nlargest(n, "_extremity").index
            selected_ids.update(picks)

print(f"Katman 3 (+somatotip×fat_band): {len(selected_ids)} satır (+{len(selected_ids)-before})")

# ── Katman 4: training_pattern kapsamı (athletic gruplar) ─────────────────────
before = len(selected_ids)
for gender in ["male", "female"]:
    for pattern in ["upper_dominant", "lower_dominant", "push_dominant", "pull_dominant"]:
        for fb in [0, 1]:  # lean athletic: fat 0–0.20
            cell = df[(df["gender"] == gender) &
                      (df["training_pattern"] == pattern) &
                      (df["fat_bin"] == fb)]
            if len(cell) == 0:
                continue
            picks = cell.sample(min(3, len(cell)), random_state=42).index
            selected_ids.update(picks)

print(f"Katman 4 (+training_pattern): {len(selected_ids)} satır (+{len(selected_ids)-before})")

# ── Katman 5: segment spread extremes ─────────────────────────────────────────
# Length score'ların ölçümlere etkisini görmek için — uzun/kısa kombinasyonlar
before = len(selected_ids)
for gender in ["male", "female"]:
    sub = df[df["gender"] == gender].copy()
    seg_cols = ["chest_height_score", "hip_length_score", "thigh_length_score",
                "lower_leg_length_score", "upper_arm_length_score",
                "forearm_length_score", "neck_length_score"]
    sub["_seg_mean"] = sub[seg_cols].mean(axis=1)
    # çok düşük ve çok yüksek segment ortalamalı örnekler
    picks = (sub.nsmallest(15, "_seg_mean").index.tolist() +
             sub.nlargest(15, "_seg_mean").index.tolist())
    selected_ids.update(picks)

print(f"Katman 5 (+segment extremes): {len(selected_ids)} satır (+{len(selected_ids)-before})")

# ── Sonuç ──────────────────────────────────────────────────────────────────────
probe = df.loc[sorted(selected_ids)].drop(
    columns=["fat_bin", "muscle_bin", "hip_bin", "waist_bin", "fat_band"],
    errors="ignore"
)

print(f"\n=== Kalibrasyon alt kümesi: {len(probe)} satır ===")
print(f"Gender: {probe['gender'].value_counts().to_dict()}")
print(f"Somatotip: {probe['somatotype'].value_counts().to_dict()}")
print(f"Group: {probe['group'].value_counts().to_dict()}")
print(f"\nfat_score      : [{probe['fat_score'].min():.3f}, {probe['fat_score'].max():.3f}]")
print(f"muscle_score   : [{probe['muscle_score'].min():.3f}, {probe['muscle_score'].max():.3f}]")
print(f"hip_score      : [{probe['hip_score'].min():.3f}, {probe['hip_score'].max():.3f}]")
print(f"waist_def_score: [{probe['waist_def_score'].min():.3f}, {probe['waist_def_score'].max():.3f}]")

probe.to_csv(OUTPUT, index=False)
print(f"\nKaydedildi: {OUTPUT}")

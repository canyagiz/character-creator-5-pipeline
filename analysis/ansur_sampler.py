"""
ansur_sampler.py
ANSUR II'den gerçek satırları coverage-maximizing (maximin) örnekleme ile seçer.

Sentetik veri üretmez — sadece gerçek insan ölçümlerini seçer.
Her ölçümün diğer ölçümlerle tüm kombinasyonlarını kapsayacak şekilde
normalize uzayda birbirinden en uzak noktaları seçer (maximin LHS hybrid).

Çıktı: logs/ansur_samples_10k.csv
Çalıştır: python analysis/ansur_sampler.py
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

ANSUR_F = str(_ROOT / "docs" / "ansur2" / "ANSUR_II_FEMALE_Public.csv")
ANSUR_M = str(_ROOT / "docs" / "ansur2" / "ANSUR_II_MALE_Public.csv")
OUT_CSV = str(_ROOT / "logs" / "ansur_samples_10k.csv")
N_EACH  = None   # None = tum gercek satirlar, imputasyon yok

os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

# ANSUR kolon → CC5 ölçüm adı (mm → cm)
MAPPING = {
    "stature":                    "height_cm",
    "neckcircumference":          "neck_circ_cm",
    "chestcircumference":         "chest_circ_cm",
    "waistcircumference":         "waist_circ_cm",
    "buttockcircumference":       "hip_circ_cm",
    "thighcircumference":         "mid_thigh_circ_cm",
    "calfcircumference":          "calf_circ_cm",
    "bicepscircumferenceflexed":  "bicep_circ_cm",
    "forearmcircumferenceflexed": "forearm_circ_cm",
    "wristcircumference":         "wrist_circ_cm",
    "bideltoidbreadth":           "shoulder_width_cm",
    "hipbreadth":                 "hip_width_cm",
    "shoulderelbowlength":        "upper_arm_length_cm",
    "radialestylionlength":       "forearm_length_cm",
    "trochanterionheight":        "trochanterion_height_cm",
    "tibialheight":               "tibial_height_cm",
    "weightkg":                   "weight_kg",
}

ANSUR_COLS = list(MAPPING.keys())
CC5_COLS   = list(MAPPING.values())

def maximin_sample(df_raw, n, gender, seed=42):
    """
    Gerçek ANSUR satırlarından n adet seçer.
    Yöntem: normalized uzayda maximin greedy seçim.
      - Tüm kolonları [0,1]'e normalize et (min-max)
      - İlk noktayı rastgele seç
      - Her adımda: mevcut seçililere olan minimum mesafesi en büyük olan
        satırı ekle
      - n'den fazla satır isteniyor ve ANSUR'da yeterli yoksa:
        kalan kısmı uniform olarak tekrarla (oversample)
    """
    rng = np.random.default_rng(seed)

    # mm → cm, ilgili kolonları al
    unit_div = {c: (10.0 if c != "weightkg" else 10.0) for c in ANSUR_COLS}
    data = df_raw[ANSUR_COLS].dropna().copy()
    for c in ANSUR_COLS:
        data[c] = data[c] / unit_div[c]
    data = data.reset_index(drop=True)

    n_avail = len(data)
    select_n = n_avail if n is None else min(n, n_avail)
    print(f"  {gender}: {n_avail} gercek satir, {select_n} seciliyor")

    if select_n == n_avail:
        # Tumu kullan, siralama maximin ile
        result = data.copy()
    else:
        # Normalize [0,1]
        col_min = data.min()
        col_max = data.max()
        norm_arr = ((data - col_min) / (col_max - col_min + 1e-9)).values.astype(np.float32)

        selected_idx = []
        first = int(rng.integers(0, n_avail))
        selected_idx.append(first)

        min_dists = np.sum((norm_arr - norm_arr[first]) ** 2, axis=1).astype(np.float32)

        for _ in range(select_n - 1):
            next_idx = int(np.argmax(min_dists))
            selected_idx.append(next_idx)
            new_dists = np.sum((norm_arr - norm_arr[next_idx]) ** 2, axis=1)
            min_dists = np.minimum(min_dists, new_dists)

        result = data.iloc[selected_idx].copy()

    result = result.reset_index(drop=True)
    result.columns = CC5_COLS
    result["gender"] = gender
    return result


# ── Ana akış ──────────────────────────────────────────────────────────────────
print("ANSUR II yukleniyor...")
fem = pd.read_csv(ANSUR_F, encoding="latin-1")
mal = pd.read_csv(ANSUR_M, encoding="latin-1")
print(f"  Female: {len(fem)} satir | Male: {len(mal)} satir")

print()
df_f = maximin_sample(fem, N_EACH, "female", seed=42)
df_m = maximin_sample(mal, N_EACH, "male",   seed=43)

# Kadin-erkek sirasyla interleave et (f0,m0,f1,m1,...), artan erkekler sona
n_f, n_m = len(df_f), len(df_m)
n_pairs  = min(n_f, n_m)
pairs    = [row for i in range(n_pairs) for row in (df_f.iloc[i], df_m.iloc[i])]
extras   = [df_m.iloc[i] for i in range(n_pairs, n_m)] if n_m > n_f \
      else [df_f.iloc[i] for i in range(n_pairs, n_f)]
df_all   = pd.DataFrame(pairs + extras).reset_index(drop=True)
df_all.insert(0, "char_id", [f"ansur_{i:05d}" for i in range(len(df_all))])

# ── Özet ─────────────────────────────────────────────────────────────────────
print(f"\n=== SONUC ===")
print(f"Toplam: {len(df_all)} satir ({len(df_f)} female, {len(df_m)} male)")
print()
print("Female ölçüm özeti (cm):")
print(df_all[df_all.gender=="female"][CC5_COLS[:10]].describe().round(1).to_string())
print()
print("Male ölçüm özeti (cm):")
print(df_all[df_all.gender=="male"][CC5_COLS[:10]].describe().round(1).to_string())

df_all.to_csv(OUT_CSV, index=False, encoding="utf-8")
print(f"\nKaydedildi: {OUT_CSV}")
print(f"Kolonlar: {list(df_all.columns)}")

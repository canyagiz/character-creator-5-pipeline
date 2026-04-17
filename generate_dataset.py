"""
Dataset generator — Synthetic Anthropometric Dataset v1.0
Spec: dataset_spec.docx
Çıktı: dataset.csv  (30,000 satır)
Bağımlılık: numpy, pandas, scipy
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc

TOTAL  = 30_000
SEED   = 42
OUTPUT = r"C:\Users\aliya\workspace\cc5-scripts\dataset.csv"

rng = np.random.default_rng(SEED)

# ── Spec tabloları ────────────────────────────────────────────────────────────

GROUPS = {
    "underweight":    {"alloc": 0.10, "fat": (0.00, 0.15), "muscle": (0.00, 0.20)},
    "normal":         {"alloc": 0.25, "fat": (0.16, 0.35), "muscle": (0.10, 0.30)},
    "overweight":     {"alloc": 0.25, "fat": (0.36, 0.60), "muscle": (0.15, 0.35)},
    "obese":          {"alloc": 0.15, "fat": (0.61, 1.00), "muscle": (0.15, 0.35)},
    "athletic_lean":  {"alloc": 0.15, "fat": (0.05, 0.15), "muscle": (0.40, 0.65)},
    "athletic_hyper": {"alloc": 0.10, "fat": (0.05, 0.15), "muscle": (0.66, 1.00)},
}

LENGTH_SCORES = ["chest_height_score", "hip_length_score", "thigh_length_score", "lower_leg_length_score",
                 "upper_arm_length_score", "forearm_length_score", "neck_length_score"]

AGE_STRATA = [
    {"lo": 14, "hi": 18, "alloc": 0.15},
    {"lo": 19, "hi": 29, "alloc": 0.50},
    {"lo": 30, "hi": 40, "alloc": 0.35},
]

# training_pattern: sadece athletic_lean ve athletic_hyper için uygulanır
# diğer gruplar her zaman "balanced"
TRAINING_PATTERNS = ["balanced", "upper_dominant", "lower_dominant", "push_dominant", "pull_dominant"]
TRAINING_ALLOC    = [0.45,       0.20,             0.15,             0.12,             0.08]

ATHLETIC_GROUPS = {"athletic_lean", "athletic_hyper"}

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def distribute(total, weights):
    """N'i ağırlıklara göre dağıt; toplamın tam eşit çıkmasını garantiler."""
    cumulative = 0
    ns = []
    w_sum = sum(weights)
    for i, w in enumerate(weights):
        if i == len(weights) - 1:
            ns.append(total - cumulative)
        else:
            n = round(w / w_sum * total)
            ns.append(n)
            cumulative += n
    return ns


def sample_ages(group, n):
    # AGE-02: athletic_hyper → age >= 18
    valid = AGE_STRATA if group != "athletic_hyper" else [s for s in AGE_STRATA if s["lo"] >= 18]
    counts = distribute(n, [s["alloc"] for s in valid])

    ages = np.concatenate([
        rng.integers(s["lo"], s["hi"] + 1, c)
        for s, c in zip(valid, counts)
    ])
    rng.shuffle(ages)
    return ages


def generate_cell(group, gender, n):
    g = GROUPS[group]

    # LHS: fat_score, muscle_score, height_score + 7 segment score
    lhs = qmc.LatinHypercube(d=10, seed=int(rng.integers(1_000_000))).random(n)
    fat_lo, fat_hi = g["fat"]
    mus_lo, mus_hi = g["muscle"]
    fat               = fat_lo + lhs[:, 0] * (fat_hi - fat_lo)
    muscle            = mus_lo + lhs[:, 1] * (mus_hi - mus_lo)
    height_hs         = lhs[:, 2].copy()
    chest_hs          = lhs[:, 3].copy()
    hip_hs            = lhs[:, 4].copy()
    thigh_hs          = lhs[:, 5].copy()
    lower_leg_hs      = lhs[:, 6].copy()
    upper_arm_hs      = lhs[:, 7].copy()
    forearm_hs        = lhs[:, 8].copy()
    neck_hs           = lhs[:, 9].copy()

    ages = sample_ages(group, n)

    # ── Yaş-morfoloji kısıtları (hard rules) ─────────────────────────────────
    m18 = ages < 18   # AGE-03
    m16 = ages < 16   # AGE-01, AGE-04

    for seg in [height_hs, chest_hs, hip_hs, thigh_hs, lower_leg_hs, upper_arm_hs, forearm_hs, neck_hs]:
        seg[m18] = np.minimum(seg[m18], 0.80)
    fat[m16]    = np.minimum(fat[m16],    0.70)
    muscle[m16] = np.minimum(muscle[m16], 0.40)

    # training_pattern: athletic gruplarda dağılımlı, diğerlerinde "balanced"
    if group in ATHLETIC_GROUPS:
        patterns = rng.choice(TRAINING_PATTERNS, size=n, p=TRAINING_ALLOC)
    else:
        patterns = np.full(n, "balanced")

    return pd.DataFrame({
        "gender":                 gender,
        "age":                    ages,
        "group":                  group,
        "fat_score":              fat.round(4),
        "muscle_score":           muscle.round(4),
        "height_score":           height_hs.round(4),
        "chest_height_score":     chest_hs.round(4),
        "hip_length_score":       hip_hs.round(4),
        "thigh_length_score":     thigh_hs.round(4),
        "lower_leg_length_score":  lower_leg_hs.round(4),
        "upper_arm_length_score":  upper_arm_hs.round(4),
        "forearm_length_score":    forearm_hs.round(4),
        "neck_length_score":       neck_hs.round(4),
        "height_cm":               "",
        "training_pattern":       patterns,
    })


# ── Ana üretim döngüsü ────────────────────────────────────────────────────────

chunks = []

for group, g_cfg in GROUPS.items():
    group_n   = round(g_cfg["alloc"] * TOTAL)
    gender_ns = distribute(group_n, [0.5, 0.5])

    for gender, gn in zip(["male", "female"], gender_ns):
        chunks.append(generate_cell(group, gender, gn))

df = pd.concat(chunks, ignore_index=True)

# Karıştır ve char_id ata
df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
df.insert(0, "char_id", [f"char_{i+1:05d}" for i in range(len(df))])

df.to_csv(OUTPUT, index=False)

# ── Dağılım denetimi ──────────────────────────────────────────────────────────

target = {
    "underweight": 3000, "normal": 7500, "overweight": 7500,
    "obese": 4500, "athletic_lean": 4500, "athletic_hyper": 3000,
}

print(f"\nTotal: {len(df)} rows -> {OUTPUT}")

print("\n-- Group -----------------------------------")
for g, cnt in df["group"].value_counts().sort_index().items():
    diff = cnt - target[g]
    print(f"  {g:<18} {cnt:>5}  (target {target[g]:>5}, diff {diff:+d})")

print("\n-- Gender ----------------------------------")
for v, cnt in df["gender"].value_counts().items():
    print(f"  {v:<10} {cnt:>5}")

print("\n-- Age strata -------------------------------")
bins   = [13, 18, 29, 40]
labels = ["adolescent(14-18)", "young_adult(19-29)", "adult(30-40)"]
strata = pd.cut(df["age"], bins=bins, labels=labels)
for l, cnt in strata.value_counts().sort_index().items():
    print(f"  {l}  {cnt:>5}  ({cnt/TOTAL*100:.1f}%)")

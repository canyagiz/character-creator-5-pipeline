"""
generate_dataset_10k.py — Her somatotipten esit 2K (toplam 10K) dataset.

Yaklasim:
  1. Kalibrasyon modellerini fit et (slider -> gercek cm)
  2. Her somatotip icin slider uzayinin hedef bolgesinde buyuk aday havuzu uret
  3. Adaylari siniflandir, sadece hedef somatotipe uyanlardan 2K sec
  4. Kalan kolonlari doldur (segment, yas, training_pattern, group)
  5. Kaydet: dataset_10k.csv

Calistir: python generate_dataset_10k.py
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc, truncnorm
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

CALIB_CSV = r"C:\Users\aliya\workspace\cc5-scripts\analysis\calib_merged.csv"
OUTPUT    = r"C:\Users\aliya\workspace\cc5-scripts\dataset_10k.csv"

N_PER_SOMA = 2_000   # her somatotipten
SEED       = 42
rng        = np.random.default_rng(SEED)

FEATURES = ["fat_score", "muscle_score", "hip_score", "waist_def_score", "height_score"]
TARGETS  = ["chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
            "mid_thigh_circ_cm", "bicep_circ_cm", "neck_circ_cm"]

MEAS_RANGES = {
    "male": {
        "chest_circ_cm":     (80,  160),
        "waist_circ_cm":     (65,  145),
        "hip_circ_cm":       (85,  160),
        "mid_thigh_circ_cm": (42,  105),
        "bicep_circ_cm":     (18,   52),
        "neck_circ_cm":      (29,   60),
    },
    "female": {
        "chest_circ_cm":     (75,  150),
        "waist_circ_cm":     (60,  145),
        "hip_circ_cm":       (80,  160),
        "mid_thigh_circ_cm": (42,  108),
        "bicep_circ_cm":     (18,   50),
        "neck_circ_cm":      (28,   58),
    },
}

HEIGHT_PARAMS = {
    "male":   {"center": 0.4284, "std": 0.062, "lo": 0.20, "hi": 0.735},
    "female": {"center": 0.2954, "std": 0.062, "lo": 0.20, "hi": 0.561},
}

# Nadir somatotipler icin hedefli slider aralik kisitlari.
# None = kisitsiz (tam [fat:0-1, muscle:0-1, hip:0.2-0.9, waist_def:0.2-0.9])
SOMA_SLIDER_HINTS = {
    "apple": {
        "fat":       (0.42, 1.00),   # waist/hip >= 0.90 icin yuksek fat gerekli
        "muscle":    (0.00, 1.00),
        "hip":       (0.20, 0.90),
        "waist_def": (0.20, 0.90),
    },
    "v_shape": {
        "fat":       (0.00, 0.25),   # fat < 0.25 sarti
        "muscle":    (0.20, 1.00),   # kadinlarda muscle > 0.60 gerekecek
        "hip":       (0.20, 0.44),   # hip_score < 0.45 sarti
        "waist_def": (0.20, 0.90),
    },
    "hourglass": {
        "fat":       (0.00, 0.13),   # waist/hip < 0.83 icin dusuk fat
        "muscle":    (0.00, 1.00),
        "hip":       (0.48, 0.57),   # dar hourglass bandi
        "waist_def": (0.70, 0.90),   # yuksek bel tanimi gerekli
    },
    "pear": {
        "fat":       (0.00, 0.70),
        "muscle":    (0.00, 0.64),   # muscle < 0.65 sarti
        "hip":       (0.58, 0.90),   # hip_score >= 0.58 sarti
        "waist_def": (0.20, 0.90),
    },
    "rectangle": {
        "fat":       (0.00, 1.00),
        "muscle":    (0.00, 1.00),
        "hip":       (0.20, 0.90),
        "waist_def": (0.20, 0.90),
    },
}

# Nadir somatotipler icin daha buyuk aday havuzu gerekli
POOL_SIZE = {
    "apple":     20_000,
    "v_shape":   20_000,
    "hourglass": 40_000,   # cok nadir — buyuk havuz
    "pear":      20_000,
    "rectangle": 30_000,
}

GENDERS = ["male", "female"]

# ── Model fit ─────────────────────────────────────────────────────────────────
print("Kalibrasyon modelleri fit ediliyor...")
calib = pd.read_csv(CALIB_CSV)
models = {}
for gender in GENDERS:
    sub = calib[calib["gender"] == gender]
    X   = sub[FEATURES].values
    models[gender] = {}
    for t in TARGETS:
        y = sub[t].values
        m = make_pipeline(PolynomialFeatures(degree=2, include_bias=False), Ridge(alpha=1.0))
        m.fit(X, y)
        models[gender][t] = m
print("  Done.")

# ── Hedefli aday uretimi ──────────────────────────────────────────────────────
def generate_targeted(gender, n, hints):
    hp  = HEIGHT_PARAMS[gender]
    a   = (hp["lo"] - hp["center"]) / hp["std"]
    b   = (hp["hi"] - hp["center"]) / hp["std"]
    lhs = qmc.LatinHypercube(d=5, seed=int(rng.integers(1_000_000))).random(n)

    f_lo, f_hi = hints["fat"]
    m_lo, m_hi = hints["muscle"]
    h_lo, h_hi = hints["hip"]
    w_lo, w_hi = hints["waist_def"]

    fat       = f_lo + lhs[:, 0] * (f_hi - f_lo)
    muscle    = m_lo + lhs[:, 1] * (m_hi - m_lo)
    hip_score = h_lo + lhs[:, 2] * (h_hi - h_lo)
    waist_def = w_lo + lhs[:, 3] * (w_hi - w_lo)
    height_s  = truncnorm.ppf(
        np.clip(lhs[:, 4], 0.001, 0.999), a, b,
        loc=hp["center"], scale=hp["std"]
    )

    X     = np.stack([fat, muscle, hip_score, waist_def, height_s], axis=1)
    mr    = MEAS_RANGES[gender]
    preds = {}
    for t in TARGETS:
        raw = models[gender][t].predict(X)
        preds[t] = np.clip(raw, *mr[t])

    return pd.DataFrame({
        "gender":          gender,
        "fat_score":       fat,
        "muscle_score":    muscle,
        "hip_score":       hip_score,
        "waist_def_score": waist_def,
        "height_score":    height_s,
        **{t: preds[t] for t in TARGETS},
    })

# ── Siniflandirma ─────────────────────────────────────────────────────────────
def classify_somatotype(df):
    wh        = (df["waist_circ_cm"] / df["hip_circ_cm"]).values
    hip_score = df["hip_score"].values
    waist_def = df["waist_def_score"].values
    fat       = df["fat_score"].values
    muscle    = df["muscle_score"].values
    gender    = df["gender"].values

    labels = []
    for i in range(len(df)):
        if wh[i] >= 0.90:
            labels.append("apple")
        elif hip_score[i] < 0.45 and fat[i] < 0.25 and (gender[i] == "male" or muscle[i] > 0.60):
            labels.append("v_shape")
        elif 0.48 <= hip_score[i] <= 0.57 and waist_def[i] >= 0.70 and wh[i] < 0.83:
            labels.append("hourglass")
        elif hip_score[i] >= 0.58 and wh[i] < 0.89 and muscle[i] < 0.65:
            labels.append("pear")
        else:
            labels.append("rectangle")
    return np.array(labels)

# ── Olcum uzayinda cesitli secim ──────────────────────────────────────────────
def diverse_select(df, n_target):
    """Waist quantile bins uzerinden cesitli secim; eksik kalirsa rastgele tamamla."""
    N_BINS   = 40
    PER_BIN  = max(1, (n_target * 2) // N_BINS)   # overkill, fallback tamamlar

    df = df.copy().reset_index(drop=True)
    df["_wq"] = pd.qcut(df["waist_circ_cm"], q=N_BINS, labels=False, duplicates="drop")

    used = set()
    sel  = []
    for _, grp in df.groupby("_wq", observed=True):
        n = min(PER_BIN, len(grp))
        if len(grp) <= n:
            chosen = grp
        else:
            grp_s = grp.sort_values(["hip_circ_cm", "bicep_circ_cm"])
            step  = len(grp_s) / n
            chosen = pd.DataFrame([grp_s.iloc[int(i * step)] for i in range(n)])
        sel.append(chosen)
        used.update(chosen.index)

    result = pd.concat(sel, ignore_index=True)

    if len(result) < n_target:
        remaining = df[~df.index.isin(used)]
        extra = remaining.sample(
            min(n_target - len(result), len(remaining)), random_state=SEED
        )
        result = pd.concat([result, extra], ignore_index=True)

    if len(result) > n_target:
        result = result.sample(n_target, random_state=SEED)

    return result.drop(columns=["_wq"])

# ── Kalan kolonlar ────────────────────────────────────────────────────────────
AGE_STRATA = [
    {"lo": 14, "hi": 18, "alloc": 0.15},
    {"lo": 19, "hi": 29, "alloc": 0.50},
    {"lo": 30, "hi": 40, "alloc": 0.35},
]
TRAINING_PATTERNS = ["balanced", "upper_dominant", "lower_dominant", "push_dominant", "pull_dominant"]
TRAINING_ALLOC    = [0.45, 0.20, 0.15, 0.12, 0.08]

def derive_group(fat, muscle):
    groups = []
    for f, m in zip(fat, muscle):
        if f <= 0.15:
            if m >= 0.66:
                groups.append("athletic_hyper")
            elif m >= 0.40:
                groups.append("athletic_lean")
            else:
                groups.append("underweight")
        elif f <= 0.35:
            groups.append("normal")
        elif f <= 0.60:
            groups.append("overweight")
        else:
            groups.append("obese")
    return np.array(groups)

def sample_ages(n, groups):
    ages = np.zeros(n, dtype=int)
    for i, group in enumerate(groups):
        valid   = AGE_STRATA if group != "athletic_hyper" else [s for s in AGE_STRATA if s["lo"] >= 18]
        weights = np.array([s["alloc"] for s in valid])
        weights /= weights.sum()
        s = valid[rng.choice(len(valid), p=weights)]
        ages[i] = rng.integers(s["lo"], s["hi"] + 1)
    return ages

def sample_segments(n):
    SEG_MAX_DEV = 0.30
    lhs    = qmc.LatinHypercube(d=7, seed=int(rng.integers(1_000_000))).random(n)
    segs   = lhs
    s_min  = segs.min(axis=1, keepdims=True)
    s_max  = segs.max(axis=1, keepdims=True)
    spread = s_max - s_min
    center = (s_max + s_min) / 2
    scale  = np.where(spread > SEG_MAX_DEV, SEG_MAX_DEV / np.maximum(spread, 1e-9), 1.0)
    return np.clip(center + (segs - center) * scale, 0.0, 1.0)

# ── Ana uretim — somatotip bazli ─────────────────────────────────────────────
SOMATOTYPES = ["apple", "v_shape", "hourglass", "pear", "rectangle"]

all_chunks = []

for soma in SOMATOTYPES:
    hints    = SOMA_SLIDER_HINTS[soma]
    pool_n   = POOL_SIZE[soma]
    print(f"\n{soma.upper()} ({pool_n:,} aday / gender):")

    soma_pool = []
    for gender in GENDERS:
        cands = generate_targeted(gender, pool_n, hints)
        cands["_soma_pred"] = classify_somatotype(cands)
        matched = cands[cands["_soma_pred"] == soma].drop(columns=["_soma_pred"])
        print(f"  {gender}: {len(matched):,} / {pool_n:,} eslesme")
        soma_pool.append(matched)

    pool = pd.concat(soma_pool, ignore_index=True)
    print(f"  Toplam eslesen: {len(pool):,}  ->  {N_PER_SOMA:,} secilecek")

    if len(pool) < N_PER_SOMA:
        print(f"  UYARI: {soma} icin yeterli aday yok ({len(pool)} < {N_PER_SOMA}), tumunu aliyoruz")
        selected = pool
    else:
        selected = diverse_select(pool, N_PER_SOMA)

    n = len(selected)
    segs   = sample_segments(n)
    groups = derive_group(selected["fat_score"].values, selected["muscle_score"].values)
    ages   = sample_ages(n, groups)

    height_s = selected["height_score"].values.copy()
    height_s[ages < 18] = np.minimum(height_s[ages < 18], 0.80)

    is_athletic = np.isin(groups, ["athletic_lean", "athletic_hyper"])
    patterns    = np.where(
        is_athletic,
        rng.choice(TRAINING_PATTERNS, size=n, p=TRAINING_ALLOC),
        "balanced"
    )

    chunk = pd.DataFrame({
        "gender":                  selected["gender"].values,
        "age":                     ages,
        "group":                   groups,
        "somatotype":              soma,
        "fat_score":               selected["fat_score"].round(4).values,
        "muscle_score":            selected["muscle_score"].round(4).values,
        "height_score":            height_s.round(4),
        "chest_height_score":      segs[:, 0].round(4),
        "hip_length_score":        segs[:, 1].round(4),
        "thigh_length_score":      segs[:, 2].round(4),
        "lower_leg_length_score":  segs[:, 3].round(4),
        "upper_arm_length_score":  segs[:, 4].round(4),
        "forearm_length_score":    segs[:, 5].round(4),
        "neck_length_score":       segs[:, 6].round(4),
        "height_cm":               "",
        "training_pattern":        patterns,
        "hip_score":               selected["hip_score"].round(4).values,
        "waist_def_score":         selected["waist_def_score"].round(4).values,
        "chest_circ_pred_cm":      selected["chest_circ_cm"].round(1).values,
        "waist_circ_pred_cm":      selected["waist_circ_cm"].round(1).values,
        "hip_circ_pred_cm":        selected["hip_circ_cm"].round(1).values,
        "thigh_circ_pred_cm":      selected["mid_thigh_circ_cm"].round(1).values,
        "bicep_circ_pred_cm":      selected["bicep_circ_cm"].round(1).values,
        "neck_circ_pred_cm":       selected["neck_circ_cm"].round(1).values,
    })
    all_chunks.append(chunk)

# ── Birles, karistir, kaydet ──────────────────────────────────────────────────
df = pd.concat(all_chunks, ignore_index=True)
df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
df.insert(0, "char_id", [f"char_{i+1:05d}" for i in range(len(df))])

print(f"\n{'='*50}")
print(f"Toplam: {len(df)} satir")
print(f"\nSomatotip: {df['somatotype'].value_counts().to_dict()}")
print(f"\nGender: {df['gender'].value_counts().to_dict()}")
print(f"\nGender x Somatotip:")
print(df.groupby(["gender", "somatotype"]).size().unstack(fill_value=0))
print(f"\nGroup: {df['group'].value_counts().to_dict()}")

print("\nTahmin edilen olcum araliklari (somatotip x gender):")
for soma in SOMATOTYPES:
    sub_s = df[df["somatotype"] == soma]
    print(f"\n  {soma}:")
    for gender in GENDERS:
        sub = sub_s[sub_s["gender"] == gender]
        if len(sub) == 0:
            continue
        w = sub["waist_circ_pred_cm"]
        h = sub["hip_circ_pred_cm"]
        print(f"    {gender:<7} n={len(sub):4d}  "
              f"waist=[{w.min():.0f},{w.max():.0f}] mean={w.mean():.0f}  "
              f"hip=[{h.min():.0f},{h.max():.0f}] mean={h.mean():.0f}")

df.to_csv(OUTPUT, index=False)
print(f"\nKaydedildi: {OUTPUT}")

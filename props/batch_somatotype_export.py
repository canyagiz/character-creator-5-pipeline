"""
batch_somatotype_export.py — Somatotip gorsel dogrulama probe'u.
CC5 Script Editor'da calistir.

Her somatotip icin 10 karakter secer; secimde maksimum varyasyon saglanir:
  - Her iki cinsiyet temsil edilir
  - Fat araligi boyunca yayilim (lean / normal / overweight / obese)
  - hip_score ve waist_def_score degerleri cesitli

Toplam: 5 somatotip x 10 = 50 karakter

Cikti:
  fbx_export/<char_id>.fbx
  logs/somatotype_probe.csv
"""

import RLPy
import csv
import gc
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from cc5_helpers import compute_all_weights, ALL_MORPHS, PROJECT_FILES

DATASET_CSV = str(_ROOT / "dataset.csv")
PREDS_CSV   = str(_ROOT / "analysis" / "dataset_with_preds.csv")
OUTPUT_DIR  = str(_ROOT / "fbx_export")
LOG_DIR     = str(_ROOT / "logs")
PROBE_CSV   = os.path.join(LOG_DIR, "somatotype_probe.csv")
OVERWRITE   = True
N_PER_SOMA  = 10

SOMATOTYPES = ["hourglass", "pear", "rectangle", "apple", "v_shape"]

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ── Veri yukle ────────────────────────────────────────────────────────────────
with open(DATASET_CSV, encoding="utf-8") as f:
    dataset_rows = {r["char_id"]: r for r in csv.DictReader(f)}

with open(PREDS_CSV, encoding="utf-8") as f:
    preds_list = list(csv.DictReader(f))
preds = {r["char_id"]: r for r in preds_list}

# ── Varyasyonlu secim ─────────────────────────────────────────────────────────
# Strateji: fat_score x gender sloklarini doldur, bos kalanlari en benzersizle tamamla

FAT_SLOTS = [
    (0.00, 0.12),
    (0.12, 0.25),
    (0.25, 0.40),
    (0.40, 0.60),
    (0.60, 1.01),
]

def select_diverse(soma, n):
    """Somatotip icin n adet cesitli karakter sec."""
    candidates = [r for r in preds_list if r.get("somatotype") == soma]
    if not candidates:
        return []

    chosen = []
    chosen_ids = set()

    # Once fat x gender slotlarini doldur (max kaplama)
    for fat_lo, fat_hi in FAT_SLOTS:
        for gender in ["female", "male"]:
            slot = [
                r for r in candidates
                if fat_lo <= float(r["fat_score"]) < fat_hi
                and r["gender"] == gender
                and r["char_id"] not in chosen_ids
            ]
            if not slot:
                continue
            # Slot icinde en "tipik" ornegi sec: soma skoruna gore
            best = max(slot, key=lambda r: _soma_score(soma, r))
            chosen.append(best["char_id"])
            chosen_ids.add(best["char_id"])
            if len(chosen) >= n:
                break
        if len(chosen) >= n:
            break

    # Hala eksikse kalan adaylardan en farkli olani ekle (greedy max-min)
    if len(chosen) < n:
        remaining = [r for r in candidates if r["char_id"] not in chosen_ids]
        import math

        def dist(r, chosen_list):
            f  = float(r["fat_score"])
            hs = float(r["hip_score"])
            wd = float(r["waist_def_score"])
            ms = float(r["muscle_score"])
            min_d = float("inf")
            for cid in chosen_list:
                c  = preds[cid]
                d = math.sqrt(
                    (f  - float(c["fat_score"]))**2 +
                    (hs - float(c["hip_score"]))**2 +
                    (wd - float(c["waist_def_score"]))**2 +
                    (ms - float(c["muscle_score"]))**2
                )
                if d < min_d:
                    min_d = d
            return min_d

        while len(chosen) < n and remaining:
            best = max(remaining, key=lambda r: dist(r, chosen))
            chosen.append(best["char_id"])
            chosen_ids.add(best["char_id"])
            remaining = [r for r in remaining if r["char_id"] not in chosen_ids]

    return chosen[:n]


def _soma_score(soma, row):
    wh = float(row["_wst_hip"])
    hc = float(row["_hip_chest"])
    hs = float(row["hip_score"])
    wd = float(row["waist_def_score"])
    if soma == "apple":
        return wh
    if soma == "pear":
        return hs - wh
    if soma == "v_shape":
        return 1.0 / hc if float(hc) > 0 else 0
    if soma == "hourglass":
        return (1.0 - abs(1.0 - hc)) + (1.0 - wh)
    return -(abs(wh - 0.872) + abs(hc - 1.12))


# ── Probe listesi olustur ─────────────────────────────────────────────────────
probe_rows = []
for soma in SOMATOTYPES:
    ids = select_diverse(soma, N_PER_SOMA)
    print(f"\n{soma.upper()} ({len(ids)} karakter):")
    for cid in ids:
        row  = dataset_rows[cid]
        pred = preds[cid]
        print(f"  {cid}  gender={row['gender']:<7} fat={float(row['fat_score']):.2f} "
              f"hip_s={float(row['hip_score']):.2f} wd={float(row['waist_def_score']):.2f} "
              f"hip/chest={float(pred['_hip_chest']):.3f} waist/hip={float(pred['_wst_hip']):.3f}")
        probe_rows.append({**row, "_soma": soma})

print(f"\nToplam probe: {len(probe_rows)} karakter")

# Probe CSV kaydet
fieldnames = list(list(dataset_rows.values())[0].keys()) + ["_soma"]
with open(PROBE_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(probe_rows)
print(f"Probe listesi kaydedildi: {PROBE_CSV}")

# ── FBX export ────────────────────────────────────────────────────────────────
fbx_setting = RLPy.RExportFbxSetting()
fbx_setting.SetOption(RLPy.EExportFbxOptions__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2__None)
fbx_setting.SetOption2(RLPy.EExportFbxOptions2_ResetBoneScale)
fbx_setting.EnableExportMotion(False)
fbx_setting.EnableBakeSubdivision(False)

done = 0
failed = 0
current_gender = None

for row in probe_rows:
    char_id  = row["char_id"]
    gender   = row["gender"]
    fbx_path = os.path.join(OUTPUT_DIR, f"{char_id}.fbx")

    if not OVERWRITE and os.path.exists(fbx_path):
        print(f"  SKIP {char_id}")
        continue

    if gender != current_gender:
        RLPy.RFileIO.LoadFile(PROJECT_FILES[gender])
        current_gender = gender
        print(f"  [project] {gender} yuklendi")

    try:
        avatar  = RLPy.RScene.GetAvatars()[0]
        shaping = avatar.GetAvatarShapingComponent()

        weights = compute_all_weights(
            fat                    = float(row["fat_score"]),
            muscle                 = float(row["muscle_score"]),
            height_score           = float(row["height_score"]),
            chest_height_score     = float(row["chest_height_score"]),
            hip_length_score       = float(row["hip_length_score"]),
            thigh_length_score     = float(row["thigh_length_score"]),
            lower_leg_length_score = float(row["lower_leg_length_score"]),
            upper_arm_length_score = float(row["upper_arm_length_score"]),
            forearm_length_score   = float(row["forearm_length_score"]),
            neck_length_score      = float(row["neck_length_score"]),
            pattern                = row.get("training_pattern", "balanced"),
            gender                 = gender,
            hip_score              = float(row.get("hip_score") or 0.5),
            waist_def_score        = float(row.get("waist_def_score") or 0.5),
        )

        for mid in ALL_MORPHS:
            shaping.SetShapingMorphWeight(mid, 0.0)
        for mid, w in weights.items():
            shaping.SetShapingMorphWeight(mid, w)

        RLPy.RScene.SelectObject(avatar)
        RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, fbx_setting)

        size = os.path.getsize(fbx_path) if os.path.exists(fbx_path) else -1
        if size < 1000:
            raise RuntimeError(f"FBX cok kucuk ({size} bytes)")

        done += 1
        print(f"  OK  {char_id} | {row['_soma']:<12} fat={float(row['fat_score']):.2f} {gender}")

    except Exception as e:
        failed += 1
        print(f"  HATA {char_id}: {e}")

    finally:
        try:
            del shaping, avatar
        except NameError:
            pass
        gc.collect()

print(f"\n=== TAMAMLANDI: {done} OK, {failed} hata ===")
print(f"Simdi pipeline.py'yi baslat: python pipeline.py --debug")

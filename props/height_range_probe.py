"""
Height Range Probe
height_score [0.0 → 1.0] aralığında gerçek boy (cm) ölçer.
Segment score'lar 0.5 (nötr) sabit tutulur — sadece height_score değişir.
CC5 Script Editor'da çalıştır (Male / Aaron projesiyle).
"""

import RLPy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from cc5_helpers import (
    PROJECT_FILES, ALL_MORPHS,
    M_CHEST_HEIGHT, M_HIP_LENGTH, M_THIGH_LENGTH, M_LOWER_LEG_LENGTH,
    M_NECK_LENGTH, M_UPPER_ARM_LENGTH, M_FOREARM_LENGTH,
    segment_weight,
)

LOG_PATH    = str(_ROOT / "logs" / "height_range_probe.log")
TEST_SCORES = [0.0, 0.10, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.75, 1.0]
SEG_NEUTRAL = 0.5  # tüm segment score'lar nötr

HEIGHT_MORPHS = [
    M_CHEST_HEIGHT,
    M_HIP_LENGTH,
    M_THIGH_LENGTH,
    M_LOWER_LEG_LENGTH,
    M_UPPER_ARM_LENGTH,
    M_FOREARM_LENGTH,
    M_NECK_LENGTH,
]

import os
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
log_file = open(LOG_PATH, "w", encoding="utf-8", buffering=1)

def log(msg=""):
    print(msg)
    log_file.write(msg + "\n")

def read_height_cm(avatar):
    kMax    = RLPy.RVector3(0, 0, 0)
    kCenter = RLPy.RVector3(0, 0, 0)
    kMin    = RLPy.RVector3(0, 0, 0)
    avatar.GetBounds(kMax, kCenter, kMin)
    # CC5 koordinat sistemi: Y = yukarı
    candidates = {
        "Y": kMax.y - kMin.y,
        "Z": kMax.z - kMin.z,
    }
    # 100–250 cm aralığında olan eksen büyük ihtimalle boy
    for axis, val in candidates.items():
        if 100 < val < 250:
            return axis, val
    # hiçbiri uymazsa hepsini döndür
    return "?", candidates

# ── Projeyi yükle ─────────────────────────────────────────────────────────────
log("LoadFile (male)...")
RLPy.RFileIO.LoadFile(PROJECT_FILES["male"])
avatar  = RLPy.RScene.GetAvatars()[0]
shaping = avatar.GetAvatarShapingComponent()
log(f"Avatar: {avatar.GetName()}")
log("")
log(f"{'height_score':>14}  {'morph_weight':>13}  {'height_cm':>10}")
log("-" * 44)

for hs in TEST_SCORES:
    # Önce tüm morphları sıfırla
    for mid in ALL_MORPHS:
        shaping.SetShapingMorphWeight(mid, 0.0)

    # Sadece boy morphlarını uygula (segment score = 0.5 → nötr offset)
    w = segment_weight(hs, SEG_NEUTRAL)
    for mid in HEIGHT_MORPHS:
        shaping.SetShapingMorphWeight(mid, w)

    axis, h = read_height_cm(avatar)
    log(f"{hs:>14.2f}  {w:>+13.4f}  {h:>9.2f} cm  [{axis}]")

log("")
log("Tamamlandı.")
log_file.close()

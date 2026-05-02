"""
Paylaşılan sabitler ve hesaplama fonksiyonları.
RLPy bağımlılığı yok — hem cc5_export hem export_probe import edebilir.
"""

# ── Proje yolları ─────────────────────────────────────────────────────────────

PROJECT_FILES = {
    "male":   r"C:\Users\Public\Documents\Reallusion\Reallusion Custom\Project\CC Project\_HD_Aaron_A-pose.ccProject",
    "female": r"C:\Users\Public\Documents\Reallusion\Reallusion Custom\Project\CC Project\_HD_Ariana_A-pose.ccProject",
}

# ── Morph ID'leri ─────────────────────────────────────────────────────────────

# Layer 1 — Full body preset morphlar
M_BODY_FAT      = "cc embed morphs/embed_full_body3"   # Body Fat B
M_BODY_THIN     = "cc embed morphs/embed_full_body5"   # Body Thin
M_BODY_MUSCULAR = "cc embed morphs/embed_full_body6"   # Body Muscular A
M_BODY_BUILDER  = "cc embed morphs/embed_full_body1"   # Body Bodybuilder

# Layer 2 — Segment scale (bölgesel sapma)
M_SHOULDER_SCALE   = "cc embed morphs/embed_arm101"
M_UPPER_ARM_SCALE  = "cc embed morphs/embed_arm3"
M_UPPER_ARM_LENGTH = "cc embed morphs/embed_arm4"
M_FOREARM_SCALE    = "cc embed morphs/embed_arm2"
M_FOREARM_LENGTH   = "cc embed morphs/embed_arm5"
M_CHEST_SCALE      = "cc embed morphs/embed_torso104"
M_CHEST_HEIGHT     = "cc embed morphs/embed_torso112"
M_CHEST_WIDTH      = "cc embed morphs/embed_torso105"
M_CHEST_DEPTH      = "cc embed morphs/embed_torso103"
M_BREAST_SCALE_B   = "cc embed morphs/embed_torso102"
M_BREAST_PROXIMITY = "cc embed morphs/embed_torso101"
M_PECTORAL_SCALE   = "cc embed morphs/embed_torso114"
M_PECTORAL_HEIGHT  = "cc embed morphs/embed_torso115"
M_NECK_SCALE       = "cc embed morphs/embed_torso110"
M_NECK_LENGTH      = "cc embed morphs/embed_torso109"
M_ABDOMEN_SCALE    = "cc embed morphs/embed_torso113"
M_ABDOMEN_DEPTH    = "cc embed morphs/embed_torso111"
M_ABS_LINE_DEPTH   = "cc embed morphs/embed_torso106"
M_HIP_LOVE_HANDLES = "cc embed morphs/embed_torso107"
M_HIP_SCALE        = "cc embed morphs/embed_torso2"
M_HIP_LENGTH       = "cc embed morphs/embed_torso4"
M_GLUTE_SCALE      = "cc embed morphs/embed_torso1"
M_THIGH_SCALE      = "cc embed morphs/embed_leg3"
M_THIGH_LENGTH     = "cc embed morphs/embed_leg4"
M_LOWER_LEG_SCALE  = "cc embed morphs/embed_leg2"
M_LOWER_LEG_LENGTH = "cc embed morphs/embed_leg5"

# HD kas morphları
M_MUSC_ARM      = "2025-05-05-12-31-36_embed_athetic_arn_01"
M_MUSC_SHOULDER = "2025-05-05-12-22-16_embed_athetic_shoulder_01"
M_MUSC_BACK     = "2025-05-05-12-31-03_embed_athetic_back_01"
M_MUSC_CHEST_A  = "2025-05-05-12-07-08_embed_athetic_chest_01"
M_MUSC_CHEST_B  = "2025-05-08-11-32-58_embed_athetic_chest_02"
M_MUSC_CHEST_C  = "2025-06-10-15-34-47_embed_athetic_chest_c"
M_MUSC_ABS      = "2025-05-08-15-26-33_embed_athetic_abs_iso_01"
M_MUSC_OBLIQUES = "2025-05-08-15-29-44_embed_athetic_side_abs_01"
M_MUSC_THIGH    = "2025-05-05-12-32-25_embed_athetic_thigh_01"
M_MUSC_CALF     = "2025-05-05-12-33-02_embed_athetic_calf_01"
M_MUSC_NECK     = "2025-05-05-13-47-33_embed_athetic_chest_01"
M_MUSC_WAIST    = "2025-05-05-12-18-34_embed_athetic_abs_01"

# HD ince deri morphları
M_SKIN_ARM      = "2025-05-07-14-12-07_pack_skinny_arm_01"
M_SKIN_SHOULDER = "2025-05-07-12-21-11_pack_skinny_shoulder_01"
M_SKIN_BACK     = "2025-06-10-17-08-24_pack_skinny_back_02"
M_SKIN_CHEST    = "2025-05-08-14-58-30_pack_skinny_chest_03"
M_SKIN_ABS      = "2025-05-07-13-43-26_pack_skinny_abs_01"
M_SKIN_RIBCAGE  = "2025-05-07-12-27-17_pack_skinny_rib_01"
M_SKIN_THIGH    = "2025-06-10-17-18-17_pack_skinny_thigh_02"
M_SKIN_CALF     = "2025-05-07-14-35-43_pack_skinny_calf_01"
M_SKIN_BUTTOCKS = "2025-06-10-17-01-51_pack_skinny_bottom_02"
M_SKIN_NECK     = "2025-05-07-12-04-51_pack_skinny_neck_01"
M_SKIN_SPINE    = "2025-05-07-14-17-56_pack_skinny_spine_01"

ALL_MORPHS = [
    # Layer 1 — full body
    M_BODY_FAT, M_BODY_THIN, M_BODY_MUSCULAR, M_BODY_BUILDER,
    # Layer 2 — segment scale
    M_NECK_SCALE, M_NECK_LENGTH,
    M_SHOULDER_SCALE, M_UPPER_ARM_SCALE, M_FOREARM_SCALE,
    M_UPPER_ARM_LENGTH, M_FOREARM_LENGTH,
    M_CHEST_SCALE, M_CHEST_WIDTH, M_CHEST_DEPTH,
    M_BREAST_SCALE_B, M_BREAST_PROXIMITY,
    M_PECTORAL_SCALE, M_PECTORAL_HEIGHT,
    M_ABDOMEN_SCALE, M_ABDOMEN_DEPTH, M_ABS_LINE_DEPTH,
    M_HIP_LOVE_HANDLES, M_HIP_SCALE,
    M_GLUTE_SCALE, M_THIGH_SCALE, M_LOWER_LEG_SCALE,
    M_CHEST_HEIGHT, M_HIP_LENGTH, M_THIGH_LENGTH, M_LOWER_LEG_LENGTH,
    # HD kas
    M_MUSC_ARM, M_MUSC_SHOULDER, M_MUSC_BACK,
    M_MUSC_CHEST_A, M_MUSC_CHEST_B, M_MUSC_CHEST_C,
    M_MUSC_ABS, M_MUSC_OBLIQUES, M_MUSC_THIGH, M_MUSC_CALF,
    M_MUSC_NECK, M_MUSC_WAIST,
    # HD ince deri
    M_SKIN_ARM, M_SKIN_SHOULDER, M_SKIN_BACK, M_SKIN_CHEST,
    M_SKIN_ABS, M_SKIN_RIBCAGE, M_SKIN_THIGH, M_SKIN_CALF,
    M_SKIN_BUTTOCKS, M_SKIN_NECK, M_SKIN_SPINE,
]

# ── Sabitler ──────────────────────────────────────────────────────────────────

FEMALE_HD_SCALE = 0.4
SEGMENT_DELTA   = 0.30

# Segment sapma normalizasyonu: dataset'te max spread=0.30 → max dev from mean=0.15
SEG_DEV_NORM = 0.15

# Layer 2 segment scale morphlarına uygulanacak max sapma katsayısı
SEG_SCALE_STRENGTH = 0.25

PATTERN_MULTIPLIERS = {
    "balanced":       {"upper": 1.00, "lower": 1.00, "chest": 1.00, "back": 1.00, "abs": 1.00},
    "upper_dominant": {"upper": 1.30, "lower": 0.55, "chest": 1.30, "back": 1.30, "abs": 1.20},
    "lower_dominant": {"upper": 0.55, "lower": 1.30, "chest": 0.55, "back": 0.55, "abs": 0.80},
    "push_dominant":  {"upper": 1.10, "lower": 0.90, "chest": 1.40, "back": 0.65, "abs": 1.10},
    "pull_dominant":  {"upper": 1.10, "lower": 0.90, "chest": 0.65, "back": 1.40, "abs": 1.10},
}

MORPH_CLIP = {
    M_SHOULDER_SCALE:   (-0.5,  1.0),
    M_UPPER_ARM_SCALE:  (-1.0,  1.0),
    M_FOREARM_SCALE:    (-1.0,  1.0),
    M_CHEST_SCALE:      (-0.5,  1.0),
    M_CHEST_WIDTH:      (-0.5,  1.0),
    M_CHEST_DEPTH:      (-0.5,  1.0),
    M_PECTORAL_SCALE:   ( 0.0,  1.0),
    M_ABDOMEN_SCALE:    (-1.0,  1.0),
    M_ABDOMEN_DEPTH:    (-1.0,  1.0),
    M_ABS_LINE_DEPTH:   ( 0.0,  1.0),
    M_HIP_LOVE_HANDLES: ( 0.0,  1.0),
    M_HIP_SCALE:        (-0.3,  1.0),
    M_GLUTE_SCALE:      (-1.0,  1.0),
    M_THIGH_SCALE:      (-1.0,  1.0),
    M_LOWER_LEG_SCALE:  (-1.0,  1.0),
}

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def score_to_weight(score):
    return max(-1.0, min(1.0, (score - 0.5) * 2.0))

def segment_weight(height_score, seg_score):
    base   = score_to_weight(height_score)
    offset = (seg_score - 0.5) * 2.0 * SEGMENT_DELTA
    return max(-1.0, min(1.0, base + offset))

# ── Ana hesaplama ─────────────────────────────────────────────────────────────

def compute_all_weights(fat, muscle, height_score, chest_height_score,
                        hip_length_score, thigh_length_score, lower_leg_length_score,
                        upper_arm_length_score, forearm_length_score,
                        neck_length_score,
                        pattern, gender):

    hd = 1.0 if gender == "male" else FEMALE_HD_SCALE
    m  = PATTERN_MULTIPLIERS.get(pattern, PATTERN_MULTIPLIERS["balanced"])

    # ── Layer 1: Full body morph ağırlıkları ──────────────────────────────────
    body_fat = min(fat, 1.0)

    # Body Thin: sadece düşük fat + düşük muscle'da aktif (underweight tipi)
    W_thin_fat  = max((0.15 - fat) / 0.15, 0.0)
    W_thin_musc = max((0.25 - muscle) / 0.25, 0.0)
    body_thin   = min(W_thin_fat * W_thin_musc, 1.0)

    # Body Muscular A ve Bodybuilder birbirini dışlayan blend:
    # muscle 0→0.65 : Muscular A açılır, Builder=0
    # muscle 0.65→1 : Muscular A kapanır, Builder açılır
    BUILDER_THRESHOLD = 0.65
    if muscle <= BUILDER_THRESHOLD:
        body_muscular = min(muscle / BUILDER_THRESHOLD * hd, 1.0)
        body_builder  = 0.0
    else:
        t = (muscle - BUILDER_THRESHOLD) / (1.0 - BUILDER_THRESHOLD)  # 0→1
        body_muscular = min((1.0 - t) * hd, 1.0)
        body_builder  = min(t * hd, 1.0)

    # ── Layer 2: Bölgesel sapma hesabı ────────────────────────────────────────
    seg_scores = [chest_height_score, hip_length_score, thigh_length_score,
                  lower_leg_length_score, upper_arm_length_score,
                  forearm_length_score, neck_length_score]
    seg_mean = sum(seg_scores) / len(seg_scores)

    def seg_dev(score):
        """Segment'in grup ortalamasından sapması, ±1 aralığına normalize edilmiş."""
        return max(-1.0, min(1.0, (score - seg_mean) / SEG_DEV_NORM))

    def dev_scale(mid, score):
        """Segment scale morph için bölgesel sapma ağırlığı."""
        lo, hi = MORPH_CLIP[mid]
        return max(lo, min(hi, seg_dev(score) * SEG_SCALE_STRENGTH))

    # HD morph yardımcıları
    def musc_hd(region):
        return min(muscle * m[region], 1.0) * hd

    def skin_hd(region):
        # W_thin_fat: düşük fat → ince deri; kas yoğunsa bastır
        return min(W_thin_fat * (2.0 - m[region]), 1.0) * hd

    w_chest = musc_hd("chest")
    w_abs   = musc_hd("abs")

    return {
        # ── Layer 1: Full body ────────────────────────────────────────────────
        M_BODY_FAT:      body_fat,
        M_BODY_THIN:     body_thin,
        M_BODY_MUSCULAR: body_muscular,
        M_BODY_BUILDER:  body_builder,

        # ── Layer 2: Bölgesel scale sapmaları ────────────────────────────────
        M_SHOULDER_SCALE:   dev_scale(M_SHOULDER_SCALE,   upper_arm_length_score),
        M_UPPER_ARM_SCALE:  dev_scale(M_UPPER_ARM_SCALE,  upper_arm_length_score),
        M_FOREARM_SCALE:    dev_scale(M_FOREARM_SCALE,    forearm_length_score),
        M_CHEST_SCALE:      dev_scale(M_CHEST_SCALE,      chest_height_score),
        M_CHEST_WIDTH:      dev_scale(M_CHEST_WIDTH,      chest_height_score),
        M_CHEST_DEPTH:      dev_scale(M_CHEST_DEPTH,      chest_height_score),
        M_ABDOMEN_SCALE:    dev_scale(M_ABDOMEN_SCALE,    hip_length_score),
        M_ABDOMEN_DEPTH:    max(0.0, dev_scale(M_ABDOMEN_DEPTH,    hip_length_score)),
        M_HIP_LOVE_HANDLES: max(0.0, dev_scale(M_HIP_LOVE_HANDLES, hip_length_score)),
        M_HIP_SCALE:        dev_scale(M_HIP_SCALE,        hip_length_score),
        M_GLUTE_SCALE:      dev_scale(M_GLUTE_SCALE,      hip_length_score),
        M_THIGH_SCALE:      dev_scale(M_THIGH_SCALE,      thigh_length_score),
        M_LOWER_LEG_SCALE:  dev_scale(M_LOWER_LEG_SCALE,  lower_leg_length_score),

        # ── HD kas morphları ──────────────────────────────────────────────────
        M_PECTORAL_SCALE:   min(musc_hd("chest"), 1.0),
        M_PECTORAL_HEIGHT:  musc_hd("chest"),
        M_ABS_LINE_DEPTH:   musc_hd("abs"),
        M_MUSC_ARM:         musc_hd("upper"),
        M_MUSC_SHOULDER:    musc_hd("upper"),
        M_MUSC_BACK:        musc_hd("back"),
        M_MUSC_CHEST_A:     w_chest / 3,
        M_MUSC_CHEST_B:     w_chest / 3,
        M_MUSC_CHEST_C:     w_chest / 3,
        M_MUSC_ABS:         w_abs / 2,
        M_MUSC_OBLIQUES:    w_abs / 2,
        M_MUSC_THIGH:       musc_hd("lower"),
        M_MUSC_CALF:        musc_hd("lower"),
        M_MUSC_NECK:        musc_hd("upper"),
        M_MUSC_WAIST:       musc_hd("abs"),

        # ── HD ince deri morphları ────────────────────────────────────────────
        M_SKIN_ARM:         skin_hd("upper"),
        M_SKIN_SHOULDER:    skin_hd("upper"),
        M_SKIN_BACK:        skin_hd("back"),
        M_SKIN_CHEST:       skin_hd("chest"),
        M_SKIN_ABS:         skin_hd("abs"),
        M_SKIN_RIBCAGE:     skin_hd("abs"),
        M_SKIN_THIGH:       skin_hd("lower"),
        M_SKIN_CALF:        skin_hd("lower"),
        M_SKIN_BUTTOCKS:    skin_hd("lower"),
        M_SKIN_NECK:        skin_hd("upper"),
        M_SKIN_SPINE:       skin_hd("back"),

        # ── Göğüs ─────────────────────────────────────────────────────────────
        M_BREAST_SCALE_B:   min(0.05 + fat * 0.60, 1.0) if gender == "female"
                            else max(0.0, (fat - 0.50) / 0.50) * 0.35,
        M_BREAST_PROXIMITY: min(0.05 + fat * 0.35, 1.0) if gender == "female"
                            else max(0.0, (fat - 0.50) / 0.50) * 0.20,

        # ── Uzunluk morphları (height_score bazlı, değişmedi) ─────────────────
        M_CHEST_HEIGHT:     segment_weight(height_score, chest_height_score),
        M_HIP_LENGTH:       segment_weight(height_score, hip_length_score),
        M_THIGH_LENGTH:     segment_weight(height_score, thigh_length_score),
        M_LOWER_LEG_LENGTH: segment_weight(height_score, lower_leg_length_score),
        M_UPPER_ARM_LENGTH: segment_weight(height_score, upper_arm_length_score),
        M_FOREARM_LENGTH:   segment_weight(height_score, forearm_length_score),
        M_NECK_SCALE:       min(muscle * m["upper"] * 0.6, 1.0),
        M_NECK_LENGTH:      max(0.0, segment_weight(height_score, neck_length_score)),
    }

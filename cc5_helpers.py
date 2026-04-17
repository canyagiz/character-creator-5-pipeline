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

M_SHOULDER_SCALE   = "cc embed morphs/embed_arm101"
M_UPPER_ARM_SCALE  = "cc embed morphs/embed_arm3"
M_FOREARM_SCALE    = "cc embed morphs/embed_arm2"
M_CHEST_SCALE      = "cc embed morphs/embed_torso104"
M_CHEST_HEIGHT     = "cc embed morphs/embed_torso112"
M_CHEST_WIDTH      = "cc embed morphs/embed_torso105"
M_CHEST_DEPTH      = "cc embed morphs/embed_torso103"
M_BREAST_SCALE_B   = "cc embed morphs/embed_torso102"
M_BREAST_PROXIMITY = "cc embed morphs/embed_torso101"
M_PECTORAL_SCALE   = "cc embed morphs/embed_torso114"
M_PECTORAL_HEIGHT  = "cc embed morphs/embed_torso115"
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
    M_SHOULDER_SCALE, M_UPPER_ARM_SCALE, M_FOREARM_SCALE,
    M_CHEST_SCALE, M_CHEST_WIDTH, M_CHEST_DEPTH,
    M_BREAST_SCALE_B, M_BREAST_PROXIMITY,
    M_PECTORAL_SCALE, M_PECTORAL_HEIGHT,
    M_ABDOMEN_SCALE, M_ABDOMEN_DEPTH, M_ABS_LINE_DEPTH,
    M_HIP_LOVE_HANDLES, M_HIP_SCALE,
    M_GLUTE_SCALE, M_THIGH_SCALE, M_LOWER_LEG_SCALE,
    M_CHEST_HEIGHT, M_HIP_LENGTH, M_THIGH_LENGTH, M_LOWER_LEG_LENGTH,
    M_MUSC_ARM, M_MUSC_SHOULDER, M_MUSC_BACK,
    M_MUSC_CHEST_A, M_MUSC_CHEST_B, M_MUSC_CHEST_C,
    M_MUSC_ABS, M_MUSC_OBLIQUES, M_MUSC_THIGH, M_MUSC_CALF,
    M_MUSC_NECK, M_MUSC_WAIST,
    M_SKIN_ARM, M_SKIN_SHOULDER, M_SKIN_BACK, M_SKIN_CHEST,
    M_SKIN_ABS, M_SKIN_RIBCAGE, M_SKIN_THIGH, M_SKIN_CALF,
    M_SKIN_BUTTOCKS, M_SKIN_NECK, M_SKIN_SPINE,
]

# ── Sabitler ──────────────────────────────────────────────────────────────────

FEMALE_HD_SCALE = 0.4
SEGMENT_DELTA   = 0.30

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
    M_ABDOMEN_DEPTH:    ( 0.0,  1.0),
    M_ABS_LINE_DEPTH:   ( 0.0,  1.0),
    M_HIP_LOVE_HANDLES: ( 0.0,  1.0),
    M_HIP_SCALE:        (-0.3,  1.0),
    M_GLUTE_SCALE:      (-1.0,  1.0),
    M_THIGH_SCALE:      (-1.0,  1.0),
    M_LOWER_LEG_SCALE:  (-1.0,  1.0),
}

# ── Hesaplama fonksiyonları ───────────────────────────────────────────────────

def score_to_weight(score):
    return max(-1.0, min(1.0, (score - 0.5) * 2.0))

def segment_weight(height_score, seg_score):
    base   = score_to_weight(height_score)
    offset = (seg_score - 0.5) * 2.0 * SEGMENT_DELTA
    return max(-1.0, min(1.0, base + offset))

def compute_all_weights(fat, muscle, height_score, chest_height_score,
                        hip_length_score, thigh_length_score, lower_leg_length_score,
                        pattern, gender):
    hd = 1.0 if gender == "male" else FEMALE_HD_SCALE
    m  = PATTERN_MULTIPLIERS.get(pattern, PATTERN_MULTIPLIERS["balanced"])

    def scale(mid, a_fat, a_musc, region=None):
        pm = m[region] if region else 1.0
        w  = fat * a_fat + muscle * a_musc * pm
        lo, hi = MORPH_CLIP[mid]
        return max(lo, min(hi, w))

    def musc_hd(region):
        return min(muscle * m[region], 1.0) * hd

    W_thin = max((0.15 - fat) / 0.15, 0.0)

    def skin_hd(region):
        return min(W_thin * (2.0 - m[region]), 1.0) * hd

    w_chest = musc_hd("chest")
    w_abs   = musc_hd("abs")

    return {
        M_SHOULDER_SCALE:   scale(M_SHOULDER_SCALE,   0.10, 0.90, "upper"),
        M_UPPER_ARM_SCALE:  scale(M_UPPER_ARM_SCALE,  0.60, 0.70, "upper"),
        M_FOREARM_SCALE:    scale(M_FOREARM_SCALE,    0.50, 0.60, "upper"),
        M_PECTORAL_SCALE:   scale(M_PECTORAL_SCALE,   0.00, 0.90, "chest"),
        M_PECTORAL_HEIGHT:  musc_hd("chest"),
        M_ABDOMEN_SCALE:    scale(M_ABDOMEN_SCALE,    0.90, 0.20, "abs"),
        M_ABDOMEN_DEPTH:    scale(M_ABDOMEN_DEPTH,    1.00, 0.00),
        M_ABS_LINE_DEPTH:   scale(M_ABS_LINE_DEPTH,   0.00, 0.90, "abs"),
        M_HIP_LOVE_HANDLES: scale(M_HIP_LOVE_HANDLES, 0.90, 0.00),
        M_HIP_SCALE:        scale(M_HIP_SCALE,        0.70, 0.00),
        M_GLUTE_SCALE:      scale(M_GLUTE_SCALE,      0.70, 0.40, "lower"),
        M_THIGH_SCALE:      scale(M_THIGH_SCALE,      0.80, 0.60, "lower"),
        M_LOWER_LEG_SCALE:  scale(M_LOWER_LEG_SCALE,  0.40, 0.60, "lower"),
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
        M_BREAST_SCALE_B:   min(0.05 + fat * 0.60, 1.0) if gender == "female"
                            else max(0.0, (fat - 0.50) / 0.50) * 0.35,
        M_BREAST_PROXIMITY: min(0.05 + fat * 0.35, 1.0) if gender == "female"
                            else max(0.0, (fat - 0.50) / 0.50) * 0.20,
        M_CHEST_HEIGHT:     segment_weight(height_score, chest_height_score),
        M_HIP_LENGTH:       segment_weight(height_score, hip_length_score),
        M_THIGH_LENGTH:     segment_weight(height_score, thigh_length_score),
        M_LOWER_LEG_LENGTH: segment_weight(height_score, lower_leg_length_score),
    }

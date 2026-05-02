# Row → CC5 Model Pipeline

Bir dataset satırı nasıl CC5 karakterine dönüşür — formüller ve örnek hesaplamalarla.

---

## Genel Mimari

```
dataset.csv row
      │
      ▼
cc5_helpers.compute_all_weights()
      │
      ├── Layer 1 — Full Body Morphs    (genel vücut tipi)
      ├── Layer 2 — Segment Scale       (bölgesel sapma)
      ├── Layer 3 — Uzunluk Morphları   (height_score + segment offset)
      ├── Layer 4 — HD Kas Morphları    (muscle detail, pattern'a duyarlı)
      └── Layer 5 — HD İnce Deri       (underweight detail)
            │
            ▼
      SetShapingMorphWeight() × ~55 morph
            │
            ▼
      ExportFbxFile() → .fbx
```

---

## Örnek Satır: `char_11256`

```
char_id       : char_11256
gender        : male
age           : 29
group         : obese
fat_score     : 1.0000
muscle_score  : 0.2131
height_score  : 0.2000
chest_height  : 0.5848
hip_length    : 0.5197
thigh_length  : 0.3647
lower_leg     : 0.4240
upper_arm     : 0.6122
forearm       : 0.5714
neck_length   : 0.3122
pattern       : balanced
```

---

## Layer 1 — Full Body Morphs

Karakterin genel vücut tipini belirleyen 4 CC5 preset morfu. Bunlar tek başına "bu adam yağlı / ince / kaslı" görünümünü sağlar.

### Formüller

**Body Fat B** `embed_full_body3`
```
body_fat = min(fat_score, 1.0)
```

**Body Thin** `embed_full_body5`  
Sadece hem fat hem muscle düşükse aktif (underweight tipi):
```
W_thin_fat  = max((0.15 - fat) / 0.15,  0.0)
W_thin_musc = max((0.25 - muscle) / 0.25, 0.0)
body_thin   = min(W_thin_fat × W_thin_musc, 1.0)
```

**Body Muscular A** `embed_full_body6`
```
hd            = 1.0 (male) veya 0.4 (female)
body_muscular = min(muscle × hd, 1.0)
```

**Body Bodybuilder** `embed_full_body1`  
Muscle > 0.65 olduğunda devreye girer:
```
body_builder = min(max(muscle - 0.65, 0) / 0.35 × hd, 1.0)
```

### char_11256 hesabı

```
body_fat      = min(1.0, 1.0)              = 1.000  ✓ tam obez
body_thin     = 0 (fat=1.0 → W_thin=0)    = 0.000
body_muscular = min(0.2131 × 1.0, 1.0)    = 0.213
body_builder  = max(0.2131-0.65, 0) = 0   = 0.000
```

---

## Layer 2 — Segment Scale (Bölgesel Sapma)

Full body morph genel görünümü kurar; segment scale morphları ise her bölgenin bu genel görünümden **ne kadar saptığını** ekler.

### Temel fikir

Her segment score'un grubun ortalamasından sapması hesaplanır ve bu sapma ±0.25 aralığında ilgili scale morphuna yazılır.

```
seg_scores = [chest, hip, thigh, lower_leg, upper_arm, forearm, neck]
seg_mean   = ortalama(seg_scores)

seg_dev(score) = clamp((score - seg_mean) / SEG_DEV_NORM,  -1.0, +1.0)
                 # SEG_DEV_NORM = 0.15  (max spread 0.30'un yarısı)

morph_weight = seg_dev(score) × SEG_SCALE_STRENGTH
               # SEG_SCALE_STRENGTH = 0.25
```

**Yorumu:** Bu bölge ortalamanın üstündeyse morph pozitif (daha iri), altındaysa negatif (daha ince). Sıfırda full body preset'in kendi değeri korunur.

### char_11256 hesabı

```
seg_mean = (0.5848 + 0.5197 + 0.3647 + 0.4240 + 0.6122 + 0.5714 + 0.3122) / 7
         = 0.4841
```

| Segment    | Score  | dev = (score−0.4841)/0.15 | scale_w = dev×0.25 | Morph           |
|---|---|---|---|---|
| chest      | 0.5848 | +0.671                    | **+0.168**         | chest_scale, chest_width, chest_depth |
| hip        | 0.5197 | +0.237                    | **+0.059**         | hip_scale, glute_scale, abdomen_scale |
| thigh      | 0.3647 | −0.796                    | **−0.199**         | thigh_scale |
| lower_leg  | 0.4240 | −0.401                    | **−0.100**         | lower_leg_scale |
| upper_arm  | 0.6122 | +0.854                    | **+0.213**         | shoulder_scale, upper_arm_scale |
| forearm    | 0.5714 | +0.582                    | **+0.145**         | forearm_scale |
| neck       | 0.3122 | −1.000 (clamp)            | **−0.250**         | (neck_scale ayrı hesaplanır) |

→ Bu karakter: göğsü ve kolları kendi vücut tipine göre biraz iri, bacakları biraz ince.

---

## Layer 3 — Uzunluk Morphları

Kemik uzunluklarını belirler. `height_score` ana boyu, her segment score ise o bölgenin boy içindeki payını ayarlar.

### Formüller

```
score_to_weight(s) = clamp((s − 0.5) × 2,  −1.0, +1.0)

segment_weight(height_score, seg_score) =
    base   = score_to_weight(height_score)
    offset = (seg_score − 0.5) × 2 × SEGMENT_DELTA   # SEGMENT_DELTA = 0.30
    return clamp(base + offset,  −1.0, +1.0)
```

`height_score = 0.5` → weight = 0 → CC5 base boy (~183 cm Aaron)  
`height_score = 0.2` → base = −0.60 → tüm segmentler kısa başlar, seg_score ile ±0.30 sapma

### char_11256 hesabı (`height_score = 0.2`)

```
base = (0.2 − 0.5) × 2 = −0.60
```

| Segment    | seg_score | offset = (s−0.5)×2×0.30 | morph_weight      |
|---|---|---|---|
| chest      | 0.5848    | +0.051                   | −0.60+0.051 = **−0.549** |
| hip        | 0.5197    | +0.012                   | **−0.588** |
| thigh      | 0.3647    | −0.081                   | **−0.681** |
| lower_leg  | 0.4240    | −0.046                   | **−0.646** |
| upper_arm  | 0.6122    | +0.067                   | **−0.533** |
| forearm    | 0.5714    | +0.043                   | **−0.557** |
| neck       | 0.3122    | −0.113                   | −0.713 → **0.000** (neck negatife gitmiyor) |

Tüm uzunluklar negatif → ~150 cm kısa boy, ama thigh en kısa, chest en az kısa.

---

## Layer 4 — HD Kas Morphları

Pattern multiplier'a duyarlı, gender ile scale edilen yüksek çözünürlüklü kas detay morphları.

### Formüller

```
hd = 1.0 (male) veya FEMALE_HD_SCALE=0.4 (female)
m  = PATTERN_MULTIPLIERS[training_pattern]   # bölge katsayıları

musc_hd(region) = min(muscle × m[region], 1.0) × hd

w_chest = musc_hd("chest")
w_abs   = musc_hd("abs")
```

**Balanced pattern** için tüm `m[region] = 1.0`.

### char_11256 hesabı (`muscle=0.2131, pattern=balanced, gender=male`)

```
musc_hd("upper") = min(0.2131 × 1.0, 1.0) × 1.0 = 0.213
musc_hd("chest") = 0.213  →  chest morphları: 0.213/3 = 0.071 her biri
musc_hd("abs")   = 0.213  →  abs morphları:   0.213/2 = 0.107 her biri
musc_hd("lower") = 0.213
musc_hd("back")  = 0.213
```

Kas skoru 0.21 düşük olduğu için HD kas morphları zayıf — bu obez bir karakter için doğru.

---

## Layer 5 — HD İnce Deri Morphları

Sadece düşük fat + düşük muscle (underweight) durumunda aktif.

### Formül

```
W_thin_fat = max((0.15 − fat) / 0.15, 0.0)   # fat < 0.15 olduğunda artar

skin_hd(region) = min(W_thin_fat × (2.0 − m[region]), 1.0) × hd
```

### char_11256 hesabı (`fat=1.0`)

```
W_thin_fat = max((0.15 − 1.0) / 0.15, 0.0) = max(−5.67, 0) = 0.0
→ Tüm skin morphları = 0.000   (obez karakterde ince deri yok)
```

---

## Tüm Morph Çıktısı — char_11256

| Morph | Değer | Layer |
|---|---|---|
| Body Fat B | **1.000** | L1 |
| Body Thin | 0.000 | L1 |
| Body Muscular A | 0.213 | L1 |
| Body Bodybuilder | 0.000 | L1 |
| shoulder_scale | +0.213 | L2 |
| upper_arm_scale | +0.213 | L2 |
| forearm_scale | +0.145 | L2 |
| chest_scale/width/depth | +0.168 | L2 |
| abdomen_scale/depth | +0.059 | L2 |
| hip_love_handles | +0.059 | L2 |
| hip_scale, glute_scale | +0.059 | L2 |
| thigh_scale | **−0.199** | L2 |
| lower_leg_scale | −0.100 | L2 |
| chest_height (uzunluk) | −0.549 | L3 |
| hip_length | −0.588 | L3 |
| thigh_length | **−0.681** | L3 |
| lower_leg_length | −0.646 | L3 |
| upper_arm_length | −0.533 | L3 |
| forearm_length | −0.557 | L3 |
| neck_length | 0.000 | L3 |
| musc_arm/shoulder/back/thigh/calf | 0.213 | L4 |
| musc_chest_A/B/C | 0.071 | L4 |
| musc_abs/obliques | 0.107 | L4 |
| skin_* (tümü) | 0.000 | L5 |

---

## Özet: Score → Görünüm Tablosu

| fat_score | muscle_score | Beklenen görünüm |
|---|---|---|
| 1.0 | 0.2 | Obez, az kaslı — Body Fat B=1.0 baskın |
| 0.1 | 1.0 | Athletic hyper — Body Muscular A=1.0, Builder=1.0 |
| 0.05 | 0.05 | Underweight — Body Thin aktif, skin morphlar görünür |
| 0.3 | 0.15 | Normal — full body preset'ler düşük, base model ağır basar |
| 0.1 | 0.55 | Athletic lean — Muscular A orta, Builder=0 |

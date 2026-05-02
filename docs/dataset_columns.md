# Dataset Column Reference

**Toplam satır:** 30,000  
**Üretim:** `generate_dataset.py` (Latin Hypercube Sampling)  
**CC5 export:** `cc5_export.py`

---

## Kimlik & Sınıflandırma

| Kolon | Tip | Değerler | Açıklama |
|---|---|---|---|
| `char_id` | string | `char_00001` … `char_30000` | Benzersiz karakter ID'si |
| `gender` | string | `male`, `female` | Cinsiyet — CC5'te farklı base model yüklenir (Aaron / Ariana) |
| `age` | int | 14–40 | Yaş. 14–17 arası adolescent kısıtları uygulanır |
| `group` | string | 6 kategori (aşağıda) | Vücut kompozisyon grubu |
| `training_pattern` | string | 5 kategori (aşağıda) | Kas geliştirme paterni — sadece athletic gruplarda anlamlı |

### group değerleri

| Değer | Dağılım | fat_score aralığı | muscle_score aralığı |
|---|---|---|---|
| `underweight` | %10 | 0.00–0.15 | 0.00–0.20 |
| `normal` | %25 | 0.16–0.35 | 0.10–0.30 |
| `overweight` | %25 | 0.36–0.60 | 0.15–0.35 |
| `obese` | %15 | 0.61–1.00 | 0.15–0.35 |
| `athletic_lean` | %15 | 0.05–0.15 | 0.40–0.65 |
| `athletic_hyper` | %10 | 0.05–0.15 | 0.66–1.00 |

### training_pattern değerleri

Sadece `athletic_lean` ve `athletic_hyper` gruplarda dağılımlı, diğerleri her zaman `balanced`.

| Değer | Etki |
|---|---|
| `balanced` | Tüm bölgeler eşit |
| `upper_dominant` | Üst vücut kas morphları güçlü, alt vücut zayıf |
| `lower_dominant` | Alt vücut kas morphları güçlü, üst vücut zayıf |
| `push_dominant` | Göğüs baskın, sırt zayıf |
| `pull_dominant` | Sırt baskın, göğüs zayıf |

---

## Kompozisyon Skorları

Tüm score'lar `[0.0, 1.0]` aralığında sürekli değer. CC5 morph weight'e dönüşüm: `weight = (score - 0.5) × 2` → `[-1.0, +1.0]`.

| Kolon | Aralık | Açıklama |
|---|---|---|
| `fat_score` | 0.00–1.00 | Yağ oranı. Gruba göre sınırlanır (yukarıdaki tablo) |
| `muscle_score` | 0.00–1.00 | Kas oranı. Gruba göre sınırlanır |

### Yaş kısıtları (hard rules)

- **< 18:** Tüm boy ve segment score'lar max 0.80 ile kırpılır
- **< 16:** `fat_score` max 0.70, `muscle_score` max 0.40

---

## Boy Skoru

| Kolon | Aralık | CC5 karşılığı (Male/Aaron) |
|---|---|---|
| `height_score` | **0.20–0.75** | ≈150 cm – ≈212 cm |

Referans noktaları (probe ölçümü, Male/Aaron, segment score'lar nötr):

| height_score | height_cm |
|---|---|
| 0.20 | 149.36 cm |
| 0.25 | 154.92 cm |
| 0.30 | 160.52 cm |
| 0.50 | 183.11 cm (base) |
| 0.75 | 211.71 cm |

> Gerçek cm değeri Blender'dan çekilir (`height_cm` kolonu export sonrası doldurulur).

---

## Segment Uzunluk Skorları

Her segment, `height_score`'u baz alır; kendi skoru ±`SEGMENT_DELTA` (0.30) offset ekler:

```
segment_weight = clip(score_to_weight(height_score) + (seg_score - 0.5) × 2 × 0.30, -1, 1)
```

| Kolon | CC5 Morph | Açıklama |
|---|---|---|
| `chest_height_score` | `embed_torso112` | Torso / göğüs yüksekliği |
| `hip_length_score` | `embed_torso4` | Kalça uzunluğu |
| `thigh_length_score` | `embed_leg4` | Uyluk uzunluğu |
| `lower_leg_length_score` | `embed_leg5` | Alt bacak uzunluğu |
| `upper_arm_length_score` | `embed_arm4` | Üst kol uzunluğu |
| `forearm_length_score` | `embed_arm5` | Ön kol uzunluğu |
| `neck_length_score` | `embed_torso109` | Boyun uzunluğu |

**Orantısızlık kısıtı:** 7 segment score'un satır içi spread'i (max − min) **≤ 0.30** ile sınırlıdır. Aşan satırlarda tüm segment'ler merkeze doğru oransal olarak sıkıştırılır.

---

## Çıktı

| Kolon | Tip | Açıklama |
|---|---|---|
| `height_cm` | float | Blender export sonrası doldurulur; üretim aşamasında boş |

---

## Outliers

Her grup için seçilmiş uç vakalar — görsel doğrulama için `extremes_export_probe.py` ile export edilir.

| char_id | group | fat | muscle | height_score | gender | age | not |
|---|---|---|---|---|---|---|---|
| `char_11256` | obese | **1.00** | 0.21 | 0.20 | male | 29 | En yüksek fat + minimum boy |
| `char_14274` | athletic_hyper | 0.09 | **1.00** | 0.75 | male | 29 | En yüksek muscle + maksimum boy |
| `char_00017` | athletic_hyper | 0.08 | 0.76 | 0.75 | female | 29 | Kaslı + uzun kadın |
| `char_00037` | athletic_hyper | 0.08 | 0.67 | 0.20 | male | 40 | Kaslı + minimum boy (eski sorunlu, artık clipped) |
| `char_00048` | underweight | 0.08 | 0.07 | 0.20 | female | 17 | En düşük fat+muscle + minimum boy (adolescent) |
| `char_00005` | underweight | 0.06 | 0.09 | 0.75 | female | 29 | En ince + maksimum boy |
| `char_00033` | obese | 0.64 | 0.31 | 0.20 | female | 22 | Kilolu + minimum boy kadın |

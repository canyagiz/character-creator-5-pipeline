# Somatotip Sınıflandırma Sistemi

**Versiyon:** 2.0 — Kalibrasyon tabanlı  
**Güncelleme:** 2026-05-05  
**İlgili dosyalar:** `generate_dataset.py`, `analysis/derive_labels.py`, `analysis/calibration_select.py`

---

## Genel Bakış

Somatotip kolonu (`hourglass`, `pear`, `rectangle`, `apple`, `v_shape`) **üretim parametresi değil, türetilmiş bir etiket**tir. Her karakterin slider değerlerinden tahmin edilen gerçek vücut ölçümlerine dayanarak deterministik olarak atanır.

### Neden bu yaklaşım?

İlk sistemde (v1.0) somatotipler fat band'a göre rastgele seçiliyordu. Bu, yüksek fat'ta `hourglass` etiketi verilen karakterler doğuruyordu — görsel olarak tamamen elma görünümlü. Sorunun kök nedeni: CC5 morph formülünde abdomen, fat'a göre kalçadan daha hızlı büyüdüğünden (%90'a karşı %60-70), yüksek fat'ta bel her zaman kalçadan geniş çıkar. Hourglass fiziksel olarak imkânsızdı.

v2.0'da somatotip etiketi **879 gerçek CC5 render ölçümünden** (chest/waist/hip cm) öğrenilen bir regresyon modeliyle tahmin edilen ölçümlere dayalı kurallara göre belirlenir.

---

## Girdi Parametreleri

Sınıflandırmada kullanılan iki ana eksen:

| Parametre | Aralık | Anlamı |
|---|---|---|
| `hip_score` | 0.2–0.9 | Kalça/glute genişliği — fat'tan bağımsız kemik yapısı. 0.5 = nötr |
| `waist_def_score` | 0.2–0.9 | Bel tanımı — yüksek = dar bel, düşük = geniş bel |
| `fat_score` | 0.0–1.0 | Bel ve kalça çevresini doğrudan etkiler |
| `muscle_score` | 0.0–1.0 | Göğüs ve kol çevresini etkiler |

---

## Kalibrasyon Süreci

### 1. Probe seçimi (`analysis/calibration_select.py`)

`dataset.csv`'den 1009 karakter seçildi:
- `fat_score × hip_score × waist_def_score` grid'i (ana shape parametreleri)
- `fat_score × muscle_score` grid'i (kas etkisi)
- Tüm somatotipler × fat band'lar için temsil
- Segment extremes (uzunluk etkisi)

### 2. CC5 export + Blender ölçümü

`props/calibration_export.py` → 879 FBX export  
`pipeline.py --fbx-dir fbx_export/calib` → gerçek cm ölçümleri (`renders/meta/*.json`)

### 3. Regresyon modeli (`analysis/fit_circ_model.py`)

Her ölçüm için ayrı Polynomial Ridge (degree=2) modeli fit edildi:

| Ölçüm | Erkek R² | Kadın R² |
|---|---|---|
| waist_circ_cm | 0.993 | 0.996 |
| hip_circ_cm | 0.992 | 0.995 |
| neck_circ_cm | 0.986 | 0.991 |
| thigh_circ_cm | 0.982 | 0.988 |
| bicep_circ_cm | 0.895 | 0.905 |
| **chest_circ_cm** | **0.765** | **0.586** |

> **Önemli:** `chest_circ_cm` tahmini güvenilmez (R²=0.59–0.77). Bu nedenle göğüs/kalça oranına dayalı kurallar yerine `hip_score` slider'ı doğrudan kullanıldı.

### 4. Label türetme (`analysis/derive_labels.py`)

Model tüm 30.000 satır için `waist_circ_pred_cm` ve `hip_circ_pred_cm` üretir. Somatotip bu tahminler + slider değerlerinden deterministik olarak atanır.

---

## Sınıflandırma Kuralları

Sıralı kural zinciri — her karakter ilk uyan kurala girer:

```
waist_pred / hip_pred ≥ 0.90
    → apple

hip_score < 0.45  AND  fat_score < 0.25  AND  (gender == male OR muscle_score > 0.60)
    → v_shape

hip_score ∈ [0.48, 0.62]  AND  waist_def_score ≥ 0.70  AND  waist_pred/hip_pred < 0.83
    → hourglass

hip_score ≥ 0.58  AND  waist_pred/hip_pred < 0.89
    → pear

else
    → rectangle
```

### Kural tasarım gerekçeleri

**Apple:** `waist/hip` oranı R²=0.99 ile güvenilir şekilde tahmin ediliyor. Eşik 0.90 — kalibrasyon verilerinde apple karakterlerin gerçek ölçümlerinden türetildi.

**V_shape:** Göğüs tahmini güvenilmez olduğundan `chest/hip` oranı yerine `hip_score` slider'ı kullanıldı. Anatomik olarak erkek vücuduna özgü; kadınlarda yalnızca yüksek kas + çok dar kalça kombinasyonunda oluşur.

**Hourglass:** Üç koşulun aynı anda sağlanması gerekiyor: nötr kalça (göğüs ≈ kalça), yüksek bel tanımı, dar bel. Bu nedenle nadir (%0.4).

**Pear:** `hip_score` slider'ı kalça genişliğini doğrudan kontrol ettiğinden, tahmin hatası yüksek `chest/hip` oranı yerine `hip_score` kullanıldı.

**Rectangle:** Diğer hiçbir kurala uymayan — varsayılan kategori.

---

## Dağılım İstatistikleri

| Somatotip | n | % | Fat aralığı | Hip_score aralığı | Waist/hip aralığı |
|---|---|---|---|---|---|
| rectangle | 12,249 | %40.8 | 0.005–0.863 | 0.204–0.893 | 0.822–0.900 |
| pear | 10,398 | %34.7 | 0.001–0.713 | 0.580–0.897 | 0.805–0.890 |
| apple | 4,719 | %15.7 | **0.417**–0.997 | 0.202–0.891 | 0.900–0.984 |
| v_shape | 2,524 | %8.4 | 0.003–**0.250** | 0.203–**0.450** | 0.826–0.885 |
| hourglass | 110 | %0.4 | 0.007–**0.134** | **0.484–0.620** | 0.813–**0.830** |

### Grup kırılımları

**Apple:** obese %86 + overweight %14 — yüksek fat zorunlu  
**Hourglass:** athletic_hyper %68 + underweight %24 — lean zorunlu  
**V_shape:** erkek %80, athletic/lean ağırlıklı  
**Pear:** tüm gruplar, muscle'dan bağımsız  
**Rectangle:** tüm gruplar, en geniş dağılım

### Fiziksel tutarlılık garantileri

- **Şişman hourglass yok:** Fat arttıkça bel genişler → `waist/hip < 0.83` koşulu yüksek fat'ta matematiksel olarak karşılanamaz (max fat = 0.134)
- **Şişman v_shape yok:** Kural `fat < 0.25` ile sınırlandırılmış (max fat = 0.250)
- **Apple min fat = 0.417:** `waist/hip ≥ 0.90` eşiği düşük fat'ta hiçbir zaman karşılanmıyor

---

## Güncelleme Prosedürü

Morph formülleri (`cc5_helpers.py`) veya dataset parametreleri değişirse:

1. `props/calibration_export.py` → CC5'te yeni FBX export
2. `pipeline.py --fbx-dir fbx_export/calib` → Blender ölçümü
3. `python analysis/fit_circ_model.py` → model yeniden fit
4. `python analysis/derive_labels.py` → dataset.csv güncelle

Eşiklerin kalibrasyonu için `analysis/calib_report.txt` referans alınabilir.

# Veri Seti Analiz Raporu

> **7218 karakterlik birlesik veri seti** (ANSUR II: 6068 + Extreme BMI: 1150)
> Kadin: 2686 | Erkek: 4532

---

## 1. BMI Dagilimi

![](../analysis/dataset_plots/01_bmi_distribution.png)

| Kategori | Kadin | Erkek | Toplam | Oran |
|---|---|---|---|---|
| Underweight | 313 | 159 | 472 | 6.5% |
| Normal | 936 | 1061 | 1997 | 27.7% |
| Overweight | 847 | 1904 | 2751 | 38.1% |
| Obese I | 171 | 921 | 1092 | 15.1% |
| Obese II | 167 | 287 | 454 | 6.3% |
| Obese III | 252 | 200 | 452 | 6.3% |

**Degerlendirme:**
- Underweight ve Obese II/III artik yeterli temsile sahip (her biri ~450+ karakter)
- Normal ve Overweight dominant — fitness uygulamasinin hedef kitlesini dogru yansıtıyor
- Kadin/erkek orani tum gruplarda dengeli

---

## 2. Vucut Yag Orani (Navy BFP)

![](../analysis/dataset_plots/02_navy_bfp_distribution.png)

| | Kadin ort. | Kadin std | Erkek ort. | Erkek std |
|---|---|---|---|---|
| Navy BFP % | 37.7 | 12.5 | 22.1 | 8.0 |

**Degerlendirme:**
- Kadin yag orani 17–62% arasinda dagiliyor — hem atletik hem obez profiller mevcut
- Erkek yag orani 9–36%
- Skinny detail morphlari dusuk BFP'de (<22%% kadin, <13%% erkek) aktive oluyor

---

## 3. Cevre Olcumleri — BMI Kategorisine Gore

![](../analysis/dataset_plots/03_circumference_by_bmi.png)

Her kategori icerisinde gercek insan varyasyonu korunuyor (violin genisligi = yogunluk).
Underweight ve Obese gruplarda cevre olcumleri beklenen yonde ayrisiyor.

---

## 4. Uzunluk Olcumleri

![](../analysis/dataset_plots/04_length_distributions.png)

| Olcum | Kadin P5 | Kadin P95 | Erkek P5 | Erkek P95 |
|---|---|---|---|---|
| Boy | 152.5 | 174.0 | 164.8 | 187.0 |
| Omuz gen. | 38.5 | 56.7 | 45.0 | 59.1 |
| Kalca gen. | 29.6 | 45.4 | 30.3 | 40.3 |
| Ust kol uz. | 30.7 | 36.2 | 33.4 | 39.4 |
| On kol uz. | 21.8 | 26.8 | 24.4 | 29.5 |
| Ust bacak uz. | 37.0 | 44.7 | 39.0 | 48.1 |
| Alt bacak uz. | 39.8 | 47.9 | 42.6 | 51.3 |

**Not:** Uzunluk olcumleri BMI'dan bagimsiz — boy, kol ve bacak uzunluklari
tum BMI kategorilerinde benzer dagilim gosteriyor. Bu model icin onemli:
ayni BMI'da farkli prop oranlarina sahip kisiler temsil ediliyor.

---

## 5. Vucut Sekli Oranlari

![](../analysis/dataset_plots/05_body_shape_ratios.png)

| Oran | Kadin P10 | Kadin P50 | Kadin P90 | Erkek P10 | Erkek P50 | Erkek P90 |
|---|---|---|---|---|---|---|
| WHR (bel/kalca) | 0.753 | 0.842 | 0.949 | 0.841 | 0.921 | 1.011 |
| SHR (omuz/kalca gen.) | 1.188 | 1.270 | 1.365 | 1.390 | 1.477 | 1.570 |

---

## 6. Somatotype Dagilimi

![](../analysis/dataset_plots/06_somatotype_distribution.png)

| Somatotype | Kadin | Erkek |
|---|---|---|
| apple | 264 (10%) | 643 (14%) |
| hourglass | 351 (13%) | 81 (2%) |
| pear | 1443 (54%) | 104 (2%) |
| rectangle | 525 (20%) | 2024 (45%) |
| v_shape | 103 (4%) | 1680 (37%) |

---

## 7. Morph Inversion Kalitesi

![](../analysis/dataset_plots/07_inversion_mae.png)

| Kaynak | Ort. MAE | Medyan | P75 | P95 | Max |
|---|---|---|---|---|---|
| ANSUR | 0.74 cm | 0.49 cm | 1.04 cm | 2.41 cm | 5.15 cm |
| Extreme | 2.39 cm | 1.98 cm | 3.52 cm | 5.34 cm | 7.54 cm |

**Degerlendirme:**
- ANSUR inversiyonu cok iyi: medyan ~0.5 cm, P95 ~2.5 cm
- Extreme BMI inversiyonu kabul edilebilir: medyan ~2 cm, BMI artikca MAE artiyor
- MAE > 5 cm olan karakterler (~%5) CC5 morph uzayinin sinirinda — gorsel olarak
  dogru yonde ama hassasiyetten odun verilmis

---

## 8. Olcum Uzayi Kapsami

![](../analysis/dataset_plots/08_coverage_scatter.png)

Scatter plotlar, kadin ve erkek karakterlerin olcum uzayinda nasil dagildığini gosteriyor.
Extreme BMI verisi (pembe) ANSUR'un (mavi) dolduramadigi bölgeleri kapsıyor.

---

## 9. Ozet Istatistik Tablosu

![](../analysis/dataset_plots/09_summary_table.png)

---

## 10. Korelasyon Analizi

![](../analysis/dataset_plots/10_correlation_matrix.png)

**Yuksek korelasyonlar (|r| > 0.80, kadin):**

- **BMI ↔ BFP%**: r = 0.97
- **BMI ↔ Boyun**: r = 0.91
- **BMI ↔ Gogus**: r = 0.95
- **BMI ↔ Bel**: r = 0.96
- **BMI ↔ Kalca**: r = 0.96
- **BMI ↔ Uyluk**: r = 0.96
- **BMI ↔ Baldır**: r = 0.92
- **BMI ↔ Bicep**: r = 0.96
- **BMI ↔ On kol**: r = 0.93
- **BMI ↔ Omuz gen.**: r = 0.94
- **BMI ↔ Kalca gen.**: r = 0.92
- **BFP% ↔ Boyun**: r = 0.87
- **BFP% ↔ Gogus**: r = 0.94
- **BFP% ↔ Bel**: r = 0.98
- **BFP% ↔ Kalca**: r = 0.96
- **BFP% ↔ Uyluk**: r = 0.95
- **BFP% ↔ Baldır**: r = 0.87
- **BFP% ↔ Bicep**: r = 0.93
- **BFP% ↔ On kol**: r = 0.88
- **BFP% ↔ Omuz gen.**: r = 0.92
- **BFP% ↔ Kalca gen.**: r = 0.93
- **Boyun ↔ Gogus**: r = 0.91
- **Boyun ↔ Bel**: r = 0.91
- **Boyun ↔ Kalca**: r = 0.89
- **Boyun ↔ Uyluk**: r = 0.88
- **Boyun ↔ Baldır**: r = 0.84
- **Boyun ↔ Bicep**: r = 0.91
- **Boyun ↔ On kol**: r = 0.90
- **Boyun ↔ Omuz gen.**: r = 0.91
- **Boyun ↔ Kalca gen.**: r = 0.85
- **Gogus ↔ Bel**: r = 0.95
- **Gogus ↔ Kalca**: r = 0.93
- **Gogus ↔ Uyluk**: r = 0.92
- **Gogus ↔ Baldır**: r = 0.86
- **Gogus ↔ Bicep**: r = 0.93
- **Gogus ↔ On kol**: r = 0.89
- **Gogus ↔ Omuz gen.**: r = 0.95
- **Gogus ↔ Kalca gen.**: r = 0.90
- **Bel ↔ Kalca**: r = 0.94
- **Bel ↔ Uyluk**: r = 0.93
- **Bel ↔ Baldır**: r = 0.86
- **Bel ↔ Bicep**: r = 0.93
- **Bel ↔ On kol**: r = 0.89
- **Bel ↔ Omuz gen.**: r = 0.94
- **Bel ↔ Kalca gen.**: r = 0.92
- **Kalca ↔ Uyluk**: r = 0.98
- **Kalca ↔ Baldır**: r = 0.92
- **Kalca ↔ Bicep**: r = 0.94
- **Kalca ↔ On kol**: r = 0.91
- **Kalca ↔ Omuz gen.**: r = 0.93
- **Kalca ↔ Kalca gen.**: r = 0.98
- **Uyluk ↔ Baldır**: r = 0.93
- **Uyluk ↔ Bicep**: r = 0.95
- **Uyluk ↔ On kol**: r = 0.92
- **Uyluk ↔ Omuz gen.**: r = 0.93
- **Uyluk ↔ Kalca gen.**: r = 0.95
- **Baldır ↔ Bicep**: r = 0.91
- **Baldır ↔ On kol**: r = 0.91
- **Baldır ↔ Omuz gen.**: r = 0.88
- **Baldır ↔ Kalca gen.**: r = 0.89
- **Bicep ↔ On kol**: r = 0.95
- **Bicep ↔ Omuz gen.**: r = 0.94
- **Bicep ↔ Kalca gen.**: r = 0.90
- **On kol ↔ Omuz gen.**: r = 0.92
- **On kol ↔ Kalca gen.**: r = 0.87
- **Boy ↔ Ust kol uz.**: r = 0.82
- **Omuz gen. ↔ Kalca gen.**: r = 0.90

Bu yuksek korelasyonlar beklenen: kalin bilekli kisinin forearm ve bicep de
kalin olmasi dogal. Model bu korelasyonlari veri setinden ogrenmeli.

---

## Genel Yeterlilik Degerlendirmesi

| Kriter | Durum | Aciklama |
|---|---|---|
| BMI kapsami | ✅ | Underweight–Obese III tum kategoriler temsil ediliyor |
| Kadin/erkek dengesi | ✅ | Her BMI grubunda her iki cinsiyet mevcut |
| Varyasyon (ayni BMI'da farkli sekil) | ✅ | Residual bootstrap sayesinde korunuyor |
| Inversion kalitesi (ANSUR) | ✅ | Medyan MAE < 1 cm |
| Inversion kalitesi (Extreme) | ⚠️ | Medyan ~2 cm, BMI 40+ icin 3-5 cm |
| Uzuv varyasyonu | ✅ | Segment uzunluklari BMI'dan bagimsiz dagilıyor |
| Somatotype cesitliligi | ✅ | 5 tip her iki cinsiyette mevcut |
| CC5 morph siniri (BMI 45+) | ⚠️ | Morph uzayi sinirda, gorsel olarak dogru yonde |
| Genel populasyon kapsami | ✅ | Extreme eklenmesiyle bosluklar kapandi |

### Kalibrasyon Oncelik Sirasi
1. **Bel cevresi** — en yuksek bireysel varyasyon, model icin en kritik
2. **Uyluk ve baldır** — alt vucut obezitesinde sınır tespiti zor
3. **Omuz genisligi** — SHR hatasi yuksek, obez modellerde dikkat
4. **Kol uzunlugu** — az degisken, model kolayca ogrenmeli

---

> Rapor otomatik olarak `analysis/dataset_analysis.py` tarafindan uretilmistir.

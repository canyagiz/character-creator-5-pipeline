# Model Mimarisi — Body Measurement Regressor

## Genel Fikir

Kullanıcıdan 8 farklı açıdan fotoğraf alınır. Her fotoğraf için dış modeller silhouette ve normal map üretir. Kullanıcı ayrıca boy ve kilo girer. Model bu girdilerden 26 vücut ölçümü tahmin eder.

Maskelerin amacı şu: modelin `bicep_circ_cm` tahminini düşürmek için tüm vücudun feature'ına bakması yerine, kol bölgesinin feature'ına odaklanması. Bu hem öğrenmeyi hızlandırır hem de tahminleri stabil kılar.

---

## Girdiler

### Eğitim zamanı (her sample için)

| Girdi | Boyut | Kaynak |
|---|---|---|
| normal_map | [8, 3, H, W] | Blender pipeline |
| silhouette | [8, 1, H, W] | Blender pipeline |
| seg_mask (GT) | [8, H, W] — integer class map | Blender pipeline |
| height_cm | scalar | meta.json |
| weight_kg | scalar | meta.json (volume_L'den türetilecek) |
| targets | [26] | meta.json |

8 görüş: `front, back, left, right, front_left, front_right, back_left, back_right`

### Inference zamanı

| Girdi | Kaynak |
|---|---|
| normal_map × 8 | DSINE / StableNormal modeli |
| silhouette × 8 | Ayrı segmentasyon modeli |
| height_cm, weight_kg | Kullanıcıdan alınır |

Seg mask inference'ta **yoktur** — model kendi seg mask'ını kendisi üretir (seg head, eğitimde GT mask ile supervised edilir; inference'ta kendi tahmini kullanılır).

---

## Adım Adım Akış

### Adım 1 — Girdi hazırlama (her görüş için ayrı)

```
normal_map  [3, 256, 256]
silhouette  [1, 256, 256]
     │
  concat(dim=0)
     │
  [4, 256, 256]   ←── backbone'a girecek
```

Normal map yüzey normallerini (3D eğimi) encode eder. Silhouette vücudun dış sınırını verir — genişlik, oran ve arka plan/ön plan ayrımı için.

---

### Adım 2 — Backbone (EfficientNet-B3, pretrained)

```
[4, 256, 256]
     │
  Stage 1  →  feat_128  [24,  128, 128]
  Stage 2  →  feat_64   [32,   64,  64]   ←── skip connection (seg head için saklanır)
  Stage 3  →  feat_32   [48,   32,  32]   ←── skip connection (seg head için saklanır)
  Stage 4  →  feat_16   [136,  16,  16]
  Stage 5  →  F         [1536,  8,   8]   ←── ana feature map
```

EfficientNet-B3 ImageNet ağırlıklarıyla başlar. İlk katman 3 kanal yerine 4 kanal alacak şekilde değiştirilir (mevcut ağırlıklar korunur, 4. kanal için ağırlıklar sıfırdan öğrenilir).

`F` her şeyin çıkış noktası. 8×8 spatial grid, her hücre yaklaşık 32×32 piksellik bir bölgeyi temsil ediyor. 1536 kanal o bölgenin ne olduğunu encode ediyor.

---

### Adım 3 — Seg Head (skip connection'lı decoder)

Amaç: `F`'den başlayarak giderek yüksek çözünürlüklü bir seg mask tahmini üretmek. GT mask ile bu tahmin supervision edilir.

```
F  [1536, 8, 8]
     │
  ConvTranspose2d  →  upsample  →  [256, 16, 16]
     │
  concat(feat_32 [48, 32, 32] → 1×1 Conv → [256, 32, 32])   ←── skip
     │
  Conv  →  [256, 32, 32]
     │
  ConvTranspose2d  →  upsample  →  [128, 64, 64]
     │
  concat(feat_64 [32, 64, 64] → 1×1 Conv → [128, 64, 64])   ←── skip
     │
  Conv  →  [128, 64, 64]
     │
  Conv 1×1  →  [K, 64, 64]   ←── K = bölge sayısı (~14-15)
     │
  softmax(dim=0)              ←── her piksel için K bölge üzerinde olasılık dağılımı
     │
  seg_pred  [K, 64, 64]
```

**Eğitimde:** `seg_pred` ile GT mask arasında CrossEntropy loss hesaplanır. Gradient hem decoder'a hem backbone'a akar — backbone "bu bölge kol" gibi sinyalleri backbone feature'larına encode etmeyi öğrenir.

**Inference'ta:** GT mask yok ama seg head yine çalışır, kendi tahminini üretir. Bu tahmin bir sonraki adımda attention olarak kullanılır.

---

### Adım 4 — Masked Pooling

`F` tüm vücudun feature'larını içeriyor. `seg_pred` hangi pikselin hangi bölgeye ait olduğunu söylüyor. Bu ikisini birleştirerek her bölge için ayrı bir feature vektörü üretiriz.

```
seg_pred  [K, 64, 64]
     │
  interpolate(size=8×8)     ←── F ile aynı çözünürlüğe indir
     │
  seg_weights  [K, 8, 8]

F  [1536, 8, 8]

Her bölge k için:
  weighted_feat_k = sum(F × seg_weights[k]) / sum(seg_weights[k])
                  = [1536]    ←── o bölgenin özelliği

  Örnek:
    k=arm    →  weighted_feat_arm  [1536]   (kol bölgesinin feature'ı)
    k=torso  →  weighted_feat_torso [1536]  (gövdenin feature'ı)
    ...

global_feat = mean(F, dim=(H,W))  =  [1536]   (tüm vücudun genel feature'ı)

view_feature = concat([region_0, region_1, ..., region_K-1, global_feat])
             = [(K+1) × 1536]
```

Bu noktada `view_feature` içinde:
- K adet bölgeye özgü özellik
- 1 adet global özellik

hepsi bir arada. Bu tek bir görüşün tam temsili.

---

### Adım 5 — 8 Görüş Aggregation

Adım 2-4 her görüş için ayrı ayrı çalışır. Şimdi 8 görüşü birleştiriyoruz.

```
Görüş 0 (front)        →  view_feature_0  [(K+1)×1536]
Görüş 1 (back)         →  view_feature_1  [(K+1)×1536]
...
Görüş 7 (back_right)   →  view_feature_7  [(K+1)×1536]

     │
  Linear projection (shared weights, tüm görüşler için aynı katman)
     │
  [8, 512]

     │
  View Attention:
    her görüş için bir skor üret  →  [8, 1]
    softmax  →  [8, 1]    ←── hangi açı bu ölçüm için daha bilgilendirici?
    weighted sum
     │
  global_embed  [512]
```

Attention ağırlıkları eğitimde öğrenilir. Örneğin `shoulder_width` için `back` görüşü daha yüksek ağırlık alabilir, `bicep_circ` için `front_left` veya `front_right` daha önemli olabilir.

Projeksiyon ağırlıkları tüm görüşler arasında paylaşılır — aynı encoder, 8 farklı açı için çalışır.

---

### Adım 6 — FiLM Conditioning (boy + kilo)

Boy ve kilo, `global_embed`'in nasıl yorumlanacağını değiştirir.

```
[height_cm, weight_kg]
     │
  normalize  →  [(height - mean_h) / std_h, (weight - mean_w) / std_w]
     │
  küçük MLP  (2 → 128 → 512 → 512)
     │
  iki çıkış:
    gamma  [512]
    beta   [512]

global_embed [512]  ×  gamma  +  beta  =  conditioned_embed [512]
```

Aynı vücut şekline sahip iki kişiyi düşün: biri 160cm, diğeri 190cm. Silhouette ve normal map'leri çok benzer görünür. Model görsel feature'lardan boyları ayırt edemez. FiLM burada devreye girer — boy bilgisi `global_embed`'in tüm boyutlarını ölçekler ve kaydırır, MLP bunu zaten "boylanmış" bir feature olarak görür.

---

### Adım 7 — Regression Head

```
conditioned_embed  [512]
     │
  Linear(512, 256)  →  GELU
  Dropout(0.3)
  Linear(256, 128)  →  GELU
  Linear(128, 26)
     │
  predictions  [26]   ←── z-score normalized (eğitimde)
```

26 çıkış z-score normalize edilmiş değerler. Loss hesaplanırken GT da aynı şekilde normalize edilir.

Soft routing burada implicit olarak gerçekleşir: MLP'nin ilk katman ağırlıkları `[512, 256]` boyutunda. `bicep_circ_cm` çıkışına giden ağırlıklar, `conditioned_embed` içindeki kol bölgesi feature'larına yüksek değer verecek şekilde öğrenilir. Ayrı bir routing mekanizması gerekmez.

---

### Adım 8 — Loss

```
L_measurement  =  Huber(predictions, targets)
                  (26 ölçümün normalize edilmiş değerleri üzerinde)

L_seg  =  CrossEntropy(seg_pred [K, 64, 64], gt_mask [64, 64])
          (eğitimde her görüş için, K sınıf üzerinde)

L_total  =  L_measurement  +  λ × L_seg

λ başlangıçta 0.5, ilerleyen epoch'larda azaltılabilir.
```

`L_seg` backbone'u "anlamlı bölgeler gör" diye zorlar. `L_measurement` ise "doğru ölçüm tahmin et" der. İkisi birlikte backbone'u hem shape-aware hem measurement-aware yapar.

---

## Inference Akışı (özet)

```
Kullanıcı:
  8 fotoğraf  →  dış model  →  8 normal_map + 8 silhouette
  height_cm, weight_kg

Model:
  Her görüş için:
    [normal_map, silhouette]  →  Backbone  →  F + skip feats
    F + skip feats  →  Seg Head  →  seg_pred  (GT yok, kendi tahmini)
    F × seg_pred  →  Masked Pooling  →  view_feature

  8 view_feature  →  View Attention  →  global_embed
  [height, weight]  →  FiLM  →  conditioned_embed
  conditioned_embed  →  MLP  →  26 ölçüm  (cm / L cinsinden denormalize edilir)
```

---

## Parametre Sayısı (yaklaşık)

| Modül | Parametre |
|---|---|
| EfficientNet-B3 backbone | ~10.7M |
| Seg Head decoder | ~2M |
| View projection + attention | ~10M (K=14 → view_dim=23040) |
| FiLM MLP | ~0.3M |
| Regression Head | ~0.2M |
| **Toplam** | **~23M** |

7286 sample için pretrained backbone ile bu büyüklük makul. Backbone dondurularak (frozen) başlanıp sonra açılabilir (fine-tune).

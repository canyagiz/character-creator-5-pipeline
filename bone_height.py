"""
Skeleton kemiklerinden avatar yüksekliğini hesaplar.
Kafa ve ayak kemiklerinin T-pose Z pozisyonları arasındaki farkı alır.
"""

import RLPy

avatar = RLPy.RScene.GetAvatars()[0]
skel   = avatar.GetSkeletonComponent()

_buf = []
def log(msg=""): _buf.append(str(msg))

# ── Tüm kemik isimlerini listele ──────────────────────────────
raw        = list(skel.GetBoneQniqueNames())
bone_names = [b.GetName() if hasattr(b, "GetName") else str(b) for b in raw]
bone_nodes = {bone_names[i]: raw[i] for i in range(len(raw))}
log(f"Toplam kemik: {len(bone_names)}")
log("")

# Kafa / ayak / kalça ile ilgili kemikleri filtrele
keywords = ["head", "foot", "hip", "neck", "spine", "toe", "heel", "pelvis"]
relevant = [b for b in bone_names if any(k in b.lower() for k in keywords)]
log("İlgili kemikler:")
for b in relevant:
    log(f"  {b}")

log("")

# ── Seçilen kemiklerin T-pose Z pozisyonlarını al ────────────
log("T-pose Z pozisyonları:")
z_values = {}

# İlk kemikle API'yi test et — hatayı görmek için
first_name = bone_names[0]
first_node = bone_nodes[first_name]
for arg in [first_name, first_node]:
    try:
        pos = skel.GetBoneTPosePosition(arg)
        log(f"  [{type(arg).__name__}] {first_name}: pos={pos}, tip={type(pos)}")
        break
    except Exception as e:
        log(f"  [{type(arg).__name__}] hata: {e}")

# Tüm kemikler — node ile dene
for name, node in bone_nodes.items():
    for arg in [node, name]:
        try:
            pos = skel.GetBoneTPosePosition(arg)
            z_values[name] = pos.z
            break
        except Exception:
            pass

# En yüksek ve en alçak Z'yi bul
if z_values:
    sorted_z = sorted(z_values.items(), key=lambda x: x[1])
    log(f"  En alçak 5 kemik:")
    for name, z in sorted_z[:5]:
        log(f"    {name}: z={z:.4f}")
    log(f"  En yüksek 5 kemik:")
    for name, z in sorted_z[-5:]:
        log(f"    {name}: z={z:.4f}")

    log("")
    top_z    = sorted_z[-1][1]
    bottom_z = sorted_z[0][1]
    log(f"  Maks Z ({sorted_z[-1][0]}): {top_z:.4f}")
    log(f"  Min Z  ({sorted_z[0][0]}):  {bottom_z:.4f}")
    log(f"  Fark (kemik yüksekliği): {top_z - bottom_z:.4f} cm")

print("\n".join(_buf))

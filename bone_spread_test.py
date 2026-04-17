"""
Kol kemiklerinin T-pose pozisyonunu okur, X ekseninde dışa kaydırır,
sonra sıfırlar. SetBoneTPosePosition'ın çalışıp çalışmadığını test eder.
"""

import RLPy

avatar = RLPy.RScene.GetAvatars()[0]
skel   = avatar.GetSkeletonComponent()

_buf = []
def log(msg=""): _buf.append(str(msg))

ARM_KEYWORDS = ["upperarm", "forearm", "hand"]
TEST_OFFSET  = 10.0  # cm

# Tüm kemik node'larını isimle eşle
all_nodes = list(skel.GetBoneQniqueNames())
bone_map  = {n.GetName(): n for n in all_nodes if hasattr(n, "GetName")}
arm_bones = {name: node for name, node in bone_map.items()
             if any(k in name.lower() for k in ARM_KEYWORDS)}

log("── Bulunan kol kemikleri ──")
for name in sorted(arm_bones):
    log(f"  {name}")

log("")
log("── Mevcut pozisyonlar ──")
original = {}
for name, node in arm_bones.items():
    try:
        pos = skel.GetBoneTPosePosition(node)
        original[name] = (pos.x, pos.y, pos.z)
        log(f"  {name}: x={pos.x:.3f}, y={pos.y:.3f}, z={pos.z:.3f}")
    except Exception as e:
        log(f"  {name} HATA: {e}")

log("")
log("── Offset uygulama ──")
for name, node in arm_bones.items():
    if name not in original:
        continue
    ox, oy, oz = original[name]
    new_x = ox - TEST_OFFSET if "_L_" in name else ox + TEST_OFFSET
    try:
        result = skel.SetBoneTPosePosition(node, RLPy.RVector3(new_x, oy, oz))
        log(f"  {name}: x {ox:.3f} -> {new_x:.3f}  (result={result})")
    except Exception as e:
        log(f"  {name} SET HATA: {e}")

RLPy.RGlobal.ForceViewportUpdate()
log("")
log("Viewport güncellendi — fark görülüyorsa SetBoneTPosePosition çalışıyor.")
log("Scripti tekrar çalıştırarak sıfırlayabilirsin (offset=0 ile).")

print("\n".join(_buf))

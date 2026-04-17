import RLPy

avatar  = RLPy.RScene.GetAvatars()[0]
shaping = avatar.GetAvatarShapingComponent()

M_SCALE = "2018-09-14-22-07-28_character scale"

def get_bbox_height():
    kMax    = RLPy.RVector3(0, 0, 0)
    kCenter = RLPy.RVector3(0, 0, 0)
    kMin    = RLPy.RVector3(0, 0, 0)
    avatar.GetBounds(kMax, kCenter, kMin)
    return kMax.y - kMin.y

# Character Scale A = 0.0 / +1.0 / -1.0 noktalarinda bbox olc
results = {}
for w in [0.0, 1.0, -1.0]:
    shaping.SetShapingMorphWeight(M_SCALE, w)
    RLPy.RGlobal.ForceViewportUpdate()
    results[w] = get_bbox_height()

shaping.SetShapingMorphWeight(M_SCALE, 0.0)
RLPy.RGlobal.ForceViewportUpdate()

print(f"W= 0.0 -> bbox_h = {results[ 0.0]:.4f}")
print(f"W=+1.0 -> bbox_h = {results[ 1.0]:.4f}")
print(f"W=-1.0 -> bbox_h = {results[-1.0]:.4f}")
print()
print("CC5 UI'dan avatarin gercek yuksekligini (cm) kontrol et ve asagiya yaz:")
print("  Modify panel > Transform > Scale veya avatar ozelliklerine bak")

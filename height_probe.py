"""
Height Probe Script
Avatarın gerçek yüksekliğini CC5 API'den dinamik olarak almanın
tüm olası yollarını dener ve sonuçları raporlar.
Beklenen değer: 167.76 cm (Ariana)
"""

import RLPy

KNOWN_HEIGHT_CM = 167.76

avatar  = RLPy.RScene.GetAvatars()[0]
shaping = avatar.GetAvatarShapingComponent()

_buf = []
def log(msg=""):
    _buf.append(str(msg))

def print_list(label, items):
    log(f"  {label} ({len(items)}):")
    for item in items:
        log(f"    {item}")

log("=" * 60)
log(f"Avatar: {avatar.GetName()}")
log("=" * 60)

# ── 1. GetBounds — tüm eksenler ────────────────────────────────
log("\n── 1. GetBounds (tüm eksenler) ──")
kMax    = RLPy.RVector3(0, 0, 0)
kCenter = RLPy.RVector3(0, 0, 0)
kMin    = RLPy.RVector3(0, 0, 0)
avatar.GetBounds(kMax, kCenter, kMin)

log(f"  kMax    : ({kMax.x:.4f}, {kMax.y:.4f}, {kMax.z:.4f})")
log(f"  kCenter : ({kCenter.x:.4f}, {kCenter.y:.4f}, {kCenter.z:.4f})")
log(f"  kMin    : ({kMin.x:.4f}, {kMin.y:.4f}, {kMin.z:.4f})")
log(f"  X span  : {kMax.x - kMin.x:.4f}")
log(f"  Y span  : {kMax.y - kMin.y:.4f}")
log(f"  Z span  : {kMax.z - kMin.z:.4f}")

for label, val in [("X", kMax.x - kMin.x), ("Y", kMax.y - kMin.y), ("Z", kMax.z - kMin.z)]:
    ratio = KNOWN_HEIGHT_CM / val if val != 0 else float('inf')
    match = "MUHTEMEL YUKSEKLIK" if 150 < val < 220 else f"cm_per_unit: {ratio:.4f}"
    log(f"  {label}={val:.4f} / {KNOWN_HEIGHT_CM}cm -> {match}")

# ── 2. Transform (Local & World) ───────────────────────────────
log("\n── 2. Transform (Local & World) ──")
for name, t in [("Local", avatar.LocalTransform()), ("World", avatar.WorldTransform())]:
    try:
        T = t.T(); S = t.S()
        log(f"  {name} T: ({T.x:.4f}, {T.y:.4f}, {T.z:.4f})")
        log(f"  {name} S: ({S.x:.4f}, {S.y:.4f}, {S.z:.4f})")
    except Exception as e:
        log(f"  {name}Transform hata: {e}")

# ── 3. GetPivot ────────────────────────────────────────────────
log("\n── 3. GetPivot ──")
try:
    kPos = RLPy.RVector3(0, 0, 0)
    kOri = RLPy.RVector3(0, 0, 0)
    avatar.GetPivot(kPos, kOri)
    log(f"  pos: ({kPos.x:.4f}, {kPos.y:.4f}, {kPos.z:.4f})")
    log(f"  ori: ({kOri.x:.4f}, {kOri.y:.4f}, {kOri.z:.4f})")
except Exception as e:
    log(f"  GetPivot hata: {e}")

# ── 4. SkeletonComponent ───────────────────────────────────────
log("\n── 4. SkeletonComponent ──")
try:
    skel = avatar.GetSkeletonComponent()
    print_list("Metodlar", [m for m in dir(skel) if not m.startswith("_")])
    for method_name in ["GetBoneCount", "GetRootBone", "GetBoneObjects",
                        "GetBones", "GetBoneObject", "FindBone", "GetAllBoneObjects"]:
        if hasattr(skel, method_name):
            try:
                result = getattr(skel, method_name)()
                log(f"  {method_name}() = {result}")
            except Exception as e:
                log(f"  {method_name}() hata: {e}")
except Exception as e:
    log(f"  SkeletonComponent hata: {e}")

# ── 5. DataBlock — Object Height property ─────────────────────
log("\n── 5. DataBlock — Object Height ──")
for str_id in ["Object", "Avatar", "RAvatar", "Character", "", "Body"]:
    try:
        db = avatar.GetDataBlock(str_id)
        if db and db.IsValid():
            log(f"  GetDataBlock('{str_id}') -> GECERLI")
            try:
                names = db.GetPropertyNames()
                print_list("Properties", list(names))
            except Exception as e:
                log(f"    GetPropertyNames hata: {e}")
            for prop_name in ["Object Height", "Height", "height", "BodyHeight"]:
                try:
                    prop = db.GetProperty(prop_name)
                    log(f"    '{prop_name}' = {prop}")
                except Exception as e:
                    log(f"    '{prop_name}' hata: {e}")
        else:
            log(f"  GetDataBlock('{str_id}') -> gecersiz/None")
    except Exception as e:
        log(f"  GetDataBlock('{str_id}') hata: {e}")

# ── 6. ShapingComponent ────────────────────────────────────────
log("\n── 6. ShapingComponent ──")
try:
    print_list("Metodlar", [m for m in dir(shaping) if not m.startswith("_")])
    for method_name in ["GetBodyHeight", "GetHeight", "GetCharacterHeight",
                        "GetAvatarHeight", "GetMeasurement"]:
        if hasattr(shaping, method_name):
            try:
                result = getattr(shaping, method_name)()
                log(f"  {method_name}() = {result}")
            except Exception as e:
                log(f"  {method_name}() hata: {e}")
except Exception as e:
    log(f"  ShapingComponent hata: {e}")

# ── 7. GetFloorContactValue ────────────────────────────────────
log("\n── 7. FloorContactValue ──")
for etype in [0, 1, 2]:
    try:
        val = avatar.GetFloorContactValue(etype)
        log(f"  GetFloorContactValue({etype}) = {val}")
    except Exception as e:
        log(f"  GetFloorContactValue({etype}) hata: {e}")

# ── 8. Height morph MinMax ─────────────────────────────────────
log("\n── 8. Height morph MinMax ──")
height_morph_ids = [
    ("Chest Height",    "cc embed morphs/embed_torso112"),
    ("Hip Length",      "cc embed morphs/embed_torso4"),
    ("Thigh Length",    "cc embed morphs/embed_leg4"),
    ("Lower Leg Length","cc embed morphs/embed_leg5"),
]
for ui_name, mid in height_morph_ids:
    try:
        min_val, max_val = RLPy.RFloatVector(), RLPy.RFloatVector()
        shaping.GetShapingMorphMinMax(mid, min_val, max_val)
        log(f"  {ui_name}: min={list(min_val)}, max={list(max_val)}")
    except Exception as e:
        try:
            result = shaping.GetShapingMorphMinMax(mid)
            log(f"  {ui_name}: {result}")
        except Exception as e2:
            log(f"  {ui_name} hata: {e2}")

# ── 9. RGlobal ────────────────────────────────────────────────
log("\n── 9. RGlobal — ilgili metodlar ──")
try:
    keys = ["height", "measure", "size", "scale", "cm"]
    relevant = [m for m in dir(RLPy.RGlobal) if not m.startswith("_")
                and any(k in m.lower() for k in keys)]
    print_list("Ilgili", relevant)
except Exception as e:
    log(f"  RGlobal dir hata: {e}")

# ── 10. Avatar dir() ──────────────────────────────────────────
log("\n── 10. Avatar dir() ──")
try:
    all_methods = [m for m in dir(avatar) if not m.startswith("_")]
    keys = ["height", "measure", "size", "scale", "cm", "unit"]
    relevant = [m for m in all_methods if any(k in m.lower() for k in keys)]
    print_list("Height/size ilgili", relevant)
    print_list("Tum metodlar", all_methods)
except Exception as e:
    log(f"  Avatar dir hata: {e}")

log("\n" + "=" * 60)
log(f"BEKLENEN: {KNOWN_HEIGHT_CM} cm")
log("=" * 60)

print("\n".join(_buf))

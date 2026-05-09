"""
render_segmentation_masks.py — Blender background script
Vertex skin weight AGGREGATION ile morph-invariant bölge sınıflandırması.

Strateji:
  Her vertex için bone group weight toplamları hesaplanır:
    arm_total, trunk_total, head_total, neck_total, shoulder_total, leg_total, foot_total
  Dominant group → bölge; arm içi için bone-projection silindirleri (bone_len orantılı).
  Geometrik parametre yok → tüm morph'larda aynı davranış.

Palette (R, G, B):
  0  background  (0,   0,   0  )
  1  neck        (128, 0,   0  )
  2  chest       (255, 0,   0  )
  3  waist       (255, 128, 0  )
  4  hip         (255, 255, 0  )
  5  mid_thigh   (0,   255, 0  )
  6  calf        (0,   128, 0  )
  7  bicep       (0,   0,   255)
  8  elbow       (0,   128, 255)
  9  forearm     (0,   255, 255)
  10 wrist       (128, 0,   255)
  11 head        (255, 128, 255)
  12 foot        (128, 128, 128)
  13 hand        (255, 255, 255)
  14 trapezius   (153, 76,  25 )
  15 shoulder    (153, 255, 0  )

Kullanım:
  blender --background --python render_segmentation_masks.py -- <fbx_path> <out_dir>
"""

import bpy
import math
import sys
import os
import mathutils
import numpy as np

# ── Args ──────────────────────────────────────────────────────────────────────
argv     = sys.argv[sys.argv.index("--") + 1:]
fbx_path = argv[0]
out_dir  = argv[1]
os.makedirs(out_dir, exist_ok=True)
char_name = os.path.splitext(os.path.basename(fbx_path))[0]

# ── Import ────────────────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.fbx(filepath=fbx_path)

# ── Mesh + Armature ───────────────────────────────────────────────────────────
arm_obj   = next((o for o in scene.objects if o.type == 'ARMATURE'), None)
mesh_objs = [o for o in scene.objects if o.type == 'MESH']
if not arm_obj:  print("ERROR: Armature yok"); sys.exit(1)
if not mesh_objs: print("ERROR: Mesh yok");    sys.exit(1)

all_bb = []
for obj in mesh_objs:
    for c in obj.bound_box:
        all_bb.append(obj.matrix_world @ mathutils.Vector(c))
z_floor  = min(v.z for v in all_bb)
z_top    = max(v.z for v in all_bb)
height_m = z_top - z_floor
center_y = (max(v.y for v in all_bb) + min(v.y for v in all_bb)) / 2

def mesh_z_span(obj):
    zs = [(obj.matrix_world @ mathutils.Vector(c)).z for c in obj.bound_box]
    return min(zs), max(zs)

body_candidates = [o for o in mesh_objs
                   if (lambda zn, zx: zn < z_floor + height_m * 0.15
                                   and zx > z_floor + height_m * 0.70
                       )(*mesh_z_span(o))]
body_obj = max(body_candidates or mesh_objs, key=lambda o: len(o.data.vertices))
print(f"Body mesh: {body_obj.name} ({len(body_obj.data.vertices)} vertex)")

# ── Kemik yardımcıları ────────────────────────────────────────────────────────
pose_bones = arm_obj.pose.bones

def bone_world(name):
    return arm_obj.matrix_world @ pose_bones[name].head

def bone_z(name):
    return bone_world(name).z

def try_z(name, fallback):
    try:    return bone_z(name)
    except: return fallback

# ── Trunk z-seviyeleri ────────────────────────────────────────────────────────
z_chest     = try_z("CC_Base_L_Breast",    z_floor + height_m * 0.60)
z_waist     = try_z("CC_Base_Waist",       z_floor + height_m * 0.48)
z_thigh     = try_z("CC_Base_L_Thigh",     z_floor + height_m * 0.47)
z_hip       = z_thigh + (z_waist - z_thigh) * 0.15
z_calf_top  = try_z("CC_Base_L_Calf",      z_floor + height_m * 0.25)
z_mid_thigh = (z_thigh + z_calf_top) / 2
z_calf_mid  = try_z("CC_Base_L_CalfTwist02", z_floor + height_m * 0.12)
z_foot      = try_z("CC_Base_L_Foot",      z_floor + height_m * 0.02)
z_head      = try_z("CC_Base_Head",        z_floor + height_m * 0.87)
z_shoulder  = (try_z("CC_Base_L_Upperarm", z_floor + height_m * 0.78) +
               try_z("CC_Base_R_Upperarm", z_floor + height_m * 0.78)) / 2
z_neck_base = try_z("CC_Base_NeckTwist01", z_floor + height_m * 0.83)

TRUNK_ZONES = [
    (z_neck_base, 2),   # boyun altı / üst göğüs → göğüs (head class sadece bone-weight'ten gelir)
    (z_chest,     2),
    (z_waist,     3),
    (z_hip,       4),
    (z_foot,      12),
]

def nearest_trunk_class(z):
    return min(TRUNK_ZONES, key=lambda t: abs(t[0] - z))[1]

def trunk_class(wv):
    """Trunk vertex sınıfı: z_neck_base üstü arka → trapez, diğerleri z-Voronoi."""
    if wv.z >= z_neck_base and wv.y > center_y:  # yalnızca boyun tabanı üstü arka: trapez
        return 14
    return nearest_trunk_class(wv.z)

# ── Bone group sınıflandırması ────────────────────────────────────────────────
_ARM_STARTS = (
    "CC_Base_L_Upperarm", "CC_Base_R_Upperarm",
    "CC_Base_L_Forearm",  "CC_Base_R_Forearm",
    "CC_Base_L_Hand",     "CC_Base_R_Hand",
)
_LEG_STARTS = (
    "CC_Base_L_Thigh",    "CC_Base_R_Thigh",
    "CC_Base_L_Calf",     "CC_Base_R_Calf",
)
_FOOT_STARTS = ("CC_Base_L_Foot", "CC_Base_R_Foot")

def bone_group(bn):
    """Bone adını geniş bir bölge grubuna ('arm','head','neck','shoulder','leg','foot','trunk') map et."""
    bnu = bn.upper()
    if any(bn.startswith(p) for p in _ARM_STARTS):
        return 'arm'
    # Parmak kemikleri
    if any(k in bnu for k in ("FINGER", "THUMB", "INDEX", "PINKY", "RING", "MID")) and "TOE" not in bnu:
        return 'arm'
    if "NECKT" in bnu:
        return 'neck'
    if bn.startswith("CC_Base_Head") or any(k in bn for k in ("Eye", "Jaw", "FacialBone")):
        return 'head'
    if "Clavicle" in bn:
        return 'shoulder'
    if any(bn.startswith(p) for p in _LEG_STARTS):
        return 'leg'
    if any(bn.startswith(p) for p in _FOOT_STARTS) or "Toe" in bn:
        return 'foot'
    return 'trunk'

# ── Vertex group index → bone adı ────────────────────────────────────────────
vg_name = {vg.index: vg.name for vg in body_obj.vertex_groups}
print(f"Armature: {len(arm_obj.pose.bones)} bone | VGroup: {len(vg_name)}")

# ── Arm içi silindir subdivizyon ──────────────────────────────────────────────
# Sadece arm olduğu teyit edilen vertex'ler için çağrılır.
# Parametreler bone_len orantılı → morph-invariant.

def _seg(p0n, p1n, start_f, end_f, radius_f):
    p0, p1    = bone_world(p0n), bone_world(p1n)
    axis      = (p1 - p0).normalized()
    bone_len  = (p1 - p0).length
    seg_start = bone_len * start_f
    seg_end   = bone_len * end_f
    radius    = bone_len * radius_f
    def _t(wv):
        to_v = wv - p0
        proj = to_v.dot(axis)
        if proj < seg_start or proj > seg_end: return False
        return (to_v - axis * proj).length <= radius
    return _t

def _sphere(center_bone, ref_p0, ref_p1, radius_f):
    """Omuz eklemi gibi yuvarlak bölgeler için küre testi — bone_len orantılı."""
    center = bone_world(center_bone)
    p0, p1 = bone_world(ref_p0), bone_world(ref_p1)
    radius = (p1 - p0).length * radius_f
    def _t(wv):
        return (wv - center).length <= radius
    return _t

def _hand_cone(forearm_n, hand_n, radius_f=0.55, length_f=0.90, back_f=0.05):
    p_fore, p_hand = bone_world(forearm_n), bone_world(hand_n)
    fore_len = (p_hand - p_fore).length
    axis     = (p_hand - p_fore).normalized()
    radius   = fore_len * radius_f
    length   = fore_len * length_f
    back     = fore_len * back_f
    def _t(wv):
        to_v = wv - p_hand
        proj = to_v.dot(axis)
        if proj < -back or proj > length: return False
        return (to_v - axis * proj).length <= radius
    return _t

# Her kural: (class_id, test_fn) — ilk eşleşen kullanılır.
try:
    ARM_RULES = [
        # ← el (el en önce kontrol edilmeli)
        (13, _hand_cone("CC_Base_L_Forearm", "CC_Base_L_Hand")),
        (13, _hand_cone("CC_Base_R_Forearm", "CC_Base_R_Hand")),
        # bilek
        (10, _seg("CC_Base_L_Forearm", "CC_Base_L_Hand",    0.65, 1.15, 0.40)),
        (10, _seg("CC_Base_R_Forearm", "CC_Base_R_Hand",    0.65, 1.15, 0.40)),
        # ön kol
        (9,  _seg("CC_Base_L_Forearm", "CC_Base_L_Hand",    0.10, 0.65, 0.40)),
        (9,  _seg("CC_Base_R_Forearm", "CC_Base_R_Hand",    0.10, 0.65, 0.40)),
        # dirsek
        (8,  _seg("CC_Base_L_Upperarm", "CC_Base_L_Forearm", 0.55, 1.15, 0.42)),
        (8,  _seg("CC_Base_R_Upperarm", "CC_Base_R_Forearm", 0.55, 1.15, 0.42)),
        # omuz deltoid — omuz eklemi etrafında küre
        # radius = upperarm_len * 0.22 → kompakt deltoid, bicep'e girmez
        (15, _sphere("CC_Base_L_Upperarm", "CC_Base_L_Upperarm", "CC_Base_L_Forearm", 0.22)),
        (15, _sphere("CC_Base_R_Upperarm", "CC_Base_R_Upperarm", "CC_Base_R_Forearm", 0.22)),
        # bicep (geri kalan üst kol)
        (7,  _seg("CC_Base_L_Upperarm", "CC_Base_L_Forearm", 0.0,  1.10, 0.38)),
        (7,  _seg("CC_Base_R_Upperarm", "CC_Base_R_Forearm", 0.0,  1.10, 0.38)),
    ]
    _ARM_RULES_OK = True
except Exception as e:
    print(f"WARN: ARM_RULES oluşturulamadı: {e}")
    ARM_RULES = []
    _ARM_RULES_OK = False

def arm_subclass(wv):
    """Arm olduğu belirlenen vertex için silindir ile bicep/dirsek/önkol/bilek/el."""
    for cls, test in ARM_RULES:
        if test(wv):
            return cls
    return 7  # fallback: bicep

# Trunk sınıfı alan ama dirsek / önkol bölgesinde kalan vertex'ler için override.
try:
    _ARM_OVERRIDE_TESTS = [
        _seg("CC_Base_L_Upperarm", "CC_Base_L_Forearm", 0.50, 1.20, 0.44),
        _seg("CC_Base_R_Upperarm", "CC_Base_R_Forearm", 0.50, 1.20, 0.44),
        _seg("CC_Base_L_Forearm",  "CC_Base_L_Hand",    0.0,  1.10, 0.42),
        _seg("CC_Base_R_Forearm",  "CC_Base_R_Hand",    0.0,  1.10, 0.42),
    ]
    def _in_arm_override(wv):
        return any(t(wv) for t in _ARM_OVERRIDE_TESTS)
except Exception:
    def _in_arm_override(wv): return False

# Trunk sınıfı alan ama bacak bölgesinde olan vertex'ler için override (diz sarı/gri sorunu).
# %10'dan başlar — kalça eklemi karışmasın.
try:
    _LEG_OVERRIDE_TESTS = [
        _seg("CC_Base_L_Thigh", "CC_Base_L_Calf", 0.10, 1.10, 0.52),
        _seg("CC_Base_R_Thigh", "CC_Base_R_Calf", 0.10, 1.10, 0.52),
        _seg("CC_Base_L_Calf",  "CC_Base_L_Foot", 0.0,  1.10, 0.48),
        _seg("CC_Base_R_Calf",  "CC_Base_R_Foot", 0.0,  1.10, 0.48),
    ]
    def _in_leg_override(wv):
        return any(t(wv) for t in _LEG_OVERRIDE_TESTS)
except Exception:
    def _in_leg_override(wv): return False

# ── Leg içi subdivizyon ───────────────────────────────────────────────────────
def leg_subclass(z):
    if z >= z_mid_thigh: return 4   # üst uyluk → sarı (kalça ölçümüyle örtüşür)
    if z >= z_calf_top:  return 5   # alt uyluk + diz üstü → açık yeşil
    if z >= z_foot:      return 6   # baldır → koyu yeşil
    return 12                        # ayak

# ── Palette ───────────────────────────────────────────────────────────────────
PALETTE = {
    0:  (0.0,   0.0,   0.0),
    1:  (0.502, 0.0,   0.0),
    2:  (1.0,   0.0,   0.0),
    3:  (1.0,   0.502, 0.0),
    4:  (1.0,   1.0,   0.0),
    5:  (0.0,   1.0,   0.0),
    6:  (0.0,   0.502, 0.0),
    7:  (0.0,   0.0,   1.0),
    8:  (0.0,   0.502, 1.0),
    9:  (0.0,   1.0,   1.0),
    10: (0.502, 0.0,   1.0),
    11: (1.0,   0.502, 1.0),
    12: (0.502, 0.502, 0.502),
    13: (1.0,   1.0,   1.0),
    14: (0.6,   0.3,   0.1),
    15: (0.6,   1.0,   0.0),
}
CLASS_NAMES = {
    1:"neck", 2:"chest", 3:"waist", 4:"hip",
    5:"mid_thigh", 6:"calf", 7:"bicep", 8:"elbow",
    9:"forearm", 10:"wrist", 11:"head", 12:"foot",
    13:"hand", 14:"trapezius", 15:"shoulder",
}

# ── Vertex sınıflandırma ──────────────────────────────────────────────────────
mesh      = body_obj.data
mat_world = body_obj.matrix_world

for attr in list(mesh.color_attributes):
    mesh.color_attributes.remove(attr)
col_attr = mesh.color_attributes.new(name="SegClass", type='FLOAT_COLOR', domain='POINT')

# ── Pass 1: Ham sınıflandırma ─────────────────────────────────────────────────
n_verts  = len(mesh.vertices)
vert_cls = [0] * n_verts

for v in mesh.vertices:
    wv = mat_world @ v.co

    if not v.groups:
        cls = nearest_trunk_class(wv.z)
    else:
        grp_w = {}
        for g in v.groups:
            bn  = vg_name.get(g.group, "")
            grp = bone_group(bn)
            grp_w[grp] = grp_w.get(grp, 0.0) + g.weight

        primary = max(grp_w, key=lambda r: grp_w[r])

        if   primary == 'arm':      cls = arm_subclass(wv)
        elif primary == 'head':     cls = 11
        elif primary == 'neck':     cls = 1
        elif primary == 'shoulder': cls = 15
        elif primary == 'leg':      cls = leg_subclass(wv.z)
        elif primary == 'foot':     cls = 12
        else:                       cls = trunk_class(wv)

        if cls in (2, 3, 4, 14) and _in_arm_override(wv):
            cls = arm_subclass(wv)
        elif cls in (2, 3, 4, 12) and _in_leg_override(wv):
            cls = leg_subclass(wv.z)

    vert_cls[v.index] = cls

# ── Pass 2: Majority-vote smoothing (glitter giderme) ────────────────────────
# Her vertex komşularının çoğunluk sınıfını alır — izole noisy vertex'ler temizlenir.
adj = [[] for _ in range(n_verts)]
for edge in mesh.edges:
    v0, v1 = edge.vertices
    adj[v0].append(v1)
    adj[v1].append(v0)

NUM_SMOOTH = 3
for _ in range(NUM_SMOOTH):
    new_cls = vert_cls[:]
    for vi in range(n_verts):
        nbrs = adj[vi]
        if not nbrs:
            continue
        cnt = {}
        for n in nbrs:
            c = vert_cls[n]
            cnt[c] = cnt.get(c, 0) + 1
        best      = max(cnt, key=lambda c: cnt[c])
        own_count = cnt.get(vert_cls[vi], 0)
        # Komşuların yarısından fazlası farklı bir sınıfta ise geçiş yap
        if cnt[best] > own_count and cnt[best] > len(nbrs) * 0.50:
            new_cls[vi] = best
    vert_cls = new_cls

# ── Pass 3: Renk yazma ────────────────────────────────────────────────────────
counts = {}
for vi, cls in enumerate(vert_cls):
    counts[cls] = counts.get(cls, 0) + 1
    col = PALETTE[cls]
    col_attr.data[vi].color = (col[0], col[1], col[2], 1.0)

print("\n--- Sinif dagilimi ---")
for cid, cnt in sorted(counts.items()):
    print(f"  class {cid:2d} {CLASS_NAMES.get(cid,'bg'):<12} {cnt}")

# ── Materyal: vertex color → emission ────────────────────────────────────────
bpy.context.view_layer.objects.active = body_obj
seg_mat = bpy.data.materials.new("SegMat")
seg_mat.use_nodes = True
nodes = seg_mat.node_tree.nodes
links = seg_mat.node_tree.links
nodes.clear()
vc   = nodes.new('ShaderNodeVertexColor');    vc.layer_name = "SegClass"
emit = nodes.new('ShaderNodeEmission');       emit.inputs["Strength"].default_value = 1.0
out  = nodes.new('ShaderNodeOutputMaterial')
links.new(vc.outputs["Color"],   emit.inputs["Color"])
links.new(emit.outputs["Emission"], out.inputs["Surface"])

head_col = PALETTE[11]  # pembe — göz, kaş, dil vb. yüz mesh'leri
for obj in scene.objects:
    if obj.type != 'MESH':
        continue
    obj.data.materials.clear()
    obj.data.materials.append(seg_mat)
    if obj is body_obj:
        continue
    for attr in list(obj.data.color_attributes):
        obj.data.color_attributes.remove(attr)
    ca = obj.data.color_attributes.new(name="SegClass", type='FLOAT_COLOR', domain='POINT')
    for i in range(len(obj.data.vertices)):
        ca.data[i].color = (head_col[0], head_col[1], head_col[2], 1.0)

# ── Render ayarları ───────────────────────────────────────────────────────────
scene.render.engine       = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Raw'
scene.view_settings.look            = 'None'
scene.view_settings.gamma           = 1.0
scene.view_settings.exposure        = 0.0
if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'use_bloom'):
    scene.eevee.use_bloom = False

scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value    = (0.0, 0.0, 0.0, 1.0)
bg.inputs["Strength"].default_value = 1.0

scene.use_nodes = True
ctree = scene.node_tree
for n in list(ctree.nodes): ctree.nodes.remove(n)
rl   = ctree.nodes.new('CompositorNodeRLayers')
comp = ctree.nodes.new('CompositorNodeComposite')
ctree.links.new(rl.outputs['Image'], comp.inputs['Image'])

# ── Kamera ────────────────────────────────────────────────────────────────────
bpy.ops.object.camera_add()
cam_obj = bpy.context.active_object
scene.camera = cam_obj
FOCAL_MM, SENSOR_MM = 85.0, 36.0
cam_obj.data.lens         = FOCAL_MM
cam_obj.data.sensor_width = SENSOR_MM

xs = [v.x for v in all_bb]; ys = [v.y for v in all_bb]
center_x   = (max(xs) + min(xs)) / 2
cam_target = mathutils.Vector((center_x, center_y, z_floor + height_m * 0.50))
cam_elev   = 8
vfov_half  = math.atan(SENSOR_MM / 2.0 / FOCAL_MM)
cam_dist   = (height_m * 1.20) / (2.0 * math.tan(vfov_half))
elev_rad   = math.radians(cam_elev)

VIEWS = [
    ("front",0),("front_right",45),("right",90),("back_right",135),
    ("back",180),("back_left",225),("left",270),("front_left",315),
]

def position_camera(angle_deg):
    a  = math.radians(angle_deg)
    cx = cam_target.x + cam_dist * math.cos(elev_rad) * math.sin(a)
    cy = cam_target.y - cam_dist * math.cos(elev_rad) * math.cos(a)
    cz = cam_target.z + cam_dist * math.sin(elev_rad)
    cam_obj.location       = (cx, cy, cz)
    direction              = cam_target - mathutils.Vector((cx, cy, cz))
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# Palette numpy array — render sonrası piksel snap için
_PAL = np.array([PALETTE[k] for k in sorted(PALETTE.keys())], dtype=np.float32)  # (16, 3)

def snap_to_palette(filepath):
    """Her pikseli en yakın palette rengine snapleler — interpolasyon artefaktlarını kaldırır."""
    img = bpy.data.images.load(filepath, check_existing=False)
    w, h = img.size
    px  = np.array(img.pixels[:], dtype=np.float32).reshape(h * w, 4)
    rgb = px[:, :3]
    # (N,1,3) - (1,16,3) → (N,16,3) → L2 dist → nearest
    dists   = np.sum((rgb[:, None] - _PAL[None]) ** 2, axis=2)
    nearest = np.argmin(dists, axis=1)
    px[:, :3] = _PAL[nearest]
    px[:, 3]  = 1.0
    img.pixels[:] = px.flatten()
    img.filepath_raw = filepath
    img.file_format  = 'PNG'
    img.save()
    bpy.data.images.remove(img)

for view_name, angle_deg in VIEWS:
    position_camera(angle_deg)
    fpath = os.path.join(out_dir, f"{char_name}_{view_name}.png")
    scene.render.filepath = fpath
    bpy.ops.render.render(write_still=True)
    snap_to_palette(fpath)

print(f"\n[seg] 8 maske -> {out_dir}")

"""
render_segmentation_masks.py — Blender background script
Her ölçüm bölgesi için vertex-level sınıflandırma yapar ve 8 yönde
RGB instance-segmentation maskesi üretir.

Strateji:
  - Kol vertex'leri: her iki kol için bone segment silindiri testi
  - Gövde/baş/bacak vertex'leri: en yakın ölçüm z-düzlemine Voronoi atama
    → boşluk kalmaz, her vertex bir sınıfa girer

Palette (R, G, B) — class 0 arkaplan (siyah):
  1  neck       (128, 0,   0  )
  2  chest      (255, 0,   0  )
  3  waist      (255, 128, 0  )
  4  hip        (255, 255, 0  )
  5  mid_thigh  (0,   255, 0  )
  6  calf       (0,   128, 0  )
  7  bicep      (0,   0,   255)
  8  elbow      (0,   128, 255)
  9  forearm    (0,   255, 255)
  10 wrist      (128, 0,   255)

Kullanım:
  blender --background --python render_segmentation_masks.py -- <fbx_path> <out_dir>
"""

import bpy
import math
import sys
import os
import mathutils

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
arm_obj = next((o for o in scene.objects if o.type == 'ARMATURE'), None)
if not arm_obj:
    print("ERROR: Armature bulunamadi"); sys.exit(1)

mesh_objs = [o for o in scene.objects if o.type == 'MESH']
if not mesh_objs:
    print("ERROR: Mesh bulunamadi"); sys.exit(1)

all_verts_bb = []
for obj in mesh_objs:
    for corner in obj.bound_box:
        all_verts_bb.append(obj.matrix_world @ mathutils.Vector(corner))
z_floor  = min(v.z for v in all_verts_bb)
z_top    = max(v.z for v in all_verts_bb)
height_m = z_top - z_floor

def mesh_z_span(obj):
    zs = [(obj.matrix_world @ mathutils.Vector(c)).z for c in obj.bound_box]
    return min(zs), max(zs)

body_candidates = [obj for obj in mesh_objs
                   if (lambda zn, zx: zn < z_floor + height_m * 0.15
                                   and zx > z_floor + height_m * 0.70
                       )(*mesh_z_span(obj))]
body_obj = max(body_candidates or mesh_objs, key=lambda o: len(o.data.vertices))
print(f"Body mesh: {body_obj.name} ({len(body_obj.data.vertices)} vertex)")

# ── Kemik pozisyonları ────────────────────────────────────────────────────────
def bone_world(name):
    return arm_obj.matrix_world @ arm_obj.pose.bones[name].head

def bone_z(name):
    return bone_world(name).z

z_head      = bone_z("CC_Base_Head")
z_neck      = (bone_z("CC_Base_NeckTwist01") + bone_z("CC_Base_NeckTwist02")) / 2
z_chest     = bone_z("CC_Base_L_Breast")
z_waist     = bone_z("CC_Base_Waist")
z_hip       = bone_z("CC_Base_L_Thigh") + (bone_z("CC_Base_Waist") - bone_z("CC_Base_L_Thigh")) * 0.15
z_mid_thigh = (bone_z("CC_Base_L_Thigh") + bone_z("CC_Base_L_Calf")) / 2
z_calf      = bone_z("CC_Base_L_CalfTwist02")
z_foot      = bone_z("CC_Base_L_Foot")

# Voronoi z-bölgeleme: her z-yüksekliğine class ID
TRUNK_ZONES = [
    (z_head,      11),  # head
    (z_neck,      1),   # neck
    (z_chest,     2),   # chest
    (z_waist,     3),   # waist
    (z_hip,       4),   # hip
    (z_mid_thigh, 5),   # mid_thigh
    (z_calf,      6),   # calf
    (z_foot,      12),  # foot
]

def nearest_trunk_class(z):
    """Vertex z'sine en yakın ölçüm düzleminin class ID'sini döndürür."""
    return min(TRUNK_ZONES, key=lambda t: abs(t[0] - z))[1]

# ── Kol segment testi (her iki kol) ──────────────────────────────────────────
ARM_SEGMENTS = [
    # (class_id, p0_bone, p1_bone, cut_at, radius_f, margin_f)
    (7,  "CC_Base_L_Upperarm", "CC_Base_L_Forearm", "mid",  0.60, 0.30),  # L bicep
    (7,  "CC_Base_R_Upperarm", "CC_Base_R_Forearm", "mid",  0.60, 0.30),  # R bicep
    (8,  "CC_Base_L_Upperarm", "CC_Base_L_Forearm", "end",  0.55, 0.20),  # L elbow
    (8,  "CC_Base_R_Upperarm", "CC_Base_R_Forearm", "end",  0.55, 0.20),  # R elbow
    (9,  "CC_Base_L_Forearm",  "CC_Base_L_Hand",    "mid",  0.60, 0.30),  # L forearm
    (9,  "CC_Base_R_Forearm",  "CC_Base_R_Hand",    "mid",  0.60, 0.30),  # R forearm
    (10, "CC_Base_L_Forearm",  "CC_Base_L_Hand",    "end",  0.50, 0.20),  # L wrist
    (10, "CC_Base_R_Forearm",  "CC_Base_R_Hand",    "end",  0.50, 0.20),  # R wrist
]

def build_arm_test(p0_name, p1_name, cut_at, radius_f, margin_f):
    p0       = bone_world(p0_name)
    p1       = bone_world(p1_name)
    axis     = (p1 - p0).normalized()
    bone_len = (p1 - p0).length
    margin   = bone_len * margin_f
    cut_pt   = (p0 + p1) * 0.5 if cut_at == "mid" else p1
    cut_half = bone_len * 0.28
    def _test(wv):
        to_v = wv - p0
        proj = to_v.dot(axis)
        if proj < -margin or proj > bone_len + margin:
            return False
        if (to_v - axis * proj).length > bone_len * radius_f:
            return False
        return abs((wv - cut_pt).dot(axis)) <= cut_half
    return _test

arm_rules = [(cls, build_arm_test(p0n, p1n, cut, rf, mf))
             for cls, p0n, p1n, cut, rf, mf in ARM_SEGMENTS]

# Kol testi: sabit absolute yarıçaplı silindir — A-pose'da çapraz inen kollar için güvenli.
# margin_start: p0 (shoulder) tarafına uzama — küçük tutulursa omuz/göğüs overlap'i önlenir.
# margin_end:   p1 (elbow/hand) tarafına uzama — segmentler arası boşluğu kapatır.
def build_arm_cyl(p0_name, p1_name, abs_radius, margin_start=0.02, margin_end=0.20):
    p0       = bone_world(p0_name)
    p1       = bone_world(p1_name)
    axis     = (p1 - p0).normalized()
    bone_len = (p1 - p0).length
    def _test(wv):
        to_v = wv - p0
        proj = to_v.dot(axis)
        if proj < -margin_start or proj > bone_len + margin_end:
            return False
        return (to_v - axis * proj).length <= abs_radius
    return _test

# El silindiri: hand kemiğinden forearm ekseni boyunca parmak uçlarına uzanır.
def build_hand_cyl(forearm_name, hand_name, abs_radius=0.08, length=0.18):
    p_fore = bone_world(forearm_name)
    p_hand = bone_world(hand_name)
    axis   = (p_hand - p_fore).normalized()
    def _test(wv):
        to_v = wv - p_hand
        proj = to_v.dot(axis)
        if proj < -0.02 or proj > length:
            return False
        return (to_v - axis * proj).length <= abs_radius
    return _test

# El testi: hand kemiğinden parmak yönüne uzanan geniş yarı-silindir.
# proj < 0 → geriye forearm'a uzanmaz. Geniş radius parmakları yakalar.
def build_hand_cone(forearm_name, hand_name, abs_radius=0.12, length=0.20, back=0.03):
    p_fore = bone_world(forearm_name)
    p_hand = bone_world(hand_name)
    axis   = (p_hand - p_fore).normalized()
    def _test(wv):
        to_v = wv - p_hand
        proj = to_v.dot(axis)
        if proj < -back or proj > length:
            return False
        return (to_v - axis * proj).length <= abs_radius
    return _test

_ARM_CYLS = [
    build_arm_cyl("CC_Base_L_Upperarm", "CC_Base_L_Forearm", abs_radius=0.10, margin_start=0.00, margin_end=0.12),
    build_arm_cyl("CC_Base_R_Upperarm", "CC_Base_R_Forearm", abs_radius=0.10, margin_start=0.00, margin_end=0.12),
    build_arm_cyl("CC_Base_L_Forearm",  "CC_Base_L_Hand",    abs_radius=0.09, margin_start=0.00, margin_end=0.10),
    build_arm_cyl("CC_Base_R_Forearm",  "CC_Base_R_Hand",    abs_radius=0.09, margin_start=0.00, margin_end=0.10),
    build_hand_cone("CC_Base_L_Forearm", "CC_Base_L_Hand"),
    build_hand_cone("CC_Base_R_Forearm", "CC_Base_R_Hand"),
]

def is_arm_vertex(wv):
    return any(cyl(wv) for cyl in _ARM_CYLS)

_HAND_TESTS = [
    build_hand_cone("CC_Base_L_Forearm", "CC_Base_L_Hand"),
    build_hand_cone("CC_Base_R_Forearm", "CC_Base_R_Hand"),
]

# ── Palette ───────────────────────────────────────────────────────────────────
PALETTE = {
    0:  (0.0,   0.0,   0.0),    # background
    1:  (0.502, 0.0,   0.0),    # neck
    2:  (1.0,   0.0,   0.0),    # chest
    3:  (1.0,   0.502, 0.0),    # waist
    4:  (1.0,   1.0,   0.0),    # hip
    5:  (0.0,   1.0,   0.0),    # mid_thigh
    6:  (0.0,   0.502, 0.0),    # calf
    7:  (0.0,   0.0,   1.0),    # bicep
    8:  (0.0,   0.502, 1.0),    # elbow
    9:  (0.0,   1.0,   1.0),    # forearm
    10: (0.502, 0.0,   1.0),    # wrist
    11: (1.0,   0.502, 1.0),    # head
    12: (0.502, 0.502, 0.502),  # foot
    13: (1.0,   1.0,   1.0),    # hand (beyaz)
}

CLASS_NAMES = {
    1: "neck", 2: "chest", 3: "waist", 4: "hip",
    5: "mid_thigh", 6: "calf",
    7: "bicep", 8: "elbow", 9: "forearm", 10: "wrist",
    11: "head", 12: "foot", 13: "hand",
}

# ── Vertex sınıflandırma ──────────────────────────────────────────────────────
mesh     = body_obj.data
mat_world = body_obj.matrix_world

for attr in list(mesh.color_attributes):
    mesh.color_attributes.remove(attr)
col_attr = mesh.color_attributes.new(name="SegClass", type='FLOAT_COLOR', domain='POINT')

counts = {}
for v in mesh.vertices:
    wv  = mat_world @ v.co
    cls = 0

    if is_arm_vertex(wv):
        cls = 7  # varsayılan: bicep
        for arm_cls, arm_test in arm_rules:
            if arm_test(wv):
                cls = arm_cls
        # El: wrist üzerine yazar — en yüksek öncelik
        if any(ht(wv) for ht in _HAND_TESTS):
            cls = 13
    else:
        cls = nearest_trunk_class(wv.z)

    counts[cls] = counts.get(cls, 0) + 1
    col = PALETTE[cls]
    col_attr.data[v.index].color = (col[0], col[1], col[2], 1.0)

for cls_id, cnt in sorted(counts.items()):
    name = CLASS_NAMES.get(cls_id, "background")
    print(f"  class {cls_id:2d} {name:<12} {cnt} vertices")

# ── Materyal: vertex color → emission ────────────────────────────────────────
bpy.context.view_layer.objects.active = body_obj
seg_mat = bpy.data.materials.new("SegMat")
seg_mat.use_nodes = True
nodes = seg_mat.node_tree.nodes
links = seg_mat.node_tree.links
nodes.clear()
vc_node   = nodes.new('ShaderNodeVertexColor');  vc_node.layer_name = "SegClass"
emit_node = nodes.new('ShaderNodeEmission');     emit_node.inputs["Strength"].default_value = 1.0
out_node  = nodes.new('ShaderNodeOutputMaterial')
links.new(vc_node.outputs["Color"],    emit_node.inputs["Color"])
links.new(emit_node.outputs["Emission"], out_node.inputs["Surface"])

for obj in scene.objects:
    if obj.type == 'MESH':
        obj.data.materials.clear()
        obj.data.materials.append(seg_mat)

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
rl_node   = ctree.nodes.new('CompositorNodeRLayers')
comp_node = ctree.nodes.new('CompositorNodeComposite')
ctree.links.new(rl_node.outputs['Image'], comp_node.inputs['Image'])

# ── Kamera ────────────────────────────────────────────────────────────────────
bpy.ops.object.camera_add()
cam_obj = bpy.context.active_object
scene.camera = cam_obj
FOCAL_MM  = 85.0
SENSOR_MM = 36.0
cam_obj.data.lens         = FOCAL_MM
cam_obj.data.sensor_width = SENSOR_MM

xs_all    = [v.x for v in all_verts_bb]
ys_all    = [v.y for v in all_verts_bb]
center_x  = (max(xs_all) + min(xs_all)) / 2
center_y  = (max(ys_all) + min(ys_all)) / 2
cam_target = mathutils.Vector((center_x, center_y, z_floor + height_m * 0.50))
cam_elev   = 8
vfov_half  = math.atan(SENSOR_MM / 2.0 / FOCAL_MM)
cam_dist   = (height_m * 1.20) / (2.0 * math.tan(vfov_half))
elev_rad   = math.radians(cam_elev)

VIEWS = [
    ("front",       0),  ("front_right", 45),  ("right",      90),
    ("back_right", 135), ("back",        180),  ("back_left", 225),
    ("left",       270), ("front_left",  315),
]

def position_camera(angle_deg):
    a  = math.radians(angle_deg)
    cx = cam_target.x + cam_dist * math.cos(elev_rad) * math.sin(a)
    cy = cam_target.y - cam_dist * math.cos(elev_rad) * math.cos(a)
    cz = cam_target.z + cam_dist * math.sin(elev_rad)
    cam_obj.location       = (cx, cy, cz)
    direction              = cam_target - mathutils.Vector((cx, cy, cz))
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

for view_name, angle_deg in VIEWS:
    position_camera(angle_deg)
    scene.render.filepath = os.path.join(out_dir, f"{char_name}_{view_name}.png")
    bpy.ops.render.render(write_still=True)

print(f"\n[seg] 8 maske -> {out_dir}")

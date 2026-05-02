"""
measure_anthropometry.py — Blender background script
CC5 FBX karakterinden antropometrik ölçümler çıkarır.
Kol kesişimini önlemek için ölçüm öncesi A-pose uygulanır.

Kullanım:
  blender --background --python measure_anthropometry.py -- <fbx_path> <out_dir>
"""

import bpy
import bmesh
import sys
import os
import json
import math
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

# ── Armature ──────────────────────────────────────────────────────────────────
arm_obj = next((o for o in scene.objects if o.type == 'ARMATURE'), None)
if not arm_obj:
    print(f"ERROR: Armature bulunamadi — {fbx_path}")
    sys.exit(1)

def bone_world(name):
    return arm_obj.matrix_world @ arm_obj.pose.bones[name].head

def bone_dist_cm(a, b):
    return round((bone_world(a) - bone_world(b)).length * 100, 2)

def bone_z(name):
    return bone_world(name).z

# ── Body mesh seçimi ──────────────────────────────────────────────────────────
mesh_objs = [o for o in scene.objects if o.type == 'MESH']
if not mesh_objs:
    print(f"ERROR: Mesh bulunamadi — {fbx_path}")
    sys.exit(1)

all_verts = []
for obj in mesh_objs:
    for corner in obj.bound_box:
        all_verts.append(obj.matrix_world @ mathutils.Vector(corner))
z_floor  = min(v.z for v in all_verts)
z_top    = max(v.z for v in all_verts)
height_m = z_top - z_floor

def mesh_z_span(obj):
    zs = [(obj.matrix_world @ mathutils.Vector(c)).z for c in obj.bound_box]
    return min(zs), max(zs)

body_candidates = []
for obj in mesh_objs:
    zmin, zmax = mesh_z_span(obj)
    if zmin < (z_floor + height_m * 0.15) and zmax > (z_floor + height_m * 0.70):
        body_candidates.append(obj)

body_obj = max(body_candidates or mesh_objs, key=lambda o: len(o.data.vertices))
print(f"Body mesh: {body_obj.name} ({len(body_obj.data.vertices)} vertex)")

height_cm = round(height_m * 100, 2)

# ── A-pose uygula (kol kesişimini önler) ──────────────────────────────────────
def apply_a_pose(angle_deg=45):
    """
    T-pose kollarını angle_deg kadar aşağı indirir.
    pbone.matrix (fresh import'ta rest pose = armature space) üzerinden
    doğrudan dünya rotasyonu uygular.
    """
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')

    angle = math.radians(angle_deg)

    for side, sign in [('L', 1), ('R', -1)]:
        pbone = arm_obj.pose.bones.get(f'CC_Base_{side}_Upperarm')
        if pbone is None:
            print(f"  [WARN] CC_Base_{side}_Upperarm bulunamadi")
            continue

        # Sadece rotasyon değişsin, omuz pozisyonu (translation) sabit kalsın
        current_world = arm_obj.matrix_world @ pbone.matrix.copy()
        loc, rot_q, scale = current_world.decompose()

        # Delta rotasyonu dünya Y ekseni etrafında ekle
        delta = mathutils.Quaternion((0, 1, 0), sign * angle)
        new_rot = delta @ rot_q

        new_world = (mathutils.Matrix.Translation(loc) @
                     new_rot.to_matrix().to_4x4() @
                     mathutils.Matrix.Diagonal((*scale, 1.0)))
        pbone.matrix = arm_obj.matrix_world.inverted() @ new_world
        bpy.context.view_layer.update()

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()

apply_a_pose(angle_deg=45)
depsgraph = bpy.context.evaluated_depsgraph_get()

# ── Çevre ölçümü: A-posed evaluated mesh + en büyük bağlı döngü ──────────────
def measure_circumference_cm(z_m):
    # A-pose uygulanmış mesh'i kullan (kol aşağıda)
    eval_obj  = body_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()

    bm = bmesh.new()
    bm.from_mesh(eval_mesh)
    bm.transform(eval_obj.matrix_world)
    eval_obj.to_mesh_clear()
    bm.faces.ensure_lookup_table()

    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    ret  = bmesh.ops.bisect_plane(
        bm,
        geom=geom,
        plane_co=(0.0, 0.0, z_m),
        plane_no=(0.0, 0.0, 1.0),
    )
    cut_edges = [e for e in ret['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]

    if not cut_edges:
        bm.free()
        return 0.0

    neighbors = {}
    for e in cut_edges:
        for v in e.verts:
            neighbors.setdefault(v.index, []).append(e)

    visited = set(); components = []
    for start in cut_edges:
        if id(start) in visited:
            continue
        comp = []; queue = [start]
        while queue:
            e = queue.pop()
            if id(e) in visited: continue
            visited.add(id(e)); comp.append(e)
            for v in e.verts:
                for ne in neighbors.get(v.index, []):
                    if id(ne) not in visited: queue.append(ne)
        components.append(comp)

    ranked   = sorted(components, key=lambda c: sum(e.calc_length() for e in c), reverse=True)
    largest  = ranked[0]
    total_cm = sum(e.calc_length() for e in largest) * 100

    if total_cm > 200.0 and len(ranked) > 1:
        second_cm = sum(e.calc_length() for e in ranked[1]) * 100
        if second_cm > 20.0:
            print(f"  [WARN] circ {total_cm:.1f} cm > 200, 2nd component {second_cm:.1f} cm kullaniliyor")
            total_cm = second_cm

    bm.free()
    return round(total_cm, 2)

# ── Referans yükseklikleri ────────────────────────────────────────────────────
z_neck      = bone_z("CC_Base_NeckTwist02")
z_chest     = bone_z("CC_Base_L_Breast")
z_waist     = bone_z("CC_Base_Waist")
z_hip       = bone_z("CC_Base_L_Thigh") - (bone_z("CC_Base_L_Thigh") - bone_z("CC_Base_L_Calf")) * 0.15
z_mid_thigh = (bone_z("CC_Base_L_Thigh") + bone_z("CC_Base_L_Calf")) / 2
z_calf      = (bone_z("CC_Base_L_Calf") + bone_z("CC_Base_L_CalfTwist02")) / 2

# ── Genişlikler ───────────────────────────────────────────────────────────────
shoulder_width_cm = round(
    abs(bone_world("CC_Base_L_Upperarm").x - bone_world("CC_Base_R_Upperarm").x) * 100, 2)
hip_width_cm = round(
    abs(bone_world("CC_Base_L_Thigh").x - bone_world("CC_Base_R_Thigh").x) * 100, 2)

# ── Ölçümler ──────────────────────────────────────────────────────────────────
measurements = {
    "char_id":   char_name,
    "height_cm": height_cm,

    "neck_circ_cm":      measure_circumference_cm(z_neck),
    "chest_circ_cm":     measure_circumference_cm(z_chest),
    "waist_circ_cm":     measure_circumference_cm(z_waist),
    "hip_circ_cm":       measure_circumference_cm(z_hip),
    "mid_thigh_circ_cm": measure_circumference_cm(z_mid_thigh),
    "calf_circ_cm":      measure_circumference_cm(z_calf),

    "upper_arm_length_cm": bone_dist_cm("CC_Base_L_Upperarm", "CC_Base_L_Forearm"),
    "forearm_length_cm":   bone_dist_cm("CC_Base_L_Forearm",  "CC_Base_L_Hand"),
    "total_arm_length_cm": bone_dist_cm("CC_Base_L_Upperarm", "CC_Base_L_Hand"),
    "upper_leg_length_cm": bone_dist_cm("CC_Base_L_Thigh",    "CC_Base_L_Calf"),
    "lower_leg_length_cm": bone_dist_cm("CC_Base_L_Calf",     "CC_Base_L_Foot"),
    "total_leg_length_cm": bone_dist_cm("CC_Base_L_Thigh",    "CC_Base_L_Foot"),

    "shoulder_width_cm": shoulder_width_cm,
    "hip_width_cm":      hip_width_cm,
}

# ── Kaydet ────────────────────────────────────────────────────────────────────
out_path = os.path.join(out_dir, f"{char_name}_measurements.json")
with open(out_path, "w") as f:
    json.dump(measurements, f, indent=2)

print(f"\n{char_name}:")
for k, v in measurements.items():
    if k != "char_id":
        print(f"  {k:<28} {v}")
print(f"\n-> {out_path}")

"""
render_debug_measurements.py — Blender background script
Her ölçüm bölgesinin konturunu renkli 3D eğri olarak render'a işler.
Çıktı: renders/debug/<char_id>_debug_front.png + _right.png + _debug.json

Renkler:
  neck      — cyan
  chest     — red
  waist     — green
  hip       — blue
  mid_thigh — orange
  calf      — magenta
  upper_arm — yellow
  forearm   — purple
"""

import bpy
import bmesh
import sys
import os
import json
import math
import mathutils



argv     = sys.argv[sys.argv.index("--") + 1:]
fbx_path = argv[0]
out_dir  = argv[1]
os.makedirs(out_dir, exist_ok=True)

char_name = os.path.splitext(os.path.basename(fbx_path))[0]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.fbx(filepath=fbx_path)

# ── Armature ──────────────────────────────────────────────────────────────────
arm_obj = next((o for o in scene.objects if o.type == 'ARMATURE'), None)
if not arm_obj:
    print(f"ERROR: Armature bulunamadi")
    sys.exit(1)

def bone_world(name):
    return arm_obj.matrix_world @ arm_obj.pose.bones[name].head

def bone_z(name):
    return bone_world(name).z

# ── Body mesh ─────────────────────────────────────────────────────────────────
mesh_objs = [o for o in scene.objects if o.type == 'MESH']
all_verts = []
for obj in mesh_objs:
    for corner in obj.bound_box:
        all_verts.append(obj.matrix_world @ mathutils.Vector(corner))

z_floor  = min(v.z for v in all_verts)
z_top    = max(v.z for v in all_verts)
height_m = z_top - z_floor
xs = [v.x for v in all_verts]; ys = [v.y for v in all_verts]
center_x = (max(xs) + min(xs)) / 2
center_y = (max(ys) + min(ys)) / 2

def mesh_z_span(obj):
    zs = [(obj.matrix_world @ mathutils.Vector(c)).z for c in obj.bound_box]
    return min(zs), max(zs)

body_candidates = [o for o in mesh_objs
                   if mesh_z_span(o)[0] < (z_floor + height_m * 0.15)
                   and mesh_z_span(o)[1] > (z_floor + height_m * 0.70)]
body_obj = max(body_candidates or mesh_objs, key=lambda o: len(o.data.vertices))
print(f"Body mesh: {body_obj.name}")

# ── A-pose uygula (kol kesişimini önler) ──────────────────────────────────────
def apply_a_pose(angle_deg=45):
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    angle = math.radians(angle_deg)
    for side, sign in [('L', 1), ('R', -1)]:
        pbone = arm_obj.pose.bones.get(f'CC_Base_{side}_Upperarm')
        if pbone is None:
            continue
        current_world = arm_obj.matrix_world @ pbone.matrix.copy()
        loc, rot_q, scale = current_world.decompose()
        delta        = mathutils.Quaternion((0, 1, 0), sign * angle)
        new_rot      = delta @ rot_q
        new_world    = (mathutils.Matrix.Translation(loc) @
                        new_rot.to_matrix().to_4x4() @
                        mathutils.Matrix.Diagonal((*scale, 1.0)))
        pbone.matrix = arm_obj.matrix_world.inverted() @ new_world
        bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()

apply_a_pose(angle_deg=45)
depsgraph = bpy.context.evaluated_depsgraph_get()

# ── Silhouette materyal (açık gri karakter, koyu arkaplan) ────────────────────
def make_emit_mat(name, rgb, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    ns = mat.node_tree.nodes; ns.clear()
    e = ns.new('ShaderNodeEmission')
    o = ns.new('ShaderNodeOutputMaterial')
    e.inputs["Color"].default_value    = (*rgb, 1.0)
    e.inputs["Strength"].default_value = strength
    mat.node_tree.links.new(e.outputs["Emission"], o.inputs["Surface"])
    return mat

sil_mat = make_emit_mat("Sil", (0.80, 0.80, 0.80), 1.0)
for obj in scene.objects:
    if obj.type == 'MESH':
        obj.data.materials.clear()
        obj.data.materials.append(sil_mat)

scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value    = (0.06, 0.06, 0.06, 1.0)
bg.inputs["Strength"].default_value = 1.0

# ── Ölçüm tanımları ───────────────────────────────────────────────────────────
# Her giriş: (label, plane_co, plane_no, color, ref_point)
# ref_point=None → en büyük bileşen (gövde ölçümleri)
# ref_point=Vector → bone orta noktasına en yakın bileşen (kol ölçümleri)

def _z_entry(label, z_m, color):
    return (label, mathutils.Vector((0.0, 0.0, z_m)),
            mathutils.Vector((0.0, 0.0, 1.0)), color, None)

def _arm_entry(label, b0, b1, color):
    p0  = bone_world(b0); p1 = bone_world(b1)
    mid = (p0 + p1) * 0.5
    ax  = (p1 - p0).normalized()
    return (label, mid, ax, color, mid)

MEASUREMENTS = [
    _z_entry("neck",      bone_z("CC_Base_NeckTwist01"),  (0.0, 1.0, 1.0)),
    _z_entry("chest",     bone_z("CC_Base_L_Breast"),     (1.0, 0.2, 0.2)),
    _z_entry("waist",     bone_z("CC_Base_Waist"),        (0.2, 1.0, 0.2)),
    _z_entry("hip",       bone_z("CC_Base_L_Thigh") - (bone_z("CC_Base_L_Thigh") - bone_z("CC_Base_L_Calf")) * 0.15,
                                                           (0.3, 0.5, 1.0)),
    _z_entry("mid_thigh", (bone_z("CC_Base_L_Thigh") + bone_z("CC_Base_L_Calf")) / 2,
                                                           (1.0, 0.55, 0.0)),
    _z_entry("calf",      bone_z("CC_Base_L_CalfTwist02"),(1.0, 0.0, 1.0)),
    _arm_entry("upper_arm", "CC_Base_L_Upperarm", "CC_Base_L_Forearm", (1.0, 1.0, 0.0)),
    _arm_entry("forearm",   "CC_Base_L_Forearm",  "CC_Base_L_Hand",    (0.7, 0.0, 1.0)),
]

# ── Edge loop sıralama ────────────────────────────────────────────────────────
def order_loop(edges):
    if not edges:
        return []
    adj = {}
    for e in edges:
        v0, v1 = e.verts
        adj.setdefault(v0.index, []).append((v1, e))
        adj.setdefault(v1.index, []).append((v0, e))

    start_v   = edges[0].verts[0]
    path      = [start_v.co.copy()]
    visited_e = set()
    visited_v = {start_v.index}
    current   = start_v
    while True:
        moved = False
        for nv, e in adj.get(current.index, []):
            if id(e) not in visited_e and nv.index not in visited_v:
                visited_e.add(id(e))
                visited_v.add(nv.index)
                path.append(nv.co.copy())
                current = nv
                moved = True
                break
        if not moved:
            break
    return path

# ── Kontur eğrileri ───────────────────────────────────────────────────────────
z_data = {}

for label, plane_co, plane_no, color, ref_point in MEASUREMENTS:
    eval_obj  = body_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(eval_mesh)
    bm.transform(eval_obj.matrix_world)
    eval_obj.to_mesh_clear()
    bm.faces.ensure_lookup_table()

    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    ret  = bmesh.ops.bisect_plane(bm, geom=geom,
                                   plane_co=tuple(plane_co),
                                   plane_no=tuple(plane_no))
    cut_edges = [e for e in ret['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]

    if not cut_edges:
        bm.free()
        continue

    # BFS bağlı bileşenler
    neighbors = {}
    for e in cut_edges:
        for v in e.verts:
            neighbors.setdefault(v.index, []).append(e)
    visited = set(); components = []
    for start in cut_edges:
        if id(start) in visited: continue
        comp = []; queue = [start]
        while queue:
            e = queue.pop()
            if id(e) in visited: continue
            visited.add(id(e)); comp.append(e)
            for v in e.verts:
                for ne in neighbors.get(v.index, []):
                    if id(ne) not in visited: queue.append(ne)
        components.append(comp)

    if ref_point is not None:
        # Kol: bone orta noktasına en yakın bileşen
        def dist_to_ref(comp):
            vecs = [v.co for e in comp for v in e.verts]
            cx = sum(v.x for v in vecs) / len(vecs)
            cy = sum(v.y for v in vecs) / len(vecs)
            cz = sum(v.z for v in vecs) / len(vecs)
            return (mathutils.Vector((cx, cy, cz)) - ref_point).length
        largest = min(components, key=dist_to_ref)
        circ_cm = sum(e.calc_length() for e in largest) * 100
    else:
        ranked  = sorted(components, key=lambda c: sum(e.calc_length() for e in c), reverse=True)
        largest = ranked[0]
        circ_cm = sum(e.calc_length() for e in largest) * 100
        if circ_cm > 200.0 and len(ranked) > 1:
            second_cm = sum(e.calc_length() for e in ranked[1]) * 100
            if second_cm > 20.0:
                largest = ranked[1]; circ_cm = second_cm

    path = order_loop(largest)
    bm.free()

    if len(path) < 2:
        continue

    # Blender eğri nesnesi
    cd = bpy.data.curves.new(f"c_{label}", 'CURVE')
    cd.dimensions  = '3D'
    cd.bevel_depth = height_m * 0.005   # ~5mm kalınlık (görünür olsun)

    sp = cd.splines.new('POLY')
    sp.points.add(len(path) - 1)
    for i, co in enumerate(path):
        sp.points[i].co = (co.x, co.y, co.z, 1.0)
    sp.use_cyclic_u = True

    co = bpy.data.objects.new(f"c_{label}", cd)
    scene.collection.objects.link(co)
    co.data.materials.append(make_emit_mat(f"m_{label}", color, strength=6.0))

    z_data[label] = {"plane_co": list(plane_co), "circ_cm": round(circ_cm, 2), "color": list(color)}
    print(f"  {label:12s} co={list(round(v,3) for v in plane_co)}  circ={circ_cm:.1f} cm  ({len(path)} pts)")

# Debug JSON (PIL annotation için)
with open(os.path.join(out_dir, f"{char_name}_debug.json"), "w") as f:
    json.dump({
        "char_id":    char_name,
        "z_floor":    z_floor,
        "z_top":      z_top,
        "height_m":   height_m,
        "center_x":   center_x,
        "center_y":   center_y,
        "measurements": z_data,
    }, f, indent=2)

# ── Kamera + render ───────────────────────────────────────────────────────────
FOCAL_MM  = 85.0
SENSOR_MM = 36.0
PADDING   = 1.20
cam_elev  = 8
vfov_half = math.atan(SENSOR_MM / 2.0 / FOCAL_MM)
cam_dist  = (height_m * PADDING) / (2.0 * math.tan(vfov_half))
cam_target = mathutils.Vector((center_x, center_y, z_floor + height_m * 0.50))
elev_rad  = math.radians(cam_elev)

scene.render.engine       = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.image_settings.file_format = 'PNG'

bpy.ops.object.camera_add()
cam_obj = bpy.context.active_object
scene.camera = cam_obj
cam_obj.data.lens         = FOCAL_MM
cam_obj.data.sensor_width = SENSOR_MM

for view_name, angle_deg in [("front", 0), ("right", 90)]:
    a  = math.radians(angle_deg)
    cx = cam_target.x + cam_dist * math.cos(elev_rad) * math.sin(a)
    cy = cam_target.y - cam_dist * math.cos(elev_rad) * math.cos(a)
    cz = cam_target.z + cam_dist * math.sin(elev_rad)
    cam_obj.location       = (cx, cy, cz)
    direction              = cam_target - mathutils.Vector((cx, cy, cz))
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath  = os.path.join(out_dir, f"{char_name}_debug_{view_name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"  [{view_name}] render OK")

print(f"\nDebug tamamlandi: {char_name}")

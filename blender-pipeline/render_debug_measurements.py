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
  bicep     — yellow
  elbow     — lime
  forearm   — purple
  wrist     — pink
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
y_front  = min(ys) - 0.01   # mesh ön yüzeyinin 1 cm önü — genişlik çizgileri buraya çizilir

def mesh_z_span(obj):
    zs = [(obj.matrix_world @ mathutils.Vector(c)).z for c in obj.bound_box]
    return min(zs), max(zs)

body_candidates = [o for o in mesh_objs
                   if mesh_z_span(o)[0] < (z_floor + height_m * 0.15)
                   and mesh_z_span(o)[1] > (z_floor + height_m * 0.70)]
body_obj = max(body_candidates or mesh_objs, key=lambda o: len(o.data.vertices))
print(f"Body mesh: {body_obj.name}")


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

def _seg_entry(label, b0, b1, color, cut_at="mid", radius_factor=0.65, margin_factor=0.35, pick="largest"):
    """
    measure_anthropometry.py::measure_segment_circumference_cm ile senkron.
    ref_point → (p0, p1, radius_factor, margin_factor, pick, cut_pt)
    """
    p0  = bone_world(b0); p1 = bone_world(b1)
    ax  = (p1 - p0).normalized()
    cut_pt = (p0 + p1) * 0.5 if cut_at == "mid" else p1
    return (label, cut_pt, ax, color, (p0, p1, radius_factor, margin_factor, pick, cut_pt))

MEASUREMENTS = [
    # Boyun — yarıçap filtresi yok, merkeze en yakın bileşen seçilir
    _seg_entry("neck",      "CC_Base_NeckTwist01", "CC_Base_NeckTwist02",
                            (0.0, 1.0, 1.0), cut_at="mid", radius_factor=None, margin_factor=0.8, pick="closest"),
    _z_entry("chest",       bone_z("CC_Base_L_Breast"),     (1.0, 0.2, 0.2)),
    _z_entry("waist",       bone_z("CC_Base_Waist"),        (0.2, 1.0, 0.2)),
    _z_entry("hip",         bone_z("CC_Base_L_Thigh") + (bone_z("CC_Base_Waist") - bone_z("CC_Base_L_Thigh")) * 0.15,
                                                             (0.3, 0.5, 1.0)),
    _z_entry("mid_thigh",   (bone_z("CC_Base_L_Thigh") + bone_z("CC_Base_L_Calf")) / 2,
                                                             (1.0, 0.55, 0.0)),
    _z_entry("calf",        bone_z("CC_Base_L_CalfTwist02"),(1.0, 0.0, 1.0)),
    # Kol ölçümleri
    _seg_entry("bicep",   "CC_Base_L_Upperarm", "CC_Base_L_Forearm", (1.0, 1.0, 0.0), cut_at="mid"),
    _seg_entry("elbow",   "CC_Base_L_Upperarm", "CC_Base_L_Forearm", (0.5, 1.0, 0.0), cut_at="end"),
    _seg_entry("forearm", "CC_Base_L_Forearm",  "CC_Base_L_Hand",    (0.7, 0.0, 1.0), cut_at="mid"),
    _seg_entry("wrist",   "CC_Base_L_Forearm",  "CC_Base_L_Hand",    (1.0, 0.4, 0.8), cut_at="end"),
]

# ── Edge loop sıralama ────────────────────────────────────────────────────────
def order_loop(edges):
    """
    Edge listesini sıralı yol olarak döner.
    Açık yaylarda (degree=1 uç vertex) uçtan başlar.
    Junction vertex içeren karmaşık topolojilerde kaçırılan edge'leri
    ikinci dönüş değeri olarak verir.
    Döner: (path: List[Vector], missed_edges: List[BMEdge])
    """
    if not edges:
        return [], []
    adj = {}
    deg = {}
    for e in edges:
        v0, v1 = e.verts
        adj.setdefault(v0.index, []).append((v1, e))
        adj.setdefault(v1.index, []).append((v0, e))
        deg[v0.index] = deg.get(v0.index, 0) + 1
        deg[v1.index] = deg.get(v1.index, 0) + 1

    endpoints = [v for e in edges for v in e.verts if deg[v.index] == 1]
    start_v   = endpoints[0] if endpoints else edges[0].verts[0]

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

    missed = [e for e in edges if id(e) not in visited_e]
    return path, missed

# ── Kontur eğrileri ───────────────────────────────────────────────────────────
z_data = {}

for label, plane_co, plane_no, color, ref_point in MEASUREMENTS:
    eval_obj  = body_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(eval_mesh)
    bm.transform(eval_obj.matrix_world)
    eval_obj.to_mesh_clear()

    # Segment ölçümlerinde çevre geometriyi filtrele
    pick_strategy = "largest"
    seg_cut_pt    = None
    if ref_point is not None:
        p0_seg, p1_seg, r_factor, m_factor, pick_strategy, seg_cut_pt = ref_point
        seg_axis = (p1_seg - p0_seg).normalized()
        bone_len = (p1_seg - p0_seg).length
        margin   = bone_len * m_factor
        remove = []
        for v in bm.verts:
            to_v = v.co - p0_seg
            proj = to_v.dot(seg_axis)
            if proj < -margin or proj > bone_len + margin:
                remove.append(v); continue
            if r_factor is not None:
                if (to_v - seg_axis * proj).length > bone_len * r_factor:
                    remove.append(v)
        bmesh.ops.delete(bm, geom=remove, context='VERTS')

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
        if pick_strategy == "closest":
            def _centroid_dist(comp):
                vecs = [v.co for e in comp for v in e.verts]
                n = len(vecs)
                c = mathutils.Vector((sum(v.x for v in vecs)/n,
                                      sum(v.y for v in vecs)/n,
                                      sum(v.z for v in vecs)/n))
                return (c - seg_cut_pt).length
            largest = min(components, key=_centroid_dist)
        else:
            largest = max(components, key=lambda c: sum(e.calc_length() for e in c))
        circ_cm = sum(e.calc_length() for e in largest) * 100
        draw_comps = [largest]
    else:
        ranked  = sorted(components, key=lambda c: sum(e.calc_length() for e in c), reverse=True)
        primary = ranked[0]
        circ_cm = sum(e.calc_length() for e in primary) * 100
        draw_comps = [primary]

        if circ_cm > 200.0 and len(ranked) > 1:
            second_cm = sum(e.calc_length() for e in ranked[1]) * 100
            if second_cm > 20.0:
                draw_comps = [ranked[1]]; circ_cm = second_cm
        else:
            # Açık yay tespiti: kasık boşluğu gibi durumlarda ikinci yayı da göster
            deg = {}
            for e in primary:
                for v in e.verts:
                    deg[v.index] = deg.get(v.index, 0) + 1
            if any(d == 1 for d in deg.values()) and len(ranked) > 1:
                second_cm = sum(e.calc_length() for e in ranked[1]) * 100
                if second_cm > 5.0:
                    draw_comps.append(ranked[1]); circ_cm += second_cm

        largest = draw_comps[0]

    draw_comps_final = draw_comps if ref_point is None else [largest]

    cd = bpy.data.curves.new(f"c_{label}", 'CURVE')
    cd.dimensions  = '3D'
    cd.bevel_depth = height_m * 0.005

    for comp in draw_comps_final:
        path, missed = order_loop(comp)

        if len(path) >= 2:
            # Açık yay (uç vertex var): use_cyclic_u=True gövde içinden görünmez çizgi çizer.
            # is_open tespiti: path[0] != path[-1] ve missed boş ise açık arc.
            deg_comp = {}
            for e in comp:
                for v in e.verts:
                    deg_comp[v.index] = deg_comp.get(v.index, 0) + 1
            arc_is_open = any(d == 1 for d in deg_comp.values())

            sp = cd.splines.new('POLY')
            sp.points.add(len(path) - 1)
            for i, co in enumerate(path):
                sp.points[i].co = (co.x, co.y, co.z, 1.0)
            sp.use_cyclic_u = not arc_is_open

        # Junction vertex nedeniyle atlanan edge'leri ayrı segment olarak ekle
        for e in missed:
            sp = cd.splines.new('POLY')
            sp.points.add(1)
            v0, v1 = e.verts
            sp.points[0].co = (v0.co.x, v0.co.y, v0.co.z, 1.0)
            sp.points[1].co = (v1.co.x, v1.co.y, v1.co.z, 1.0)
            sp.use_cyclic_u = False

    bm.free()

    co = bpy.data.objects.new(f"c_{label}", cd)
    scene.collection.objects.link(co)
    co.data.materials.append(make_emit_mat(f"m_{label}", color, strength=6.0))

    z_data[label] = {"plane_co": list(plane_co), "circ_cm": round(circ_cm, 2), "color": list(color)}
    print(f"  {label:12s} co={list(round(v,3) for v in plane_co)}  circ={circ_cm:.1f} cm")

# ── Omuz + kalça genişlik çizgileri ──────────────────────────────────────────
def add_width_line(label, z_m, window_m, color, use_apose=False):
    """
    z_m yüksekliğinde max_x - min_x genişliğini çizer.
    use_apose=True: evaluated mesh (A-pose, kollar aşağı) — omuz için kolları dışlar.
    use_apose=False: rest pose vertex'leri — kalça için (kol girişimi yok).
    """
    x_vals = []
    if use_apose:
        eval_obj  = body_obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(eval_mesh)
        bm.transform(eval_obj.matrix_world)
        eval_obj.to_mesh_clear()
        for v in bm.verts:
            if abs(v.co.z - z_m) <= window_m:
                x_vals.append(v.co.x)
        bm.free()
    else:
        for obj in mesh_objs:
            mat = obj.matrix_world
            for v in obj.data.vertices:
                wv = mat @ v.co
                if abs(wv.z - z_m) <= window_m:
                    x_vals.append(wv.x)

    if len(x_vals) < 2:
        return None

    x_min, x_max = min(x_vals), max(x_vals)
    width_cm = round((x_max - x_min) * 100, 2)

    cd = bpy.data.curves.new(f"c_{label}", 'CURVE')
    cd.dimensions  = '3D'
    cd.bevel_depth = height_m * 0.005

    sp = cd.splines.new('POLY')
    sp.points.add(1)
    sp.points[0].co = (x_min, y_front, z_m, 1.0)
    sp.points[1].co = (x_max, y_front, z_m, 1.0)
    sp.use_cyclic_u = False

    co = bpy.data.objects.new(f"c_{label}", cd)
    scene.collection.objects.link(co)
    co.data.materials.append(make_emit_mat(f"m_{label}", color, strength=6.0))

    z_data[label] = {
        "plane_co": [0.0, 0.0, z_m],
        "circ_cm":  width_cm,
        "color":    list(color),
    }
    print(f"  {label:12s} z={z_m:.3f}  width={width_cm:.1f} cm  [{x_min*100:.1f}, {x_max*100:.1f}]")
    return width_cm

z_shoulder = bone_z("CC_Base_L_Upperarm")
z_hip_bone  = bone_z("CC_Base_L_Thigh")

# Omuz genişliği: omuz eklemi (CC_Base_L/R_Upperarm) X konumunu sınır olarak kullan.
# Deltoid eklemi 3-5 cm aşar; kol ise çok daha uzağa gider.
# X filtresi: eklem X'i ± DELTOID_M — deltoid dahil, kol hariç.
p_sh_L     = bone_world("CC_Base_L_Upperarm")
p_sh_R     = bone_world("CC_Base_R_Upperarm")
DELTOID_M  = 0.05   # 5 cm deltoid marjı

# L/R kemik X yönü karakterin bakış tarafına göre değişebilir; min/max ile sıraya al.
x_sh_lo = min(p_sh_L.x, p_sh_R.x) - DELTOID_M
x_sh_hi = max(p_sh_L.x, p_sh_R.x) + DELTOID_M

x_vals_sh = []
for obj in mesh_objs:
    mat = obj.matrix_world
    for v in obj.data.vertices:
        wv = mat @ v.co
        if abs(wv.z - z_shoulder) <= 0.06:
            if x_sh_lo <= wv.x <= x_sh_hi:
                x_vals_sh.append(wv.x)

if x_vals_sh:
    sh_x_min  = min(x_vals_sh)
    sh_x_max  = max(x_vals_sh)
    sh_w_cm   = round((sh_x_max - sh_x_min) * 100, 2)
    sh_z      = z_shoulder
    cd_sh = bpy.data.curves.new("c_shoulder_w", 'CURVE')
    cd_sh.dimensions  = '3D'
    cd_sh.bevel_depth = height_m * 0.005
    sp = cd_sh.splines.new('POLY')
    sp.points.add(1)
    sp.points[0].co = (sh_x_min, y_front, sh_z, 1.0)
    sp.points[1].co = (sh_x_max, y_front, sh_z, 1.0)
    sp.use_cyclic_u = False
    co_sh = bpy.data.objects.new("c_shoulder_w", cd_sh)
    scene.collection.objects.link(co_sh)
    co_sh.data.materials.append(make_emit_mat("m_shoulder_w", (1.0, 1.0, 1.0), strength=6.0))
    z_data["shoulder_w"] = {"plane_co": [0.0, 0.0, sh_z], "circ_cm": sh_w_cm, "color": [1.0, 1.0, 1.0]}
    print(f"  shoulder_w    z={sh_z:.3f}  width={sh_w_cm:.1f} cm  (deltoid+{DELTOID_M*100:.0f}cm)")

# Kalça: mesh vertex genişliği, bu yükseklikte kol yok.
add_width_line("hip_w", z_hip_bone, window_m=0.05, color=(0.8, 0.8, 0.0), use_apose=False)

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

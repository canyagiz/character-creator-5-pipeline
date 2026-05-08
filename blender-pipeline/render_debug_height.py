"""
render_debug_height.py — Blender background script
Çevre ölçümü halkaları + height segment çizgileri tek render'da.
Height çizgileri modelin merkezinde (center_x) dikey ruler olarak gösterilir.

Kullanım:
  blender --background --python render_debug_height.py -- fbx_path out_dir

Çıktı:
  out_dir/<char_id>_height_front.png
  out_dir/<char_id>_height.json
"""

import bpy, bmesh, sys, os, json, math, mathutils

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
    print("ERROR: Armature bulunamadi"); sys.exit(1)

def bone_world(name):
    return arm_obj.matrix_world @ arm_obj.pose.bones[name].head

def bone_z(name):
    return bone_world(name).z

def bone_dist_cm(b0, b1):
    return round((bone_world(b0) - bone_world(b1)).length * 100, 2)

# ── Mesh bounding box ─────────────────────────────────────────────────────────
mesh_objs = [o for o in scene.objects if o.type == 'MESH']
all_corners = []
for obj in mesh_objs:
    for c in obj.bound_box:
        all_corners.append(obj.matrix_world @ mathutils.Vector(c))

z_floor  = min(v.z for v in all_corners)
z_top    = max(v.z for v in all_corners)
xs       = [v.x for v in all_corners]
ys       = [v.y for v in all_corners]
x_min_bb = min(xs); x_max_bb = max(xs)
center_x = (x_max_bb + x_min_bb) / 2.0
center_y = (max(ys)  + min(ys))  / 2.0
y_front  = min(ys) - 0.015
height_m = z_top - z_floor

body_candidates = [o for o in mesh_objs
    if min((o.matrix_world @ mathutils.Vector(c)).z for c in o.bound_box) < z_floor + height_m * 0.15
    and max((o.matrix_world @ mathutils.Vector(c)).z for c in o.bound_box) > z_floor + height_m * 0.70]
body_obj = max(body_candidates or mesh_objs, key=lambda o: len(o.data.vertices))
print(f"Body mesh: {body_obj.name}")

depsgraph = bpy.context.evaluated_depsgraph_get()

# ── Materyaller ───────────────────────────────────────────────────────────────
def make_emit_mat(name, rgb, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    ns = mat.node_tree.nodes; ns.clear()
    e = ns.new('ShaderNodeEmission'); o = ns.new('ShaderNodeOutputMaterial')
    e.inputs["Color"].default_value    = (*rgb, 1.0)
    e.inputs["Strength"].default_value = strength
    mat.node_tree.links.new(e.outputs["Emission"], o.inputs["Surface"])
    return mat

sil_mat = make_emit_mat("Sil", (0.78, 0.78, 0.78), 1.0)
for obj in scene.objects:
    if obj.type == 'MESH':
        obj.data.materials.clear()
        obj.data.materials.append(sil_mat)

scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value    = (0.06, 0.06, 0.06, 1.0)
bg.inputs["Strength"].default_value = 1.0

# ── Yardımcı: edge-loop sıralama ─────────────────────────────────────────────
def order_loop(edges):
    if not edges: return [], []
    adj = {}; deg = {}
    for e in edges:
        for v in e.verts:
            adj.setdefault(v.index, []).append((v if v is not e.verts[0] else e.verts[1], e))
            deg[v.index] = deg.get(v.index, 0) + 1
    # düzelt: her edge için her iki vertex
    adj = {}
    for e in edges:
        v0, v1 = e.verts
        adj.setdefault(v0.index, []).append((v1, e))
        adj.setdefault(v1.index, []).append((v0, e))
        deg[v0.index] = deg.get(v0.index, 0) + 1
        deg[v1.index] = deg.get(v1.index, 0) + 1
    endpoints = [v for e in edges for v in e.verts if deg[v.index] == 1]
    start_v   = endpoints[0] if endpoints else edges[0].verts[0]
    path = [start_v.co.copy()]; visited_e = set(); visited_v = {start_v.index}; current = start_v
    while True:
        moved = False
        for nv, e in adj.get(current.index, []):
            if id(e) not in visited_e and nv.index not in visited_v:
                visited_e.add(id(e)); visited_v.add(nv.index)
                path.append(nv.co.copy()); current = nv; moved = True; break
        if not moved: break
    missed = [e for e in edges if id(e) not in visited_e]
    return path, missed

# ── Çevre halkaları ───────────────────────────────────────────────────────────
def add_ring(label, plane_co, plane_no, color, ref_point=None):
    eval_obj  = body_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(eval_mesh)
    bm.transform(eval_obj.matrix_world)
    eval_obj.to_mesh_clear()

    pick_strategy = "largest"; seg_cut_pt = None
    if ref_point is not None:
        p0, p1, r_factor, m_factor, pick_strategy, seg_cut_pt = ref_point
        ax = (p1 - p0).normalized(); bone_len = (p1 - p0).length; margin = bone_len * m_factor
        remove = []
        for v in bm.verts:
            to_v = v.co - p0; proj = to_v.dot(ax)
            if proj < -margin or proj > bone_len + margin: remove.append(v); continue
            if r_factor is not None and (to_v - ax * proj).length > bone_len * r_factor:
                remove.append(v)
        bmesh.ops.delete(bm, geom=remove, context='VERTS')

    bm.faces.ensure_lookup_table()
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    ret  = bmesh.ops.bisect_plane(bm, geom=geom,
                                   plane_co=tuple(plane_co), plane_no=tuple(plane_no))
    cut_edges = [e for e in ret['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    if not cut_edges: bm.free(); return 0.0

    neighbors = {}
    for e in cut_edges:
        for v in e.verts: neighbors.setdefault(v.index, []).append(e)
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
            def _dist(c):
                vecs = [v.co for e in c for v in e.verts]; n = len(vecs)
                ctr = mathutils.Vector((sum(v.x for v in vecs)/n, sum(v.y for v in vecs)/n, sum(v.z for v in vecs)/n))
                return (ctr - seg_cut_pt).length
            largest = min(components, key=_dist)
        else:
            largest = max(components, key=lambda c: sum(e.calc_length() for e in c))
        circ_cm = sum(e.calc_length() for e in largest) * 100
        draw_comps = [largest]
    else:
        ranked  = sorted(components, key=lambda c: sum(e.calc_length() for e in c), reverse=True)
        primary = ranked[0]; circ_cm = sum(e.calc_length() for e in primary) * 100
        draw_comps = [primary]
        if circ_cm > 200.0 and len(ranked) > 1:
            second_cm = sum(e.calc_length() for e in ranked[1]) * 100
            if second_cm > 20.0: draw_comps = [ranked[1]]; circ_cm = second_cm
        else:
            deg2 = {}
            for e in primary:
                for v in e.verts: deg2[v.index] = deg2.get(v.index, 0) + 1
            if any(d == 1 for d in deg2.values()) and len(ranked) > 1:
                second_cm = sum(e.calc_length() for e in ranked[1]) * 100
                if second_cm > 5.0: draw_comps.append(ranked[1]); circ_cm += second_cm
        largest = draw_comps[0]

    draw_comps_final = draw_comps if ref_point is None else [largest]
    cd = bpy.data.curves.new(f"c_{label}", 'CURVE')
    cd.dimensions = '3D'; cd.bevel_depth = height_m * 0.005
    for comp in draw_comps_final:
        path, missed = order_loop(comp)
        if len(path) >= 2:
            dcomp = {}
            for e in comp:
                for v in e.verts: dcomp[v.index] = dcomp.get(v.index, 0) + 1
            sp = cd.splines.new('POLY'); sp.points.add(len(path) - 1)
            for k, co in enumerate(path): sp.points[k].co = (co.x, co.y, co.z, 1.0)
            sp.use_cyclic_u = not any(d == 1 for d in dcomp.values())
        for e in missed:
            sp = cd.splines.new('POLY'); sp.points.add(1)
            v0, v1 = e.verts
            sp.points[0].co = (v0.co.x, v0.co.y, v0.co.z, 1.0)
            sp.points[1].co = (v1.co.x, v1.co.y, v1.co.z, 1.0)
    bm.free()
    co = bpy.data.objects.new(f"c_{label}", cd)
    scene.collection.objects.link(co)
    co.data.materials.append(make_emit_mat(f"m_{label}", color, strength=6.0))
    print(f"  {label:12s}  circ={circ_cm:.1f} cm")
    return circ_cm

def seg_entry(b0, b1, cut_at="mid", radius_factor=0.65, margin_factor=0.35, pick="largest"):
    p0 = bone_world(b0); p1 = bone_world(b1)
    ax = (p1 - p0).normalized()
    cut_pt = (p0 + p1) * 0.5 if cut_at == "mid" else p1
    return (cut_pt, ax, (p0, p1, radius_factor, margin_factor, pick, cut_pt))

# Ölçüm tanımları
CIRC_MEASUREMENTS = []
def _z(label, z_m, color):
    CIRC_MEASUREMENTS.append((label, mathutils.Vector((0,0,z_m)), mathutils.Vector((0,0,1)), color, None))
def _seg(label, b0, b1, color, cut_at="mid", rf=0.65, mf=0.35, pick="largest"):
    p0 = bone_world(b0); p1 = bone_world(b1); ax = (p1-p0).normalized()
    cut_pt = (p0+p1)*0.5 if cut_at=="mid" else p1
    CIRC_MEASUREMENTS.append((label, cut_pt, ax, color, (p0, p1, rf, mf, pick, cut_pt)))

_seg("neck",      "CC_Base_NeckTwist01", "CC_Base_NeckTwist02", (0.0,1.0,1.0), rf=None, mf=0.8, pick="closest")
_z ("chest",      bone_z("CC_Base_L_Breast"),                   (1.0,0.2,0.2))
_z ("waist",      bone_z("CC_Base_Waist"),                      (0.2,1.0,0.2))
_z ("hip",        bone_z("CC_Base_L_Thigh") + (bone_z("CC_Base_Waist") - bone_z("CC_Base_L_Thigh")) * 0.15,
                                                                 (0.3,0.5,1.0))
_z ("mid_thigh",  (bone_z("CC_Base_L_Thigh") + bone_z("CC_Base_L_Calf")) / 2,
                                                                 (1.0,0.55,0.0))
_z ("calf",       bone_z("CC_Base_L_CalfTwist02"),              (1.0,0.0,1.0))
_seg("bicep",     "CC_Base_L_Upperarm", "CC_Base_L_Forearm",    (1.0,1.0,0.0))
_seg("elbow",     "CC_Base_L_Upperarm", "CC_Base_L_Forearm",    (0.5,1.0,0.0), cut_at="end")
_seg("forearm",   "CC_Base_L_Forearm",  "CC_Base_L_Hand",       (0.7,0.0,1.0))
_seg("wrist",     "CC_Base_L_Forearm",  "CC_Base_L_Hand",       (1.0,0.4,0.8), cut_at="end")

circ_data = {}
for label, plane_co, plane_no, color, ref_point in CIRC_MEASUREMENTS:
    circ_cm = add_ring(label, plane_co, plane_no, color, ref_point)
    circ_data[label] = {
        "plane_co": [round(v, 4) for v in plane_co],
        "circ_cm":  round(circ_cm, 2),
        "color":    list(color),
    }

# ── Omuz + kalça genişlik çizgileri ──────────────────────────────────────────
def add_width_line(label, z_m, window_m, color, use_apose=False, x_lo=None, x_hi=None):
    x_vals = []
    if use_apose:
        eval_obj = body_obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        bm2 = bmesh.new(); bm2.from_mesh(eval_mesh); bm2.transform(eval_obj.matrix_world)
        eval_obj.to_mesh_clear()
        for v in bm2.verts:
            if abs(v.co.z - z_m) <= window_m:
                if (x_lo is None or v.co.x >= x_lo) and (x_hi is None or v.co.x <= x_hi):
                    x_vals.append(v.co.x)
        bm2.free()
    else:
        for obj in mesh_objs:
            mat2 = obj.matrix_world
            for v in obj.data.vertices:
                wv = mat2 @ v.co
                if abs(wv.z - z_m) <= window_m:
                    if (x_lo is None or wv.x >= x_lo) and (x_hi is None or wv.x <= x_hi):
                        x_vals.append(wv.x)
    if len(x_vals) < 2: return None
    x_l, x_r = min(x_vals), max(x_vals)
    width_cm = round((x_r - x_l) * 100, 2)
    cd = bpy.data.curves.new(f"c_{label}", 'CURVE'); cd.dimensions='3D'; cd.bevel_depth=height_m*0.005
    sp = cd.splines.new('POLY'); sp.points.add(1)
    sp.points[0].co = (x_l, y_front, z_m, 1.0)
    sp.points[1].co = (x_r, y_front, z_m, 1.0)
    sp.use_cyclic_u = False
    co = bpy.data.objects.new(f"c_{label}", cd)
    scene.collection.objects.link(co)
    co.data.materials.append(make_emit_mat(f"m_{label}", color, strength=6.0))
    circ_data[label] = {"plane_co": [0.0, 0.0, z_m], "circ_cm": width_cm, "color": list(color)}
    print(f"  {label:12s}  width={width_cm:.1f} cm")
    return width_cm

z_shoulder = bone_z("CC_Base_L_Upperarm")
z_hip_bone = bone_z("CC_Base_L_Thigh")

p_sh_L = bone_world("CC_Base_L_Upperarm"); p_sh_R = bone_world("CC_Base_R_Upperarm")
DELTOID_M = 0.07
x_sh_lo = min(p_sh_L.x, p_sh_R.x) - DELTOID_M
x_sh_hi = max(p_sh_L.x, p_sh_R.x) + DELTOID_M
x_sh_vals = []
for obj in mesh_objs:
    mat2 = obj.matrix_world
    for v in obj.data.vertices:
        wv = mat2 @ v.co
        if abs(wv.z - z_shoulder) <= 0.06 and x_sh_lo <= wv.x <= x_sh_hi:
            x_sh_vals.append(wv.x)
if x_sh_vals:
    sh_x_l = min(x_sh_vals); sh_x_r = max(x_sh_vals); sh_w = round((sh_x_r - sh_x_l)*100, 2)
    cd2 = bpy.data.curves.new("c_shoulder_w", 'CURVE'); cd2.dimensions='3D'; cd2.bevel_depth=height_m*0.005
    sp2 = cd2.splines.new('POLY'); sp2.points.add(1)
    sp2.points[0].co = (sh_x_l, y_front, z_shoulder, 1.0)
    sp2.points[1].co = (sh_x_r, y_front, z_shoulder, 1.0)
    co2 = bpy.data.objects.new("c_shoulder_w", cd2); scene.collection.objects.link(co2)
    co2.data.materials.append(make_emit_mat("m_shoulder_w", (1.0,1.0,1.0), strength=6.0))
    circ_data["shoulder_w"] = {"plane_co": [0.0, 0.0, z_shoulder], "circ_cm": sh_w, "color": [1.0,1.0,1.0]}
    print(f"  shoulder_w    width={sh_w:.1f} cm")

# A-pose'da el/önkol kalça yüksekliğinde geniş X'e sahip → thigh kemiği ile kliple
p_hip_L = bone_world("CC_Base_L_Thigh"); p_hip_R = bone_world("CC_Base_R_Thigh")
HIP_M   = 0.10
add_width_line("hip_w", z_hip_bone, 0.05, (0.8,0.8,0.0),
               x_lo=min(p_hip_L.x, p_hip_R.x) - HIP_M,
               x_hi=max(p_hip_L.x, p_hip_R.x) + HIP_M)

# ── Height segment çizgileri (center_x'te dikey ruler) ───────────────────────
z_foot = bone_z("CC_Base_L_Foot")
z_knee = bone_z("CC_Base_L_Calf")
z_hip  = bone_z("CC_Base_L_Thigh")
z_neck = bone_z("CC_Base_NeckTwist01")
z_head = bone_z("CC_Base_Head")        # boyun üstü / kafa tabanı

lower_leg_cm = bone_dist_cm("CC_Base_L_Calf",  "CC_Base_L_Foot")
upper_leg_cm = bone_dist_cm("CC_Base_L_Thigh", "CC_Base_L_Calf")
torso_cm     = round((z_neck  - z_hip)  * 100, 1)
neck_cm      = round((z_head  - z_neck) * 100, 1)
head_cm      = round((z_top   - z_head) * 100, 1)
foot_cm      = round((z_foot  - z_floor)* 100, 1)
total_cm     = round((z_top   - z_floor)* 100, 2)

SEGMENTS = [
    ("foot",      z_floor, z_foot,  foot_cm,      (0.55, 0.55, 0.55)),
    ("lower_leg", z_foot,  z_knee,  lower_leg_cm, (1.0,  0.0,  1.0 )),
    ("upper_leg", z_knee,  z_hip,   upper_leg_cm, (1.0,  0.55, 0.0 )),
    ("torso",     z_hip,   z_neck,  torso_cm,     (0.2,  1.0,  0.2 )),
    ("neck",      z_neck,  z_head,  neck_cm,      (0.0,  1.0,  1.0 )),
    ("head",      z_head,  z_top,   head_cm,      (0.9,  0.6,  0.1 )),
    ("total",     z_floor, z_top,   total_cm,     (1.0,  1.0,  1.0 )),
]

# Merkez x'te, gövdenin tam önünde dikey segment çizgileri
# Her segment kendi z aralığını kaplar → üst üste binme yok
# Yatay "tick" işaretleri segment sınırlarında
y_ruler = y_front - 0.008   # çevre halkalarının biraz önünde

TICK     = 0.022             # tick işareti yarı genişliği (m)
BEVEL_SEG = height_m * 0.004
BEVEL_TOT = height_m * 0.006  # total çizgisi biraz daha kalın

# Segment sınırları (tekrarlanmayan)
boundaries = sorted({z_floor, z_foot, z_knee, z_hip, z_neck, z_top})

seg_data = {}
for label, z_lo, z_hi, length_cm, color in SEGMENTS:
    bevel = BEVEL_TOT if label == "total" else BEVEL_SEG
    cd = bpy.data.curves.new(f"h_{label}", 'CURVE')
    cd.dimensions = '3D'; cd.bevel_depth = bevel

    # Dikey çizgi
    sp = cd.splines.new('POLY'); sp.points.add(1)
    sp.points[0].co = (center_x, y_ruler, z_lo, 1.0)
    sp.points[1].co = (center_x, y_ruler, z_hi, 1.0)

    # Alt tick
    sp2 = cd.splines.new('POLY'); sp2.points.add(1)
    sp2.points[0].co = (center_x - TICK, y_ruler, z_lo, 1.0)
    sp2.points[1].co = (center_x + TICK, y_ruler, z_lo, 1.0)

    # Üst tick
    sp3 = cd.splines.new('POLY'); sp3.points.add(1)
    sp3.points[0].co = (center_x - TICK, y_ruler, z_hi, 1.0)
    sp3.points[1].co = (center_x + TICK, y_ruler, z_hi, 1.0)

    co = bpy.data.objects.new(f"h_{label}", cd)
    scene.collection.objects.link(co)
    co.data.materials.append(make_emit_mat(f"m_h_{label}", color, strength=7.0))

    seg_data[label] = {
        "z_lo":      round(z_lo,  4),
        "z_hi":      round(z_hi,  4),
        "z_mid":     round((z_lo + z_hi) / 2, 4),
        "length_cm": length_cm,
        "color":     list(color),
    }
    print(f"  {label:<12}  {length_cm:.1f} cm  ({z_lo*100:.1f} → {z_hi*100:.1f})")

# ── JSON ──────────────────────────────────────────────────────────────────────
with open(os.path.join(out_dir, f"{char_name}_height.json"), "w") as f:
    json.dump({
        "char_id":      char_name,
        "z_floor":      round(z_floor,  4),
        "z_top":        round(z_top,    4),
        "height_m":     round(height_m, 4),
        "height_cm":    total_cm,
        "center_x":     round(center_x, 4),
        "center_y":     round(center_y, 4),
        "measurements": circ_data,
        "segments":     seg_data,
    }, f, indent=2)

# ── Kamera + render ───────────────────────────────────────────────────────────
FOCAL_MM = 85.0; SENSOR_MM = 36.0; PADDING = 1.20; cam_elev = 8
vfov_half = math.atan(SENSOR_MM / 2.0 / FOCAL_MM)
cam_dist  = (height_m * PADDING) / (2.0 * math.tan(vfov_half))
cam_target = mathutils.Vector((center_x, center_y, z_floor + height_m * 0.5))
elev_rad  = math.radians(cam_elev)

scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 512; scene.render.resolution_y = 512
scene.render.image_settings.file_format = 'PNG'

bpy.ops.object.camera_add()
cam_obj = bpy.context.active_object; scene.camera = cam_obj
cam_obj.data.lens = FOCAL_MM; cam_obj.data.sensor_width = SENSOR_MM

cx = cam_target.x
cy = cam_target.y - cam_dist * math.cos(elev_rad)
cz = cam_target.z + cam_dist * math.sin(elev_rad)
cam_obj.location = (cx, cy, cz)
cam_obj.rotation_euler = (cam_target - mathutils.Vector((cx,cy,cz))).to_track_quat('-Z','Y').to_euler()
scene.render.filepath = os.path.join(out_dir, f"{char_name}_height_front.png")
bpy.ops.render.render(write_still=True)
print(f"\nTamamlandi: {char_name}  height={total_cm} cm")

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

    ranked  = sorted(components, key=lambda c: sum(e.calc_length() for e in c), reverse=True)
    primary = ranked[0]
    total_cm = sum(e.calc_length() for e in primary) * 100

    if total_cm > 200.0 and len(ranked) > 1:
        second_cm = sum(e.calc_length() for e in ranked[1]) * 100
        if second_cm > 20.0:
            print(f"  [WARN] circ {total_cm:.1f} cm > 200, 2nd component {second_cm:.1f} cm kullaniliyor")
            total_cm = second_cm
    else:
        # Açık yay tespiti: kasık boşluğu gibi mesh gap'larında uç vertex'ler degree=1 olur.
        deg = {}
        for e in primary:
            for v in e.verts:
                deg[v.index] = deg.get(v.index, 0) + 1
        is_open = any(d == 1 for d in deg.values())
        if is_open:
            # Gap mesafesini (iki uç vertex arası düz çizgi) ölçüme ekle.
            # Fiziksel şerit metre bu boşluğu düz geçer.
            ep_positions = [v.co.copy() for e in primary for v in e.verts
                            if deg[v.index] == 1]
            if len(ep_positions) >= 2:
                gap_cm = (ep_positions[0] - ep_positions[1]).length * 100
                total_cm += gap_cm

    bm.free()
    return round(total_cm, 2)

# ── Referans yükseklikleri ────────────────────────────────────────────────────
z_chest     = bone_z("CC_Base_L_Breast")
z_waist     = bone_z("CC_Base_Waist")
z_hip       = bone_z("CC_Base_L_Thigh") + (bone_z("CC_Base_Waist") - bone_z("CC_Base_L_Thigh")) * 0.15
z_mid_thigh = (bone_z("CC_Base_L_Thigh") + bone_z("CC_Base_L_Calf")) / 2
z_calf      = bone_z("CC_Base_L_CalfTwist02")

# ── Genel kemik-eksen çevre ölçümü: vertex filtresi + eksene dik bisect ──────
def measure_segment_circumference_cm(bone_start_name, bone_end_name,
                                     cut_at="mid", radius_factor=0.65, margin_factor=0.35,
                                     pick="largest"):
    """
    bone_start → bone_end segmenti boyunca vertex filtresi uygular, ardından
    segment eksenine dik düzlemde keser.
    cut_at        : "mid" → segment ortası | "end" → bone_end pozisyonu
    radius_factor : bone_len çarpanı. None → yarıçap filtresi uygulanmaz (sadece eksen marjı)
    margin_factor : eksen boyunca marj çarpanı
    pick          : "largest" → en uzun bileşen (kol) | "closest" → cut_pt'ye en yakın (boyun)
    """
    p0       = bone_world(bone_start_name)
    p1       = bone_world(bone_end_name)
    axis     = (p1 - p0).normalized()
    bone_len = (p1 - p0).length

    cut_pt = (p0 + p1) * 0.5 if cut_at == "mid" else p1
    margin = bone_len * margin_factor

    eval_obj  = body_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(eval_mesh)
    bm.transform(eval_obj.matrix_world)
    eval_obj.to_mesh_clear()

    remove = []
    for v in bm.verts:
        to_v = v.co - p0
        proj = to_v.dot(axis)
        if proj < -margin or proj > bone_len + margin:
            remove.append(v)
            continue
        if radius_factor is not None:
            if (to_v - axis * proj).length > bone_len * radius_factor:
                remove.append(v)
    bmesh.ops.delete(bm, geom=remove, context='VERTS')
    bm.faces.ensure_lookup_table()

    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    ret  = bmesh.ops.bisect_plane(bm, geom=geom,
                                   plane_co=(cut_pt.x, cut_pt.y, cut_pt.z),
                                   plane_no=(axis.x,   axis.y,   axis.z))
    cut_edges = [e for e in ret['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    if not cut_edges:
        bm.free()
        return 0.0

    neighbors = {}
    for e in cut_edges:
        for v in e.verts:
            neighbors.setdefault(v.index, []).append(e)
    visited = set(); components = []
    for start_e in cut_edges:
        if id(start_e) in visited: continue
        comp = []; queue = [start_e]
        while queue:
            e = queue.pop()
            if id(e) in visited: continue
            visited.add(id(e)); comp.append(e)
            for v in e.verts:
                for ne in neighbors.get(v.index, []):
                    if id(ne) not in visited: queue.append(ne)
        components.append(comp)

    if pick == "closest":
        def centroid_dist(comp):
            vecs = [v.co for e in comp for v in e.verts]
            n = len(vecs)
            c = mathutils.Vector((sum(v.x for v in vecs)/n,
                                  sum(v.y for v in vecs)/n,
                                  sum(v.z for v in vecs)/n))
            return (c - cut_pt).length
        best = min(components, key=centroid_dist)
    else:
        best = max(components, key=lambda c: sum(e.calc_length() for e in c))

    circ_cm = sum(e.calc_length() for e in best) * 100
    bm.free()
    return round(circ_cm, 2)

# ── Lateral genişlik ölçümü (T-pose rest vertices) ───────────────────────────
def measure_width_cm(z_m, window_m=0.06):
    """
    T-pose'da z_m yüksekliğinde ±window_m penceresi içindeki tüm mesh
    vertex'lerinin max_x - min_x genişliğini cm cinsinden döndürür.
    Rest pose (T-pose) vertex'leri kullanır — evaluated depsgraph değil.
    """
    x_vals = []
    for obj in mesh_objs:
        mat = obj.matrix_world
        for v in obj.data.vertices:
            wv = mat @ v.co
            if abs(wv.z - z_m) <= window_m:
                x_vals.append(wv.x)
    if len(x_vals) < 2:
        return 0.0
    return round((max(x_vals) - min(x_vals)) * 100, 2)

# Referans yükseklikleri
z_shoulder_bone = bone_z("CC_Base_L_Upperarm")
z_hip_bone      = bone_z("CC_Base_L_Thigh")

# ── Omuz genişliği: omuz eklemi X'i + 7 cm deltoid marjı ──────────────────────
# T-pose'da kollar yatay olduğundan Z filtresi kolu yakalar.
# Çözüm: omuz kemiği X pozisyonunu sınır al, ötesini dışla.
_p_sh_L   = arm_obj.matrix_world @ arm_obj.pose.bones["CC_Base_L_Upperarm"].head
_p_sh_R   = arm_obj.matrix_world @ arm_obj.pose.bones["CC_Base_R_Upperarm"].head
_DELT_M   = 0.07
_x_sh_lo  = min(_p_sh_L.x, _p_sh_R.x) - _DELT_M
_x_sh_hi  = max(_p_sh_L.x, _p_sh_R.x) + _DELT_M
_sh_xs    = []
for _obj in mesh_objs:
    _mat = _obj.matrix_world
    for _v in _obj.data.vertices:
        _wv = _mat @ _v.co
        if abs(_wv.z - z_shoulder_bone) <= 0.06 and _x_sh_lo <= _wv.x <= _x_sh_hi:
            _sh_xs.append(_wv.x)
shoulder_width_cm = round((max(_sh_xs) - min(_sh_xs)) * 100, 2) if len(_sh_xs) >= 2 else 0.0

# ── Ölçümler ──────────────────────────────────────────────────────────────────
measurements = {
    # Boyun: NeckTwist01–NeckTwist02 ortası, yarıçap filtresi yok (obez boyunları keser)
    # pick="closest" → merkeze en yakın bileşen = boyun (omuz değil)
    "neck_circ_cm":      measure_segment_circumference_cm(
                             "CC_Base_NeckTwist01", "CC_Base_NeckTwist02",
                             cut_at="mid", radius_factor=None, margin_factor=0.8,
                             pick="closest"),
    "chest_circ_cm":     measure_circumference_cm(z_chest),
    "waist_circ_cm":     measure_circumference_cm(z_waist),
    "hip_circ_cm":       measure_circumference_cm(z_hip),
    "mid_thigh_circ_cm": measure_circumference_cm(z_mid_thigh),
    "calf_circ_cm":      measure_circumference_cm(z_calf),
    "bicep_circ_cm":    measure_segment_circumference_cm("CC_Base_L_Upperarm", "CC_Base_L_Forearm", cut_at="mid"),
    "elbow_circ_cm":    measure_segment_circumference_cm("CC_Base_L_Upperarm", "CC_Base_L_Forearm", cut_at="end"),
    "forearm_circ_cm":  measure_segment_circumference_cm("CC_Base_L_Forearm",  "CC_Base_L_Hand",    cut_at="mid"),
    "wrist_circ_cm":    measure_segment_circumference_cm("CC_Base_L_Forearm",  "CC_Base_L_Hand",    cut_at="end"),

    "shoulder_width_cm":  shoulder_width_cm,
    "hip_width_cm":       measure_width_cm(z_hip_bone, window_m=0.05),

    "upper_arm_length_cm": bone_dist_cm("CC_Base_L_Upperarm", "CC_Base_L_Forearm"),
    "forearm_length_cm":   bone_dist_cm("CC_Base_L_Forearm",  "CC_Base_L_Hand"),
    "total_arm_length_cm": bone_dist_cm("CC_Base_L_Upperarm", "CC_Base_L_Hand"),
    "upper_leg_length_cm": bone_dist_cm("CC_Base_L_Thigh",    "CC_Base_L_Calf"),
    "lower_leg_length_cm": bone_dist_cm("CC_Base_L_Calf",     "CC_Base_L_Foot"),
    "total_leg_length_cm": bone_dist_cm("CC_Base_L_Thigh",    "CC_Base_L_Foot"),

}

# ── Kaydet (meta JSON'a merge et) ─────────────────────────────────────────────
out_path = os.path.join(out_dir, f"{char_name}_meta.json")
meta = {}
if os.path.exists(out_path):
    with open(out_path) as f:
        meta = json.load(f)
meta.update(measurements)
with open(out_path, "w") as f:
    json.dump(meta, f, indent=2)

print(f"\n{char_name}:")
for k, v in measurements.items():
    print(f"  {k:<28} {v}")
print(f"\n-> {out_path}")

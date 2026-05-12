"""
render_views.py — Blender background script
Her FBX için 8 yönde iki pass:
  1. Raw  — orijinal materyaller + 3 nokta ışık
  2. Silhouette — karakter beyaz, arkaplan siyah

Kullanım:
  blender --background --python render_views.py -- <fbx_path> <raw_dir> <sil_dir> <meta_dir>
"""

import bpy
import math
import sys
import os
import json
import mathutils

# ── Args ──────────────────────────────────────────────────────────────────────
argv     = sys.argv[sys.argv.index("--") + 1:]
fbx_path = argv[0]
raw_dir  = argv[1]
sil_dir  = argv[2]
meta_dir = argv[3]

for d in (raw_dir, sil_dir, meta_dir):
    os.makedirs(d, exist_ok=True)

char_name = os.path.splitext(os.path.basename(fbx_path))[0]

# ── Sahneyi temizle + FBX import ──────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.fbx(filepath=fbx_path, use_image_search=False)

# ── Bounds ────────────────────────────────────────────────────────────────────
all_coords = []
for obj in scene.objects:
    if obj.type == 'MESH':
        for corner in obj.bound_box:
            all_coords.append(obj.matrix_world @ mathutils.Vector(corner))

if not all_coords:
    print(f"ERROR: mesh bulunamadi — {fbx_path}")
    sys.exit(1)

xs = [v.x for v in all_coords]
ys = [v.y for v in all_coords]
zs = [v.z for v in all_coords]

height_cm = (max(zs) - min(zs)) * 100
height_m  = max(zs) - min(zs)
center_x  = (max(xs) + min(xs)) / 2
center_y  = (max(ys) + min(ys)) / 2
z_bot     = min(zs)

cam_target = mathutils.Vector((center_x, center_y, z_bot + height_m * 0.50))
cam_elev   = 8

FOCAL_MM  = 85.0
SENSOR_MM = 36.0
PADDING   = 1.20
vfov_half = math.atan(SENSOR_MM / 2.0 / FOCAL_MM)
cam_dist  = (height_m * PADDING) / (2.0 * math.tan(vfov_half))

# ── Meta JSON ─────────────────────────────────────────────────────────────────
with open(os.path.join(meta_dir, f"{char_name}_meta.json"), "w") as f:
    json.dump({"char_id": char_name, "height_cm": round(height_cm, 2)}, f)
print(f"Height: {height_cm:.2f} cm")

# ── Render base ayarları ──────────────────────────────────────────────────────
scene.render.engine       = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.image_settings.file_format = 'PNG'

# ── Kamera ────────────────────────────────────────────────────────────────────
bpy.ops.object.camera_add()
cam_obj = bpy.context.active_object
scene.camera = cam_obj
cam_obj.data.lens         = FOCAL_MM
cam_obj.data.sensor_width = SENSOR_MM

VIEWS = [
    ("front",       0),
    ("front_right", 45),
    ("right",       90),
    ("back_right",  135),
    ("back",        180),
    ("back_left",   225),
    ("left",        270),
    ("front_left",  315),
]

elev_rad = math.radians(cam_elev)

def position_camera(angle_deg):
    a  = math.radians(angle_deg)
    cx = cam_target.x + cam_dist * math.cos(elev_rad) * math.sin(a)
    cy = cam_target.y - cam_dist * math.cos(elev_rad) * math.cos(a)
    cz = cam_target.z + cam_dist * math.sin(elev_rad)
    cam_obj.location       = (cx, cy, cz)
    direction              = cam_target - mathutils.Vector((cx, cy, cz))
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def set_world(r, g, b):
    scene.world = bpy.data.worlds.new("W")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value    = (r, g, b, 1.0)
    bg.inputs["Strength"].default_value = 1.0

def render_pass(out_dir, label):
    for view_name, angle_deg in VIEWS:
        position_camera(angle_deg)
        scene.render.filepath = os.path.join(out_dir, f"{char_name}_{view_name}.png")
        bpy.ops.render.render(write_still=True)
    print(f"  [{label}] 8 render OK -> {out_dir}")

# ══════════════════════════════════════════════════════════════════════════════
# PASS 1 — Raw (orijinal materyaller + 3 nokta ışık)
# ══════════════════════════════════════════════════════════════════════════════
set_world(0.15, 0.15, 0.15)

def add_light(name, offset, energy, color=(1, 1, 1), size_mult=2.5):
    loc = cam_target + mathutils.Vector(offset)
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.active_object
    l.name = name
    l.data.energy = energy
    l.data.size   = height_m * size_mult  # büyük ışık → yumuşak specular
    l.data.color  = color
    l.rotation_euler = (cam_target - loc).to_track_quat('-Z', 'Y').to_euler()

r = height_m
add_light("Key",  ( r*0.8, -r*0.8,  r*0.6), 130)
add_light("Fill", (-r*0.6, -r*0.5,  r*0.2),  80, (0.9, 0.95, 1.0))
add_light("Rim",  ( 0,      r*1.2,  r*0.4),  35)

render_pass(raw_dir, "raw")

# ══════════════════════════════════════════════════════════════════════════════
# PASS 2 — Silhouette (karakter beyaz, arkaplan siyah, ışık yok)
# ══════════════════════════════════════════════════════════════════════════════

# Işıkları kaldır
for obj in [o for o in scene.objects if o.type == 'LIGHT']:
    bpy.data.objects.remove(obj, do_unlink=True)

# Arkaplan siyah
set_world(0.0, 0.0, 0.0)

# Bloom sızdırmasını önle
if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'use_bloom'):
    scene.eevee.use_bloom = False

# Ton haritalama olmadan ham renk çıktısı (0.0 → 0, 1.0 → 255)
scene.view_settings.view_transform = 'Raw'
scene.view_settings.look            = 'None'
scene.view_settings.gamma           = 1.0
scene.view_settings.exposure        = 0.0

# Compositor: her pikseli 0 ya da 1'e yuvarla (hard threshold @ 0.5)
scene.use_nodes = True
ctree = scene.node_tree
for n in list(ctree.nodes):
    ctree.nodes.remove(n)
rl_node   = ctree.nodes.new('CompositorNodeRLayers')
rgb2bw    = ctree.nodes.new('CompositorNodeRGBToBW')
gt_node   = ctree.nodes.new('CompositorNodeMath')
gt_node.operation = 'GREATER_THAN'
gt_node.inputs[1].default_value = 0.5
comp_node = ctree.nodes.new('CompositorNodeComposite')
ctree.links.new(rl_node.outputs['Image'], rgb2bw.inputs['Image'])
ctree.links.new(rgb2bw.outputs['Val'],    gt_node.inputs[0])
ctree.links.new(gt_node.outputs['Value'], comp_node.inputs['Image'])

# Tüm mesh'lere beyaz emission
mat = bpy.data.materials.new("Silhouette")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()
emit   = nodes.new('ShaderNodeEmission')
out_n  = nodes.new('ShaderNodeOutputMaterial')
emit.inputs["Color"].default_value    = (1.0, 1.0, 1.0, 1.0)
emit.inputs["Strength"].default_value = 1.0
links.new(emit.outputs["Emission"], out_n.inputs["Surface"])

for obj in scene.objects:
    if obj.type == 'MESH':
        obj.data.materials.clear()
        obj.data.materials.append(mat)

render_pass(sil_dir, "silhouette")

print(f"\nTamamlandi: {char_name}")

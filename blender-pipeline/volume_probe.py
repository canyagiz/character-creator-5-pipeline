"""
volume_probe.py — Blender background script
Verilen FBX listesi için mesh hacmini hesaplar (bmesh.calc_volume).

Kullanım (batch_volume_probe.py tarafından çağrılır):
  blender --background --python volume_probe.py -- <fbx_path> <out_json>
"""

import bpy
import bmesh
import sys
import os
import json

argv     = sys.argv[sys.argv.index("--") + 1:]
fbx_path = argv[0]
out_json = argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.fbx(filepath=fbx_path)

mesh_objs = [o for o in scene.objects if o.type == 'MESH']
if not mesh_objs:
    print(f"ERROR: Mesh bulunamadi — {fbx_path}")
    sys.exit(1)

# En büyük mesh = body (vertex sayısına göre)
body_obj = max(mesh_objs, key=lambda o: len(o.data.vertices))

bm = bmesh.new()
bm.from_mesh(body_obj.data)
# World-space transform uygula (scale dahil)
bmesh.ops.transform(bm, matrix=body_obj.matrix_world, verts=bm.verts)
volume_m3 = abs(bm.calc_volume())
bm.free()

result = {
    "fbx":       os.path.basename(fbx_path),
    "mesh_name": body_obj.name,
    "volume_m3": volume_m3,
    "volume_L":  volume_m3 * 1000,
}

with open(out_json, "w") as f:
    json.dump(result, f, indent=2)

print(f"[volume_probe] {os.path.basename(fbx_path)} → {volume_m3*1000:.3f} L")

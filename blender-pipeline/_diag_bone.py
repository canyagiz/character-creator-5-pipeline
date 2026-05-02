import bpy, math, mathutils, sys

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=argv[0])

arm_obj = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')

pbone = arm_obj.pose.bones['CC_Base_L_Upperarm']
w_before = (arm_obj.matrix_world @ pbone.matrix).translation.copy()
print(f"BEFORE head world: {w_before}")

current_world = arm_obj.matrix_world @ pbone.matrix.copy()
rot = mathutils.Matrix.Rotation(math.radians(45), 4, 'Y')
pbone.matrix = arm_obj.matrix_world.inverted() @ (rot @ current_world)
bpy.context.view_layer.update()

w_after = (arm_obj.matrix_world @ pbone.matrix).translation.copy()
print(f"AFTER  head world: {w_after}")
print(f"Delta: {w_after - w_before}")

# Also check evaluated depsgraph
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_arm = arm_obj.evaluated_get(depsgraph)
ep = eval_arm.pose.bones['CC_Base_L_Upperarm']
w_eval = (eval_arm.matrix_world @ ep.matrix).translation.copy()
print(f"EVAL   head world: {w_eval}")

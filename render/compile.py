"""Blender-side scene compiler.

Reads a scene.json produced by `python -m meble compile-scene` (boxes in mm: name, size, center, color)
and builds geometry, frames a camera, adds light, and renders a PNG. Uses only json + bpy/bmesh (no
extra deps), so Blender's bundled Python is enough.

Usage (Blender NOT required to be on PATH for the rest of the toolchain — only for rendering):
    blender --background --python render/compile.py -- <scene.json> <out.png> [--glb out.glb]

Everything here is disposable: it is rebuilt from the YAML every run. There is no hand-edited .blend
of your designs (see CLAUDE.md → Render artifacts).
"""
import json
import math
import sys

try:
    import bpy
    import bmesh
    from mathutils import Vector
except ImportError:
    print("This script must be run inside Blender:  blender --background --python render/compile.py -- ...")
    sys.exit(1)

MM = 0.001  # mm -> metres


def argv_after_ddash():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.6
    return mat


def add_box(name, size, center, rgb):
    sx, sy, sz = (v * MM for v in size)
    cx, cy, cz = (v * MM for v in center)
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    obj.scale = (sx, sy, sz)
    obj.location = (cx, cy, cz)
    obj.data.materials.append(material(name + "_mat", rgb))
    return obj


def frame_all(objects):
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objects:
        for corner in o.bound_box:
            wc = o.matrix_world @ Vector(corner)
            mn = Vector(map(min, mn, wc))
            mx = Vector(map(max, mx, wc))
    center = (mn + mx) / 2
    radius = max((mx - mn).length / 2, 0.5)

    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    d = radius * 2.6
    cam.location = center + Vector((d, -d, d * 0.8))
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam

    sun_data = bpy.data.lights.new("Sun", type="SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.location = center + Vector((d, -d, d * 1.5))
    sun.rotation_euler = (math.radians(50), 0, math.radians(40))
    bpy.context.collection.objects.link(sun)

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.9, 0.9, 0.92, 1.0)
        bg.inputs[1].default_value = 1.0
    bpy.context.scene.world = world


def render(out_png):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"          # more reliable headless than Eevee
    scene.cycles.samples = 48
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)


def main():
    args = argv_after_ddash()
    if len(args) < 2:
        print("usage: blender --background --python render/compile.py -- <scene.json> <out.png> [--glb out.glb]")
        sys.exit(1)
    scene_path, out_png = args[0], args[1]
    glb = args[args.index("--glb") + 1] if "--glb" in args else None

    with open(scene_path) as f:
        scene = json.load(f)

    reset_scene()
    objs = []
    for o in scene.get("objects", []):
        if o.get("type") == "box":
            objs.append(add_box(o["name"], o["size"], o["center"], o.get("color", [0.85, 0.85, 0.83])))
    if not objs:
        print("scene has no boxes; nothing to render")
        sys.exit(1)

    frame_all(objs)
    render(out_png)
    print(f"rendered {len(objs)} object(s) -> {out_png}")
    if glb:
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB")
        print(f"exported -> {glb}")


if __name__ == "__main__":
    main()

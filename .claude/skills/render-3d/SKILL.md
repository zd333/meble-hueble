---
name: render-3d
description: Render a 3D preview (Blender) of cabinets or a whole set/run from this meble repo, including reused IKEA METOD/PAX units. Use when the user wants to visualize, preview, or render a cabinet/kitchen/wardrobe layout in 3D, or export a glTF/glb model.
---

# render-3d

Two steps so Blender needs no extra Python deps:

1. **Resolve** the design to a flat JSON scene (boxes in mm, from panel roles/placements + cabinet
   positions; readymade units render as a box or their `model_ref`):
   ```bash
   python -m meble compile-scene --set kitchen          # -> out/scene.json
   # also: --cabinet <id> | --apartment <id> | --out <file>
   ```
2. **Render** with Blender (must be installed; see below):
   ```bash
   blender --background --python render/compile.py -- out/scene.json out/kitchen.png
   # optional glTF:  ... -- out/scene.json out/kitchen.png --glb out/kitchen.glb
   ```
   `compile-scene` prints the exact render command for the chosen scope.

## Notes
- Everything is generated into `out/` (git-ignored) and rebuilt from YAML each run — **no hand-edited
  `.blend` of the design exists**; nothing to keep in sync (see CLAUDE.md → Render artifacts).
- Custom cabinets are built from their panels (placement derived from `role`, or an explicit
  `panel.placement`). Reused IKEA units render as a box unless their library entry sets `model_ref` to a
  curated `.glb`/`.blend` under `library/units/models/`.
- **Home Builder 5** is an optional, manual-only tool (open `out/*.glb` or a `--save-blend` snapshot) —
  not on this automation path.

## If Blender isn't installed
`compile-scene` still produces `out/scene.json`. Install Blender (`brew install --cask blender` on macOS,
then `blender` is at `/Applications/Blender.app/Contents/MacOS/Blender`) or point the user at it. The
render step is the only part that needs Blender; the rest of the toolchain does not.

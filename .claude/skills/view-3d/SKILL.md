---
name: view-3d
description: Open an interactive 3D viewer (browser) of cabinets or a whole set/run from this meble repo. Use when the user wants to see, preview, inspect, rotate, or visualize a cabinet/kitchen/wardrobe in 3D, or look at how it goes together (exploded view). The viewer supports orbit/zoom/pan, preset views, exploded view, per-panel isolate/hide, and labels with cut dimensions.
---

# view-3d

Builds a self-contained `out/viewer.html` from the design and opens it in the browser. No Blender — the
viewer renders the same scene the tool computes (`build_scene`), with cabinet-aware interaction.

## Run
```bash
python -m meble view --set kitchen          # whole set
python -m meble view --cabinet d60-base     # one cabinet
python -m meble view --apartment bohaterow  # everything
# flags: --no-serve (just write the html) · --port N · --out FILE
```
This writes `out/viewer.html`, starts a small **localhost** server, and opens your browser. Press
**Ctrl-C** in the terminal to stop the server when you're done. (`task view` wraps this.)

## In the viewer
- **Drag** = rotate · **scroll** = zoom · **right-drag** = pan.
- **Preset views**: Front / Back / Left / Right / Top / Iso.
- **Exploded** slider — slides panels apart along their normals to show construction.
- **Panels** list — checkbox to show/hide; click a name to **isolate** it; "Show all panels" resets.
- **Hover** a panel to highlight it and show its cut size; "Show all labels" pins every label.

## Notes
- Generated into `out/` (git-ignored) and rebuilt from YAML each run — nothing to keep in sync.
- **three.js loads from a CDN, so the viewer needs internet at view time.** (If that ever matters,
  vendoring three.js locally is a small change.)
- ES-module pages can't load from `file://`, which is why it's served over localhost (handled for you).
- Reused IKEA units currently render as a labelled box; their `model_ref` (`library/units/models/*.glb`)
  is reserved for a later phase that loads real models via three.js `GLTFLoader`.

Run from the repo root with the venv active and `PYTHONPATH=tools`.

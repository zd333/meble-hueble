---
name: validate-design
description: Validate cabinet designs in this meble repo for consistency — broken material/band/hardware refs, out-of-bounds or illegal drill holes, bad banding edges, orphan stamped holes, and readymade-unit sanity. Use before exporting CSV/PDF or placing an order, or whenever the user wants to check a design.
---

# validate-design

Static consistency checks. There is no regeneration safety net (panels are the source of truth), so run
this before exporting or ordering.

## Run
```bash
python -m meble validate --apartment bohaterow   # all sets/cabinets in an apartment
python -m meble validate --set kitchen           # one set
python -m meble validate --cabinet open-900      # one cabinet
python -m meble validate                         # everything in the repo
```

## What it checks
- Refs resolve: `material` → board, edge band ids → `edgebands.yaml`, fitting `hardware` → `hardware.yaml`,
  fitting `through`/`into` → real panels.
- Holes in bounds and legal: edge bore Ø∈{4,8}, depth 2–35, within edge length; surface bore
  Ø∈{3,5,8,10,15,20,35}, depth 2–15 or `through`, within the panel; `multi` holes have the required
  `count`/`spacing`(/`direction`).
- Banding edges are 1–4.
- **Warnings:** orphan stamped holes (a hole's `src` has no matching fitting — usually means a fitting
  was removed; re-run `meble fit` or delete the hole).
- Readymade units have positive actual width/depth/height.

Exit code is non-zero if there are errors. Run from the repo root with the venv active and
`PYTHONPATH=tools`.

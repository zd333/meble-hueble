---
name: generate-order-csv
description: Export the centrum.meble.pl PRO100 CSV (panel dimensions, quantity, grain, coarse banding) from cabinet designs in this meble repo. Use when the user wants to import panels into the meble.pl editor, generate the cut/parts list CSV, or prepare an order. One CSV per board model.
---

# generate-order-csv

Produces the CSV the meble.pl editor imports. It carries **only what the import accepts** — panel name,
width, height, thickness, quantity, grain (`Słoje`), and coarse per-axis banding marks (`=`/`-`/blank).
Rich per-edge banding, band model, drilling and grooving are entered manually from the PDF spec sheet.
We never produce a cutting layout — meble.pl owns nesting.

## Run
```bash
python -m meble csv --set kitchen          # all cabinets in a set
python -m meble csv --cabinet open-900     # one cabinet
python -m meble csv --apartment bohaterow  # everything in an apartment
# -> out/csv/<board-id>.csv  (one file per board model; out/ is git-ignored)
```

## Then
1. In the meble.pl editor, create/confirm the **board** (model + thickness) matching each CSV's board id.
2. Import the matching `out/csv/<board>.csv` under that board.
3. Use `generate-panel-pdf` to fill in banding + drilling by hand for each panel.

## /!\ Some panels export rotated 180° — this is deliberate

When a panel bands ONE edge of an axis, the import always puts that band on **edge 3** (width axis) or
**edge 4** (height axis). The mark is a count, not an identity, and nothing overrides it. So a panel
banding edge 1 or 2 alone is exported turned 180° (`tools/meble/normalize.py`), which says the same
thing in a frame the importer can express.

The **PDF applies the same rotation** and marks those pages with a banner — so the two always agree,
and the user should type each sheet exactly as drawn. Such a page will disagree with the 3D viewer
about which end is "top"; that is expected. The finished panel is identical either way.

**Never "fix" this by rotating the YAML** — `meble fit` re-derives stamped holes in the canonical
frame and would silently undo it, leaving banding and drilling contradicting each other.

If `meble csv` prints a `TICK EDGE n BY HAND` warning, that panel's two axes want opposite ends and no
rotation can fix it; relay the list to the user so they tick those boxes. It should normally be empty.

Details of the format (columns, banding symbols, `Słoje` codes) and the measurement behind the
edge-3/edge-4 rule are in `docs/meblepl-editor.md`. Run `task test` after touching the exporters.
Run from the repo root with the venv active and `PYTHONPATH=tools`.

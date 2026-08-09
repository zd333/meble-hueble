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

Details of the format (columns, banding symbols, `Słoje` codes) are in `docs/meblepl-editor.md`.
Run from the repo root with the venv active and `PYTHONPATH=tools`.

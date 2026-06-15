---
name: generate-panel-pdf
description: Generate per-panel PDF spec sheets (to-scale diagrams + tables, in the meble.pl editor's field order, with a check column) from cabinet designs in this meble repo. Use when the user needs a printable/visual reference for manually entering edge banding and drilling into the meble.pl editor, or a clean summary of a panel/set.
---

# generate-panel-pdf

Builds a PDF: a linked index, then **one page per panel** with two to-scale diagrams (front + back face,
edges numbered 1–4, holes plotted), followed by tables for size, edge banding, and drilling — laid out in
the editor's entry order, each row with a check box to track manual entry.

## Run
```bash
python -m meble pdf --set kitchen          # all cabinets in a set
python -m meble pdf --cabinet d60-base     # one cabinet
python -m meble pdf --apartment bohaterow  # everything
# -> out/pdf/<scope>.pdf   (out/ is git-ignored)
```

## Notes
- Reads only the panels (the source of truth). If you changed fittings, run `python -m meble fit
  --cabinet <id>` first so stamped holes appear; auto-stamped holes are marked `(auto)` on the sheet.
- Holes drawn green = surface, red = edge; hollow circle = drill-through.
- To order a subset, scope with `--cabinet` (repeat per cabinet) or point `--set` at a set containing
  only the cabinets you need.

Run from the repo root with the venv active and `PYTHONPATH=tools`. Requires `reportlab` (in
`tools/requirements.txt`).

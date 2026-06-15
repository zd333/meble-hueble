---
name: design-cabinet
description: Author or edit a cabinet design (panels, fittings, drilling) in this meble repo. Use when the user wants to create, modify, or extend a cabinet/wardrobe/kitchen unit — e.g. "build a base cabinet", "add a shelf/drawer", "make a built-in wardrobe", "add another confirmat/hinge here". Covers scaffolding a new cabinet, editing panels, and stamping holes from fittings.
---

# design-cabinet

Guided authoring of cabinet YAML. **Panels are the single source of truth** — read `CLAUDE.md` and
`docs/schema.md` first; never invent a parallel representation.

## Where things go
- New/edited cabinet → `apartments/<apartment>/sets/<set>/cabinets/<id>.yaml`.
- Boards/bands/hardware/reusable parts/IKEA units → `library/` (reuse existing ids; add new entries there).
- Construction numbers (carcass formulas, drill patterns, standard dims) → `docs/cabinet-construction.md`.

## Workflow

1. **Clarify** dimensions, category (base/wall/tall/wardrobe), construction (default `confirmat`),
   material + edge band (reuse a `library/materials.yaml` / `edgebands.yaml` id, or add one), and the
   internal layout (shelves, later: doors/drawers).
2. **Scaffold** a starting point (optional but fast):
   ```bash
   python -m meble scaffold base --width 600 --height 720 --depth 560 --id d60-base --name "Szafka dolna 600"
   ```
   It prints YAML — save it to the cabinet path above. The scaffold is one-shot: after saving you own
   and edit the file freely.
3. **Edit panels** directly. Apply the conventions in `CLAUDE.md`:
   - carcass `top/bottom length = width − 2×thickness` (e.g. `W−36`);
   - edges `1=top 2=right 3=bottom 4=left`; coords from bottom-left; mm.
   - Band only visible edges; pick `glue_type` (`long` default).
   - Left/right sides with through-face drilling are usually distinct panels (`bok-l`, `bok-r`).
4. **Fittings & holes.** To join panels, add a fitting under `assembly.fittings` (see `docs/schema.md`)
   and stamp its holes:
   ```bash
   python -m meble fit --cabinet <id>
   ```
   `fit` is safe and idempotent: it only (re)writes holes whose `src` matches the fitting; **manual holes
   are never touched.** Add an extra screw either by adding a fitting (it stamps) or by adding a hole by
   hand to the panel's `holes` list.
5. **Validate**: `python -m meble validate --cabinet <id>` — fix any errors (bad refs, out-of-bounds
   holes, illegal Ø/depth).
6. Hand off to `generate-order-csv` / `generate-panel-pdf` / `render-3d`.

## Notes
- `element_type` stays `panel` (carcass). `front`/`countertop` are reserved for later iterations.
- Reusable sub-assembly (e.g. a drawer box) → a file in `library/parts/`, referenced from
  `cabinet.parts[]` with a quantity; its panels flow into the list ×quantity.
- Run all commands from the repo root with the venv active and `PYTHONPATH=tools` (see CLAUDE.md).

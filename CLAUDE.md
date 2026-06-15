# meble — cabinet furniture design & ordering workspace

This repo is the **source of truth** for flat-pack MFC cabinet designs (as YAML) and the **knowledge
base** + **tools** to turn them into orders at **centrum.meble.pl** and into 3D previews. It's driven from
Claude Code sessions — everything a fresh session needs is in this file + `docs/` + `.claude/skills/`, so
you should not need to re-interview the user.

## What we're doing

The user designs cabinets, then orders the cut panels at centrum.meble.pl. That editor has no export and
stores state server-side, so banding/drilling/grooving are re-typed by hand each time. So we:
1. keep designs as YAML (this repo),
2. export the meble.pl **CSV** (panel dimensions — kills the most tedious typing),
3. generate a per-panel **PDF spec sheet** (diagram + tables, in the editor's field order) for fast,
   low-error manual entry of banding/drilling,
4. render **3D previews** (Blender), with first-class reuse of ready-made IKEA METOD/PAX units.

Bias: **simple, cheap, popular** materials & methods — MFC, confirmat screws (default), minifix, rafix,
euro hinges, drawer slides. Nothing exotic.

Typical session: *"help me build a base cabinet / wardrobe for X"* → discuss → write/update the cabinet
YAML → `validate` → `csv` + `pdf` (+ `render`) → user places the order.

## The data model (read this before editing designs)

**Panels are the single source of truth for the order.** A cabinet is a collection of panels (each a
box: material, W×H×thickness, grain, per-edge banding, an explicit list of drill `holes`, reserved
`grooving`). The CSV and PDF read **only** the panels. This mirrors PRO100 (every element is a panel; the
cutlist is a projection over the panels actually present).

Two **peer** layers live alongside, and are **never** order-relevant:
- **`placement`** — where each panel sits in the cabinet's local frame. Only for grouping + 3D viz.
- **`assembly.fittings`** — confirmat/hinge/etc. objects that reference the panels they join. *Applying* a
  fitting (`meble fit`) **stamps** the matching holes onto those panels (each tagged `src: <fittingId>`).
  After that the holes are owned by the panel and freely editable.

Key rules:
- **Nothing regenerates panels.** There is one representation of what gets ordered, so there's nothing to
  keep in sync. Adding an extra screw = add a fitting (it stamps) or add a hole by hand. Both first-class.
- `meble fit` is **idempotent and safe**: it only replaces holes whose `src` matches the fitting;
  **manual holes (no `src`) are never touched.**
- **Templates are one-shot scaffolds** (`meble scaffold`): they seed a new cabinet's panels once; you then
  own and edit them. Re-running scaffolds a fresh cabinet, it does not re-bind an existing one.
- **`element_type`** on a panel is `panel` (carcass board) for now; `front` and `countertop` are reserved
  first-class kinds (separate meble.pl products) added in later iterations — additively, no restructure.
- **We never compute a cutting layout** (nesting/`rozkrój`) — meble.pl owns that. We emit the panel list.

Full field reference: **`docs/schema.md`**. Editor fields + CSV format: **`docs/meblepl-editor.md`**.

## Conventions

- **mm** everywhere. Coordinate origin **bottom-left**; width → X, height → Y.
- Edges: **1 = top, 2 = right, 3 = bottom, 4 = left**.
- Edge-hole distance from 0: left for top/bottom (1,3), bottom for left/right (2,4). Surface holes: x,y
  from bottom-left.
- **Faces are `outer` (visible outside) / `inner` (toward cavity)** — never front/back. One panel frame;
  the face only picks the **drill side** (x,y are NOT mirrored between faces). Editor mapping: outer →
  przód (front), inner → tył (back). Confirmat heads → outer; shelf-pin/System-32/hinge holes → inner.
- **Left & right sides are MIRROR parts** (front edge = 2 on the left, 4 on the right; asymmetric holes
  mirror too) — never identical. Full table + edge cases: **`docs/conventions.md`** (read before drilling).
- Edge-band thickness only **1 or 2 mm**; glue default **long** ("kryjące długie").
- `grain` default **forces orientation** (panels never rotate). `any|width|height` → CSV `Słoje` 0|2|1.
- Carcass (top/bottom **between** sides): **`top/bottom length = width − 2×thickness`** (e.g. `W−36`).
- Ball-bearing drawer box width = `internal − 25.4`. System-32 = **Ø5, 32 mm pitch, 37 mm front setback**.
- **Prefer bulk (multi) drilling.** Whenever holes form a regular series — a shelf-pin column, a
  System-32 row, repeated confirmats along a seam — specify **one `multi` hole** (`count` + `spacing`,
  plus `direction` for surface holes), **not N singles**. In the editor a multi hole is one entry
  instead of N, so it's far less manual typing and can be cheaper. `meble fit` already collapses
  evenly-spaced fitting screws into a multi hole — do the same when adding holes by hand. Only fall back
  to singles for genuinely irregular positions.

## Quick-reference drill table (supplier convention — verify before first order)

| Fitting               | Face hole              | Edge hole | Notes |
|-----------------------|------------------------|-----------|-------|
| Confirmat (l=45)      | Ø8 + countersink       | Ø4 d≈35   | default carcass joint; edge Ø4 (editor allows 4/8); ≥50 mm from end |
| Minifix 15            | Ø15 cam + Ø8 dowel     | Ø5 bolt   | knock-down, hidden |
| Rafix 20              | Ø20 housing (~14 deep) | Ø5 bolt   | faster, pricier |
| Dowel Ø8 (l=30)       | Ø8                     | Ø8        | alignment |
| Hinge cup             | Ø35 (~12 deep) + 2 scr | —         | boring dist 3–6, center ~22.5 from door edge |
| Shelf pin / plate     | Ø5                     | —         | on 32 mm grid, 37 mm setback |

Board 18 mm, back 3 mm HDF. Deep dive: **`docs/cabinet-construction.md`**. IKEA reuse:
**`docs/ikea-metod-pax-reference.md`**.

## Tools (run from repo root)

Convenient entry point: **`task <name>`** (see `Taskfile.yml`; `task --list`). Most take a scope after
`--`, e.g. `task pdf -- --cabinet d60-base`. User-facing tasks: `list`, `review`, `csv`, `pdf`, `render`,
`setup`. The design internals (`scaffold`, `fit`, `validate`) are `python -m meble …` commands the
`design-cabinet` / `cabinet-review` skills run for you during a session — not surfaced as tasks. Full CLI: 

```bash
source .venv/bin/activate && export PYTHONPATH=tools     # one-time per shell
python -m meble list                                     # what's in the project
python -m meble validate --apartment bohaterow           # schema/bounds checks
python -m meble review   --apartment bohaterow           # domain linter (mirror, carcass math, wrong face…)
python -m meble scaffold base --width 600 --height 720 --depth 560   # seed a new cabinet (prints YAML)
python -m meble fit  --cabinet d60-base                  # (re)stamp holes from fittings (safe/idempotent)
python -m meble csv  --set kitchen                       # -> out/csv/<board>.csv   (import to meble.pl)
python -m meble pdf  --set kitchen                        # -> out/pdf/<set>.pdf     (manual-entry sheets)
python -m meble compile-scene --set kitchen              # -> out/scene.json
# then: blender --background --python render/compile.py -- out/scene.json out/render.png
```
`--cabinet <id>`, `--set <id>`, or `--apartment <id>` select scope for most commands.

Skills wrap these: **design-cabinet** (author/edit + scaffold + fit), **generate-order-csv**,
**generate-panel-pdf**, **render-3d**, **validate-design**, and **cabinet-review** (independent
domain-expert review: runs `meble review` + a skeptical LLM pass against a growing pitfall checklist,
report-only). Run `cabinet-review` before ordering. All real logic is in `tools/meble/`.

## Render artifacts

Everything Blender is **generated on the fly into `out/` (git-ignored)** and rebuilt from YAML each run —
nothing to keep in sync. There is **no hand-edited `.blend` of your designs**. The only committed
Blender data is `library/units/models/*.glb` — curated 3rd-party reference models for reused IKEA units.

## Layout map

- `apartments/<a>/sets/<s>/cabinets/*.yaml` — the designs (currently apartment `bohaterow`).
- `library/` — boards, edge bands, hardware (with drill patterns), reusable parts & IKEA units.
- `docs/` — knowledge base (schema, editor/CSV, cabinet construction, IKEA reference).
- `tools/meble/` — Python package + CLI. `render/compile.py` — Blender side. `.claude/skills/` — workflows.

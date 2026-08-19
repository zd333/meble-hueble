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
4. open an interactive **3D viewer** (browser — orbit/zoom, exploded view, isolate panels), with reuse
   of ready-made IKEA METOD/PAX units.

Bias: **simple, cheap, popular** materials & methods — MFC, confirmat screws (default), minifix, rafix,
euro hinges, drawer slides. Nothing exotic.

Typical session: *"help me build a base cabinet / wardrobe for X"* → discuss → write/update the cabinet
YAML → `validate` → `csv` + `pdf` (+ `view`) → user places the order.

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
  **manual holes (no `src`) are never touched.** Flip side: it only stamps **perimeter butt joints** (the
  seam runs along one of the through panel's own edges). Cam hardware, mid-face T-joints, and joints
  whose two panels measure the seam from different origins are skipped with a warning and written by
  hand — and **hand-written holes do not follow a resize.** Re-derive them yourself when dimensions move.
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
- **Faces are `outer` (visible outside) / `inner` (toward cavity)** — never front/back. That gloss
  **inverts on a `top` panel** (its outer faces DOWN into the cabinet); the frame is fixed by the
  joinery, not by what you can see — see `docs/conventions.md`. One panel frame;
  the face only picks the **drill side** (x,y are NOT mirrored between faces). Editor mapping: outer →
  przód (front), inner → tył (back). Confirmat heads → outer; shelf-pin/System-32/hinge holes → inner.
- **Left & right sides are MIRROR parts** (front edge = 2 on the left, 4 on the right; asymmetric holes
  mirror too) — never identical. Full table + edge cases: **`docs/conventions.md`** (read before drilling).
- **The CSV import can only band edge 3 or edge 4** when a panel bands ONE edge of an axis — the mark is
  a *count*, not an identity, and no token overrides it (measured against the live editor 2026-08-17).
  So `tools/meble/normalize.py` exports such a panel turned **180°**, in the CSV and the PDF together;
  those PDF pages carry a banner, and they will disagree with the 3D viewer about which end is "top".
  **Author designs in the YAML frame and ignore this** — it is presentation-only, applied on the way
  out, and never stored (a rotation in YAML would be silently undone by the next `meble fit`).
- **Every dimension is the FINISHED size — banding is included, never added on top.** The size you type
  into the meble.pl editor is the finished element, so YAML sizes go in as-is: **never** subtract band
  thickness on banded axes, and never inflate a panel to "leave room" for the band. (Confirmed against
  the live editor.) So e.g. two 417-wide doors + a 2 mm gap really do fill an 836 carcass.
- **Pick the joint by whether the screw head is ever seen.** Default to **confirmat** wherever the head
  lands on a face nobody looks at: the underside of a bottom/divider, the top face of a top panel, an
  internal gable's end joints, anything inside a sealed boxing, a carcass face against a wall. Confirmats
  are cheaper than cam fittings, faster to assemble, need no Ø20 housing bore (so far less to type into
  the editor), and pull a T-joint tighter. Reach for a cam fitting only when the head would otherwise
  sit on a show face — or when the joint is meant to be taken apart repeatedly, since a confirmat's Ø4
  pilot strips after a few cycles.
- **The cam fitting is `rafix-20`, and it is the only one.** Two holes per joint, not three: the Ø20
  housing sits **9.5 mm** from the seam edge so its bore breaks out there and the bolt enters directly.
  Minifix puts its Ø15 cam ~34 mm back and needs a third bore — a Ø8 channel in from the edge — which
  is an extra hole to be charged for and an extra line to type. Do not mix the two; `minifix-15` stays
  in the library as reference only.
- **meble.pl will CUT a panel longer than 2500 mm but will NOT DRILL it** (told to us 2026-08-18 while
  entering an order). So a tall side panel is only orderable as drawn if it carries no holes — and a
  carcass side always carries holes. Both bathroom columns were shortened for this: `wc-column`
  2524 → 2500 and `wm-wardrobe` 2520 → 2500. **Take the height off the part of the cabinet that is
  free to move**, never off a dimension something physical sets: the WC cover is fixed by the cistern
  frame and the laundry bay by the appliance stack, so in both cases the loss came out of the cabinet
  ABOVE. `tests/test_designs.py` enforces the limit, so a future design cannot quietly re-cross it.
- **Panel `width`/`height` must be whole millimetres.** The CSV writes them as integers, so a half-mm
  dimension is silently rounded away in the order. Choose envelope numbers that keep every *derived*
  size whole — e.g. 736 wide rather than 735, so the two doors land on 367 and not 366.5. Hole
  coordinates are exempt: 22.5 for a hinge cup is fine.
- Edge-band thickness only **1 or 2 mm**; glue default **long** ("kryjące długie").
- `grain` default **forces orientation** (panels never rotate). `any|width|height` → CSV `Słoje` 0|2|1.
- Carcass (top/bottom **between** sides): **`top/bottom length = width − 2×thickness`** (e.g. `W−36`).
- Ball-bearing drawer box width = `internal − 25.4`. System-32 = **Ø5, 32 mm pitch, 37 mm front setback**.
- **Hardware you BUY is declared on the fitting, never inferred from holes** (`meble hardware`). Three
  fields carry it: **`variant:`** — a purchasing difference the drilling cannot express, above all hinge
  overlay (a door on an outer side is `full`; two doors sharing a divider are `half`, and the cup and
  plate line are IDENTICAL, so nothing else can tell them apart); **`quantity:`** — defaults to
  `len(at)`, stated explicitly when it differs (a shelf-pin fitting's `at` is a list of shelf HEIGHTS,
  and each shelf takes 4 pins); and **`drilling:`** — `stamped` (default, `meble fit` owns the holes),
  `manual` (hand-derived, tagged `src:`, fit leaves them alone), or `none` (no holes by design, e.g.
  drawer slides mounted on site). Counting hardware from drill holes is wrong twice over: a hole does
  not know what it is for, and the count is not the quantity.
- **A fitting's PARTS are its own; how a shop packages them is the vendor's.** `components:` on the
  hardware lists the logical parts of one fitting (a hinge is arm+cup **plus** a plate; a rafix is
  housing **plus** bolt). `sourcing:` lists offerings, each saying which components it `covers:` — one
  for a loose part, several for a bundle. `meble hardware` resolves per vendor and **reports any
  component nothing covers**, because 10 hinges with no plates hangs zero doors. Prices there are
  indicative and carry a `checked:` date; they are never a quote (same lesson as `meble pack`).
- **Prefer bulk (multi) drilling.** Whenever holes form a regular series — a shelf-pin column, a
  System-32 row, repeated confirmats along a seam — specify **one `multi` hole** (`count` + `spacing`,
  plus `direction` for surface holes), **not N singles**. In the editor a multi hole is one entry
  instead of N, so it's far less manual typing and can be cheaper. `meble fit` already collapses
  evenly-spaced fitting screws into a multi hole — do the same when adding holes by hand. Only fall back
  to singles for genuinely irregular positions.
- **A gable/divider with shelves on BOTH sides gets ONE `depth: through` pin column pair, not two
  opposing blind ones.** Two Ø5 × 13 bores facing each other in an 18 mm panel add up to 26 mm: they
  meet in the middle and you get a ragged, drill-wandered through-hole whether you asked for one or not.
  Ask for it on purpose — half the holes, and both compartments' shelves land on the *same* x, so they
  are supported identically. Buy pins **with a collar/flange** (two meet mid-panel at ~9 mm each, which
  is plenty; a plain collarless peg has nothing to stop it). `meble review` does **not** catch the
  opposing-bore case — it only checks one hole at a time against the thickness. Blind is still right for
  a side panel, where a through Ø5 would show on the outside.
- **A floor-to-ceiling cabinet gets NO screw driven down through its top panel.** If the unit finishes a
  few mm under the ceiling there is no room for a bit, a driver or a hand above it — before *or* after
  installation — so any fixing whose head lands on the top panel's up face is undrivable, and assembling
  the box flat first only postpones the problem (you still cannot re-tighten it). This kills the obvious
  way to fix a back panel's or a gable's TOP edge. Fix those panels at the **sides**, from **below**, or
  along the **rear edge into the back panel** instead, and leave the top edge simply butted — a back
  screwed along both vertical edges is already a shear diaphragm. Check the whole design by asking of
  every fitting: *which direction does the driver come from, and is that space still there once the unit
  is in place?* Height, depth and against-a-wall all constrain it. `meble review` does not check this.
- **Shelf-pin depth 13 is the System-32 line-boring standard**, not a requirement of the pin (a Ø5 pin
  engages ~10 mm). On a blind bore the extra is free clearance; it is never a reason to thin a panel.
- **Fixed pins beat an adjustable column when drilling is charged per hole.** A full System-32 run over a
  1.5 m cabinet is ~40 holes *per column* — 328 across four columns, vs 32 for four chosen heights.
  Decide the shelf heights against the storage boxes you will actually buy, order the 32, and drill more
  by hand later if you need them (depth stop + a shelf-pin jig).
- **The half sheet is 2800 × 1032 — narrower, NOT shorter.** It is the full 2800 × 2070 sheet ripped down
  its length, so it takes a full-height 2520 mm gable just as happily. Never assume the smaller format
  means smaller panels: writing it down as 2070 × 1032 once barred every tall panel from it.
- **We do NOT work out how many sheets to buy.** meble.pl will sell a part sheet and their optimiser
  never matched our predictions, so a local estimate was worse than none — it invited confident
  decisions from numbers that turned out wrong. Send the panel list, take their quote. (`meble pack`
  and `decor_optional` existed for this and were removed 2026-08-18.)
- **Which decor a hidden panel rides is still a real choice, just not an arithmetic one.** Decide it on
  looks and on what offcuts you actually have; never move a panel whose face you can see.

## Quick-reference drill table (supplier convention — verify before first order)

| Fitting               | Face hole              | Edge hole | Notes |
|-----------------------|------------------------|-----------|-------|
| Confirmat (l=45)      | Ø8 + countersink       | Ø4 d≈35   | default carcass joint; edge Ø4 (editor allows 4/8); ≥50 mm from end |
| **Rafix 20** (our cam) | Ø20 housing ~14 deep, axis **9.5** from the edge | Ø5 bolt d12 | **2 holes**; bore breaks out at the edge so the bolt enters — no channel |
| Minifix 15 (not used)  | Ø15 cam + Ø8 edge channel | Ø5 bolt | 3 holes; cam sits ~34 mm back |
| Dowel Ø8 (l=30)       | Ø8                     | Ø8        | alignment |
| Hinge cup             | Ø35 (~12 deep) + 2 scr | —         | boring dist 3–6, center ~22.5 from door edge |
| Shelf pin / plate     | Ø5                     | —         | on 32 mm grid, 37 mm setback |

Board 18 mm, back 3 mm HDF. Deep dive: **`docs/cabinet-construction.md`**. IKEA reuse:
**`docs/ikea-metod-pax-reference.md`**.

## Tools (run from repo root)

Convenient entry point: **`task <name>`** (see `Taskfile.yml`; `task --list`). Most take a scope after
`--`, e.g. `task pdf -- --cabinet open-900`. User-facing tasks: `list`, `review`, `test`, `csv`, `pdf`,
`hardware`, `view`, `setup`. The design internals (`scaffold`, `fit`, `validate`) are `python -m meble …` commands the
`design-cabinet` / `cabinet-review` skills run for you during a session — not surfaced as tasks. Full CLI: 

```bash
source .venv/bin/activate && export PYTHONPATH=tools     # one-time per shell
python -m meble list                                     # what's in the project
python -m meble validate --apartment bohaterow           # schema/bounds checks
python -m meble review   --apartment bohaterow           # domain linter (mirror, carcass math, wrong face…)
python -m meble scaffold base --width 600 --height 720 --depth 560   # seed a new cabinet (prints YAML)
python -m meble fit  --cabinet open-900                  # (re)stamp holes from fittings (safe/idempotent)
python -m meble hardware --apartment bohaterow           # -> what to BUY + out/pdf/<scope>-hardware.pdf
python -m meble csv  --set kitchen                       # -> out/csv/<board>.csv   (import to meble.pl)
python -m meble pdf  --set kitchen                        # -> out/pdf/<set>.pdf     (manual-entry sheets)
python -m meble view --set kitchen                       # interactive 3D viewer (opens browser)
.venv/bin/python -m pytest -q                            # or `task test` — run before you trust an export
```
`--cabinet <id>`, `--set <id>`, or `--apartment <id>` select scope for most commands.

**Tests (`tests/`) are the safety net — run them.** A wrong export costs a sheet of MFC and a
re-order, so the exact bytes of both CSVs and the text of the whole PDF are locked as goldens
(`tests/golden/`, regenerate with `tests/regen_golden.py` and **read the diff**). `meble fit`'s
"never touch a manual hole" contract, the carcass arithmetic, every `review`/`validate` rule and the
export-time rotation are all covered.

Skills wrap these: **design-cabinet** (author/edit + scaffold + fit), **generate-order-csv**,
**generate-panel-pdf**, **view-3d**, **validate-design**, and **cabinet-review** (independent
domain-expert review: runs `meble review` + a skeptical LLM pass against a growing pitfall checklist,
report-only). Run `cabinet-review` before ordering. All real logic is in `tools/meble/`.

## Viewer artifacts

The 3D viewer (`meble view`) writes a self-contained **`out/viewer.html`** (git-ignored), rebuilt from
YAML each run — nothing to keep in sync. three.js loads from a **CDN** (needs internet at view time);
ES-module pages can't load from `file://`, so `view` serves it on localhost and opens the browser for you.
Reused IKEA units render as a labelled box; `library/units/models/*.glb` + `model_ref` are **reserved**
for a later phase that loads real models via three.js `GLTFLoader`.

## Layout map

- `apartments/<a>/sets/<s>/cabinets/*.yaml` — the designs (currently apartment `bohaterow`).
- `library/` — boards, edge bands, hardware (with drill patterns), reusable parts & IKEA units.
- `docs/` — knowledge base (schema, editor/CSV, cabinet construction, IKEA reference).
- `tools/meble/` — Python package + CLI. `viewer/template.html` — the interactive 3D viewer.
  `.claude/skills/` — workflows.

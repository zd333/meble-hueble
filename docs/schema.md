# YAML schema reference

The data model. **Panels are the single source of truth** for what gets ordered; `assembly` (fittings)
and `placement` are peer layers for assembly/visualization only. Nothing regenerates panels — see
[CLAUDE.md](../CLAUDE.md) for the philosophy. All lengths in **mm**.

## Hierarchy & files

```
library/materials.yaml      boards (MFC + HDF)            -> referenced by id
library/edgebands.yaml      edge bands                    -> referenced by id
library/hardware.yaml       fasteners + their drill data  -> referenced by id
library/parts/*.yaml        reusable sub-assemblies (drawer box, ...)
library/units/*.yaml        reusable ready-made units (IKEA)
apartments/<a>/apartment.yaml
apartments/<a>/sets/<s>/set.yaml
apartments/<a>/sets/<s>/cabinets/<c>.yaml
```

`apartment → set → cabinet → (part) → panel`. Refs are by short string id; ids are unique within their
kind.

## Board (`materials.yaml: boards[]`)
```yaml
- id: w1100-18              # used in panel.material
  name: "Egger Biały W1100 ST9"
  vendor: Egger
  decor_code: W1100
  texture: ST2
  thickness: 18            # mm; panels inherit this unless they override
  grain_directional: false # true for woodgrains (affects sensible default grain)
  color: "#F2F1ED"         # optional hint for 3D render
```

## Sheet formats — not modelled

We do **not** describe stock sheets or compute how many to buy. meble.pl will sell a part sheet and
their cutting optimiser never matched a local estimate, so the estimate was worse than no estimate:
send them the panel list and take their quote. `library/materials.yaml` keeps the formats as a
comment only, for the one fact worth remembering — the 2800 × 1032 half sheet is **narrower, not
shorter**, so it still takes a full-height 2520 mm gable.

## Hardware you buy (`assembly.fittings[]`)

A fitting is both a joint and a **line on the shopping list** (`meble hardware`). Three optional
fields carry the purchasing side; all default sensibly, so existing fittings need nothing.

```yaml
- id: hg-door-r
  hardware: hinge-clip-110
  variant: half            # a PURCHASING difference the drilling cannot express. Must be one of the
                           # hardware's `variants:`. Hinge overlay is the case that matters: the cup
                           # and plate line are identical for full/half/inset, so this is the only
                           # place the difference can live.
  drilling: manual         # stamped (default) = `meble fit` computes the holes
                           # manual            = holes are hand-derived and tagged `src: <this id>`
                           # none              = no holes at all, by design (a slide mounted on site)
  quantity: 16             # how many to BUY. Defaults to len(at); state it when it differs — a
                           # shelf-pin fitting's `at` is a list of shelf HEIGHTS, 4 pins per shelf.
  door: door-r             # panel refs; `shelves:` takes a list
  side: gable-mid
  at: [1312, 1868, 2424]
```

`drilling: manual` and `none` are skipped by `meble fit` **silently** — they are deliberate, not
unimplemented, and warning about them on every run is how a warning stops being read.

## Edge band (`edgebands.yaml: edgebands[]`)
```yaml
- id: eb-w1100-1
  name: "ABS Biały W1100 1mm"
  decor_code: W1100
  texture: ST2
  thickness: 1             # 1 | 2  (the only variants the editor supports)
```

## Hardware (`hardware.yaml: hardware[]`)
Carries the **drill pattern** that fittings stamp. Shape varies by `type`:
```yaml
- id: confirmat-7x50
  type: confirmat
  drill: { face: {dia: 8, countersink: true}, edge: {dia: 5, depth: 35} }
- id: minifix-15
  type: minifix
  drill: { cam: {dia: 15, depth: 13}, dowel: {dia: 8}, bolt: {dia: 5} }
- id: dowel-8x30
  type: dowel
  drill: { face: {dia: 8, depth: 15}, edge: {dia: 8, depth: 15} }
- id: hinge-clip-110
  type: hinge
  drill: { cup: {dia: 35, depth: 12, boring: 5}, plate: {pattern: system32, screws: 2} }
```

## What a fitting is made of, and how a shop sells it (`hardware.yaml`)

One fitting is often several physical parts — a hinge is an arm+cup **plus** a mounting plate, a rafix
is a housing **plus** a bolt. **How those map onto things you can buy is a property of the vendor, not
of the fitting**: Blum sells the hinge and the plate as two article numbers, while cheaper ranges sell
"zawias z prowadnikiem" as one. So the two are modelled separately.

```yaml
- id: hinge-clip-110
  components:                    # the logical parts of ONE fitting; vendor-independent
    - { id: hinge, name: "arm + Ø35 cup", per_variant: true }
    - { id: plate, name: "mounting plate (prowadnik)" }
  sourcing:                      # offerings. `covers:` lists the components each one satisfies
    - vendor: centrum.meble.pl
      covers: [hinge]            # one part only — Blum sells them apart
      variant: half              # optional: narrows the offering to one variant
      sku: 71T3650
      name: "Blum CLIP top 110° bliźniaczy, ze sprężyną"
      price: 7.37                # INDICATIVE, and only meaningful with `checked:`
      checked: 2026-08-18
    - vendor: cheap-shop
      covers: [hinge, plate]     # a bundle — one purchase satisfies both parts
      sku: SET-1
```

`meble hardware [--vendor V]` resolves them and **reports any component nothing covers**. That check
is the point: 10 hinges with no mounting plates hangs exactly zero doors, and the shopping list is
where that has to surface rather than at assembly.

**Prices are indicative and dated.** `checked:` is when someone last looked; the sheet prints it, flags
anything older than `PRICE_STALE_DAYS`, and says plainly that it is not a quote. `meble pack` was
deleted from this project because a local number that looked authoritative invited confident decisions
that turned out wrong — a hard-coded price is the same trap. A price without `checked:` is a test
failure.

## Panel (`cabinet.panels[]`) — SOURCE OF TRUTH
```yaml
- id: side-l               # unique within the cabinet; referenced by fittings
  name: "Left side"
  element_type: panel      # panel (carcass, default) | front | countertop  (latter two added later)
  role: side               # optional label: side | top | bottom | shelf | back | divider | ...
  material: w1100-18        # ref; defaults to cabinet.defaults.material
  width: 560               # X
  height: 720              # Y
  thickness: 18            # optional; defaults to material.thickness
  quantity: 1
  grain: height            # any | width | height  (default = force orientation; see meblepl-editor.md)
  edge_banding:
    all_edges: false       # if true, band all 4 with `band` (below) / default band
    band: eb-w1100-1        # single band when all_edges or no per-edge override
    edges: { 2: eb-w1100-1 }# per-edge: key 1=top 2=right 3=bottom 4=left; value = band id (or true)
    glue_type: long        # long ("kryjące długie", default) | short
  holes: []                # see Hole; explicit; stamped holes carry `src`
  grooving: []             # reserved; structures must not reshape when this is filled in later
  placement:               # optional, FOR VIZ ONLY (not order-relevant)
    pos: [0, 0, 0]         # min-corner in cabinet local frame (x=width, y=depth, z=height)
    rot: [0, 0, 0]         # Euler degrees; local panel frame W->X H->Y thickness->Z
    step: [0, 0, 424]      # optional: draw all `quantity` copies, each offset by this from the last
                           # (e.g. identical shelves on a pitch). Count comes from `quantity`, so the
                           # two can't disagree; omit `step` and only ONE box is drawn.
```

### Hole (`panel.holes[]`)
Two shapes by `face`:
```yaml
# EDGE hole (edge drilling): face = edge1|edge2|edge3|edge4
- { face: edge3, from: 50, dia: 4, depth: 35, type: single, src: cf-1 }
- { face: edge2, from: 100, dia: 8, depth: 13, type: multi, count: 5, spacing: 32 }
# SURFACE hole (surface drilling): face = outer|inner  (see docs/conventions.md)
- { face: inner, x: 37, y: 100, dia: 5, depth: 13, type: single }
- { face: outer, x: 37, y: 100, dia: 8, depth: through, type: multi, count: 4, spacing: 32, direction: y }
```
- `face` (surface): **`outer`** (visible outside) or **`inner`** (toward cavity); picks the drill side
  only — x,y stay in the one panel frame (editor: outer → przód, inner → tył).
- `from` (edge holes): distance from 0 — left for top/bottom (1,3), bottom for left/right (2,4).
- `x,y` (surface holes): from bottom-left.
- `dia`: edge = 4|8; surface = 3|5|8|10|15|20|35.
- `depth`: edge = 2–35; surface = 2–15 or `through`.
- `type`: `single` | `multi`. multi edge → +`count`,+`spacing`; multi surface → +`count`,+`spacing`,
  +`direction` (`x`|`y`).
- `src`: **the fitting this hole belongs to.** For a `drilling: stamped` fitting that means `meble fit`
  computed it and owns it; for `drilling: manual` (hinge plates, shelf pins) the hole is hand-derived
  and the tag is just the audit trail the buy list and `review` read. Either way `fit` only ever
  replaces holes belonging to a fitting it actually re-stamped, so a hand-written hole is never lost —
  and a hole with no `src` at all is never touched by anything.

## Cabinet (`cabinets/<c>.yaml`)
```yaml
id: open-900
name: "Kitchen open unit 900"
kind: custom               # custom | readymade
category: base             # base | wall | tall | wardrobe
construction: confirmat    # default joinery hint
dimensions: { width: 900, height: 400, depth: 600 }   # envelope (layout/grouping/viz)
position: { x: 0, y: 0, z: 0, rotation: 0 }           # placement within the set/room
defaults: { material: w1100-18, edgeband: eb-w1100-1 }
back: { type: surface }    # surface | rebate | groove
plinth: { height: 100 }
panels: [ ... ]            # source of truth
assembly:
  fittings: [ ... ]        # see Fitting
parts:
  - { ref: drawer-box-500x400, quantity: 2, placement: { pos: [...], rot: [...] } }
```

`kind: readymade` cabinet: omit `panels`/`assembly`; add `system`, `nominal_size`, actual `dimensions`,
optional `model_ref`, `catalog` (see `ikea-metod-pax-reference.md`).

### Fitting (`cabinet.assembly.fittings[]`)
References panels; **applying** it (`meble fit`) stamps holes onto them. Confirmat/dowel shape:
```yaml
- id: cf-bl                # unique within the cabinet; becomes the holes' `src`
  hardware: confirmat-7x50 # ref; the drill pattern lives there
  through: side-l          # panel the screw passes through -> gets the FACE/surface hole
  into: bottom             # panel whose EDGE receives the screw
  seam: { through_edge: 3, into_edge: 4 }  # edge of each panel that forms the joint line
  at: [50, 282, 510]       # positions along the seam (from 0)
```
Hinge/slide fittings (added with fronts) follow the same pattern with type-specific keys; stamping for
those is implemented when fronts arrive.

## Part (`library/parts/<p>.yaml`)
A reusable sub-assembly = a mini cabinet. Same shape as a custom cabinet (`panels` + `assembly`), plus
`id`, `name`, `type`. Referenced by `cabinet.parts[]`; its panels flow into the panel list ×quantity.

## Set (`sets/<s>/set.yaml`)
```yaml
id: kitchen
name: "Kitchen"
room: kitchen
cabinets: [open-900, ...]  # cabinet ids in this set's cabinets/ dir
layout: {}                 # optional notes about relative placement (positions also live on cabinets)
```

## Apartment (`apartments/<a>/apartment.yaml`)
```yaml
id: bohaterow
name: "Mieszkanie Bohaterów"
rooms: [kitchen, bathroom, bedroom, hall]
sets: [kitchen]            # set ids present under sets/
```

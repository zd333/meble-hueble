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
- `src`: id of the fitting that stamped this hole (absent = manual). `meble fit` only ever replaces holes
  with a matching `src`; manual holes are never touched.

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

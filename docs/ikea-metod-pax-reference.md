# IKEA METOD & PAX — Dimensional / Technical Reference

> Scope: data needed to (a) place ready-made IKEA METOD (kitchen) and PAX (wardrobe) units in a layout
> next to custom MFC cabinets and (b) render them in 3D. EU/metric (the US "SEKTION" line differs and is
> NOT covered). Verified against IKEA product pages + the official METOD installation guide. Items
> marked ⚠️ are uncertain or vary by market/finish — verify per project.

## CRITICAL: nominal vs. actual (read first)

IKEA names cabinets by a **nominal/system size** = the module grid pitch, not always the physical
carcass. Store **both** a `nominal_size` (for the grid/ordering) and **actual** `dimensions` (for layout
collision + render). Size fillers off **actual + reveal**, never nominal.

- **METOD width** — nominal == actual. "60 cm" frame = **600 mm**.
- **METOD depth** — "60 cm" base = **590 carcass / 600 with suspension rail**; "37 cm" = **366 / 376**.
- **METOD height** — nominal == carcass height (40/60/80/100/140/200/220 cm). Legs/plinth added on top.
- **PAX width** — actual ~**2 mm narrower** per module: "100 cm" = **998 mm** (three = ~2994, not 3000);
  "75" ≈ 748 ⚠️; "50" ≈ 498 ⚠️.
- **PAX height** — "236 cm" = **2364 mm**; "201 cm" ≈ 2012 ⚠️.  **PAX depth** — "58" = 580; "35" = 350 ⚠️.

## 1. METOD (kitchen)

- **Carcass:** 18 mm melamine particleboard; assembled with **dowels + cam locks + screws**; interior
  **System-32** holes (Ø5, 32 mm pitch), notably a **dual row** per side (vs PAX/BILLY single row).
  First row ~37 mm from front ⚠️.
- **Base:** heights **80** (std), 40; widths **20/30/40/60/80**; depths **60** (590/600) and **37**
  (366/376). Legs **80 mm** std (110 mm alt ⚠️), height-adjustable; plinth clips to legs, recessed
  (~50 mm ⚠️). Finished worktop ~90 cm.
- **Wall:** heights **40/60/80/100/140**; widths 20–80; depth **37** (some 60).
- **High/tall:** heights **200/220**; widths 40/60(/80 ⚠️); depths 60/37.
- **Suspension rail:** base-rail underside **82 cm above floor**; standard kitchen stacks **208 / 228 /
  248 cm** with **120 / 140 / 160 cm** gaps to the wall-cabinet rail.
- **Fillers:** IKEA uses scribed filler pieces (≥25–35 mm) between cabinets/walls — this is the seam where
  a custom MFC filler meets a METOD run.
- **Fronts:** full-overlay/frameless, ~**3 mm reveal** between fronts ⚠️; front ≈ pitch − reveal; model
  as a separate slab ~18–20 mm thick offset in front of the carcass.
- **Hinges:** standard **35 mm-cup euro hinges** (UTRUSTA), 110°/153°, soft-close. Drawers (MAXIMERA)
  use the carcass's pre-drilled rows (outer = standard, inner = inner drawers).

## 2. PAX (wardrobe)

- **Frame:** melamine particleboard ~18 mm ⚠️; dowels + cam locks; adjustable feet; interior **System-32
  single column** (Ø5, 32 mm pitch).
- **Sizes:** widths **50/75/100** (998 actual for 100); heights **201/236** (2364 for 236); depths
  **35/58** (580 for 58). Need **237 cm** ceiling to raise a 236 frame upright (240 cm for sliding doors).
  KOMPLEMENT interiors are 35 cm deep.
- **Doors:** hinged **195** (201 frame, 3 hinges) / **229 cm** (236 frame, 4 hinges), widths 50/75,
  reversible, swing out (leave ≈door-width clearance). Sliding doors sold **in pairs by total run width**
  (150/200 cm), front projection ~5–6 cm ⚠️, no side clearance.

## 3. Fields to capture for a readymade unit (`kind: readymade`)

```yaml
kind: readymade
system: metod | pax
nominal_size: "60x60x80"        # the order/grid code
dimensions: { width, depth, height }   # ACTUAL mm — for layout + render
position: { x, y, z, rotation }
model_ref: library/units/models/<file>.glb   # optional 3D model; else rendered as a box
catalog: { article: "..." }     # optional SKU
# optional: depth_with_rail, leg_height, plinth_height, rail_height_from_floor,
#           front: { type, reveal, thickness, hinge_side, opening_angle, swing_clearance }
```

Filler rule: leftover filler = opening − Σ(actual widths) − reveals. METOD actual == nominal (slack only
at run ends + wall out-of-square). PAX accumulates ~2 mm/module shortfall.

## Confidence

**High (verified):** 18 mm METOD panel; dowel+cam construction; System-32; METOD base 60 = 590/600,
37 = 366/376; 82 cm base-rail; 208/228/248 stacks; legs/plinth 8 cm (11 alt); UTRUSTA 35 mm 110/153;
PAX 100 = 998/2364/580; heights 201/236; depths 35/58; hinged doors 195/229 (3/4 hinges); sliding doors
in pairs 150/200; KOMPLEMENT 35 deep; PAX single-column holes.
**⚠️ Verify before ordering:** exact 3 mm METOD reveal; front thickness per range; METOD dual-row hole +
cam/dowel coordinates; PAX 50/75 actual widths and 201 actual height; 11 cm leg availability; plinth
recess depth; sliding-door projection.

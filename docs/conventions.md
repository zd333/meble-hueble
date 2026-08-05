# Orientation & face conventions

The single source of confusion in cabinet design is "which face / which edge / which way round." This
nails it down so the YAML, the PDF, and the editor all agree. The `meble review` linter and the
`cabinet-review` skill enforce the rules here.

## Coordinate frame (one frame per panel)

- All lengths in **mm**. Each panel is a `width × height` rectangle, **origin bottom-left**: width → X
  (right), height → Y (up).
- **Edges: 1 = top, 2 = right, 3 = bottom, 4 = left.**
- Edge-hole `from` = distance from 0 along that edge: from the **left** for top/bottom (1, 3), from the
  **bottom** for left/right (2, 4).
- Surface-hole `x, y` = from the bottom-left corner.

## Faces: `outer` / `inner` (not front/back)

A board has two faces. We name them by physical position, never "front/back" (which collides with the
cabinet's front *direction*):

- **`outer`** = the face on the outside of the box / the visible face.
- **`inner`** = the face toward the cavity (where shelf pins, hinge plates, slide screws live).

**Key rule — one frame, face = drill side only.** `x, y` are in the *single* panel frame above; `outer`
/`inner` only says **which face the drill enters**. Coordinates are **not** mirrored between faces. A
hole at `(x:37, y:100, face:inner)` and `(x:37, y:100, face:outer)` are the *same point on the panel*,
drilled from opposite sides. (This matches the meble.pl editor: you pick przód/tył, but x,y stay in the
one panel frame.)

**Editor mapping:** `outer` → enter as **przód (front)**, `inner` → **tył (back)**. The PDF prints this
on every panel page.

Typical placement: confirmat **heads → outer** (visible); shelf-pin / System-32 / hinge-plate holes →
**inner**. Putting a blind Ø5 on `outer` (visible) or a confirmat through-head on `inner` is almost
always a mistake (the linter flags it).

## Per-role orientation (which local edge faces the cabinet front)

| role            | outer face points | cabinet FRONT edge | notes |
|-----------------|-------------------|--------------------|-------|
| `side-left`     | left              | **2 (right)**      | mirror of side-right |
| `side-right`    | right             | **4 (left)**       | mirror of side-left |
| `bottom`        | down              | **1 (top)**        | width = internal (W−2t), height = depth |
| `top`           | **down**          | **1 (top)**        | see the note below — `inner` is its UP face |
| `shelf`         | (symmetric)       | **1 (top)**        | faces equivalent; use `inner` as reference |
| `back`          | toward wall       | —                  | usually unbanded; ~3 mm HDF |
| `divider` / other | —               | —                  | declare explicitly |

So a `side-left` is entered with its **outer (left-facing) face**, cabinet front on the **right (edge 2)**,
cabinet top at the top (edge 1). The `side-right` is its **mirror**: outer faces right, cabinet front on
the **left (edge 4)**.

### Horizontals: which face is up

For a horizontal panel (`top` / `bottom` / `shelf` / `divider`) the frame is pinned by its joinery:
**edge 4 is the cabinet LEFT, edge 2 the RIGHT, edge 1 the FRONT** (a left-side fitting joins into the
horizontal's edge 4 — see `d60-base`). With the panel frame being right-handed and read from the outer
face, those two facts **force the outer face to point DOWN** on *every* horizontal. So:

- `bottom`: `outer` = down, `inner` = up (toward the cavity) — as you'd expect.
- **`top`: `outer` = down (toward the cavity), `inner` = UP.** Counter-intuitive, but it is the same
  frame; a top panel is not mirrored relative to a bottom panel. To bore a cam or a pin hole into the
  **underside** of a top panel, use **`outer`**.
- `shelf`: both faces are in the cavity, so it only matters for keeping a hole set self-consistent.

Most horizontals are symmetric about their vertical axis, so the physical part can be flipped at
assembly time and still fit — but the **face you name here is the face the supplier drills**, so name the
one you actually want machined.

## Left & right sides are MIRROR parts

They are **not** the same part. At minimum the **front-edge banding is on a mirrored edge** (2 on the
left, 4 on the right). If the cabinet is asymmetric front-to-back (a hinge on one edge, offset holes),
the hole positions mirror too. Entering two *identical* sides is the classic error that wastes a sheet —
`meble review` flags it (`mirror-pair`). In a *symmetric* cabinet the hole sets happen to be identical
and only the banding edge differs (as in the `d60-base` example).

## Edge cases

- **Shelf / drawer bottom** — both faces face the cavity; the two faces are equivalent. Pick `inner` as
  the reference; usually no surface holes anyway.
- **Back (HDF)** — `outer` = toward the wall. Surface-mounted, unbanded, ~3 mm.
- **Fronts / doors (later)** — `outer` = the room-facing decorative face; hinge cups go on `inner`.

## Why this is safe

These rules are checked two ways: `meble review` (deterministic linter) catches the mechanical ones
(carcass arithmetic, mirror mismatch, wrong face, breakthrough, unbanded front edge); the
`cabinet-review` skill adds an independent expert pass for judgement-level issues and accumulates new
pitfalls as we hit them.

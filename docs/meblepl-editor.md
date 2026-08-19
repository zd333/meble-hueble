# centrum.meble.pl editor — panel model & CSV format

How the online order editor works, the per-panel fields we must reproduce, and the PRO100 CSV import
format. Source: user's description of the live editor + the two provided PRO100 example files.

## Order structure

- The order has one or more **boards** ("płyty / MFC"): a **model** (vendor + decor + texture code) and
  a **thickness**. Board sheet dimensions don't matter to us — the supplier's engine generates the
  cutting layout (`rozkrój`). **We never compute the cutting layout.**
- Under each board you add multiple **cabinet panels** ("formatki").
- Product categories: **cabinet panels**, **fronts**, **countertops**. We model **panels** first;
  fronts/countertops are separate products added later (see `element_type` in `schema.md`).
- State lives on the backend; there is **no full export**. Banding/drilling/grooving are entered by hand.
  The editor **does** accept a CSV import — but for panel **dimensions only**.

## Per-panel fields (what the PDF spec sheet must mirror, in entry order)

1. **Name** (free text; does not affect the cut).
2. **Size**: width + height. This is the **FINISHED size — the edge band is included, not added on top**
   (confirmed against the live editor). Enter our YAML dimensions verbatim; never subtract the band
   thickness on a banded axis. **No grain-direction / rotation option** — panels keep their orientation
   (width is always width). The cutting engine does not rotate them.
3. **Quantity**.
4. **Edge banding:**
   - "Band all edges" checkbox. If off, choose edges by number: **1 = top, 2 = right, 3 = bottom,
     4 = left**.
   - "Use different edge bands" checkbox. If on, a band per edge; if off, one band for the panel.
   - Band details: thickness **1 mm or 2 mm**; band **model code** (vendor + decor + texture).
   - **"Rodzaj klejenia"** radio — **"kryjące długie"** (default) or **"kryjące krótkie"**: which edges'
     band is the *covering* one at the corners (matters mostly for 2 mm band, to hide joints). Default
     "długie" = the long edges' band covers.
5. **Drilling** — two independent groups, in this order on screen (the PDF sheet matches it):
   - **Surface drilling** (per hole): surface **back | front** (we model these as **inner | outer** — see
     `conventions.md`: outer → front/przód, inner → back/tył); **x, y** (from **left, bottom**); bore Ø
     **3 / 5 / 8 / 10 / 15 / 20 / 35 mm**; depth **2–15 mm** (1 mm step) **or drill-through**; type
     **single | multi**; if multi → number of holes + distance + direction (**X or Y axis**).
   - **Edge drilling** (per hole): edge number (1–4); distance from 0 (always from **left/bottom**);
     bore Ø **4 or 8 mm**; depth **2–35 mm** (1 mm step); type **single | multi**; if multi → number of
     holes + distance between them.

   Each group numbers its own rows from 1, which is why the PDF restarts numbering per section.

   **Prefer `multi` for regular series — but only up to 140 mm apart.** A `multi` hole is a *single
   editor entry* that produces a whole evenly-spaced row/column (shelf-pin columns, System-32 rows,
   repeated confirmats), so it cuts manual entry sharply.

   /!\ **THE SURFACE FORM REJECTS A `multi` WHOSE SPACING EXCEEDS 140 mm** (measured 2026-08-19).
   **EDGE drilling has no such limit** — retested the same day, after the rule was briefly applied to
   both groups on an assumption that turned out wrong. Keep the run as one `multi` in the YAML either
   way — that is the design intent, and the drilling is identical —
   `tools/meble/normalize.py: expand_wide_multis` splits only the surface ones on the PDF. Today that
   is +69 rows to type; edge runs stay as one entry however far apart they are.
6. **Grooving** — out of scope for now; reserved (`grooving: []`). Adding it later must not reshape
   existing structures.

## Coordinate conventions (mirrored in our YAML)

- Origin **bottom-left**; width → X, height → Y.
- Edges: **1 top, 2 right, 3 bottom, 4 left**.
- Edge-hole "distance from 0": from **left** for top/bottom edges (1, 3); from **bottom** for left/right
  edges (2, 4).
- Surface holes: **x** from left, **y** from bottom; face = **outer**/**inner** (editor: front/back).

## PRO100 CSV import format (dimensions only)

Semicolon-separated; one panel per row; UTF-8 (Polish characters); a trailing `;` after the last column.
Header (from `example.csv`):

```
Nazwa (nie wpływa na rozkrój);Szerokość;Oklejanie szerokości;Wysokość;Oklejanie wysokość;Grubość płyty;Ilość sztuk;Słoje [0 = bez znaczenia / 1 = po drugim wymiarze (po wysokości) / 2 lub puste = po pierwszym wymiarze (po szerokości)];
```

| # | Column | Meaning | Our mapping |
|---|--------|---------|-------------|
| 1 | Nazwa | name (does not affect cut) | `panel.name` |
| 2 | Szerokość | width (mm) | `panel.width` |
| 3 | Oklejanie szerokości | banding of the **width** edges = top(1)+bottom(3) | derived from `edge_banding` |
| 4 | Wysokość | height (mm) | `panel.height` |
| 5 | Oklejanie wysokość | banding of the **height** edges = right(2)+left(4) | derived from `edge_banding` |
| 6 | Grubość płyty | thickness (e.g. `18.00`) | from `material.thickness` |
| 7 | Ilość sztuk | quantity (blank = 1) | `panel.quantity` |
| 8 | Słoje | grain: `0`=any / `1`=along height / `2`/blank=along width | from `panel.grain` |

**Banding marks** (cols 3 & 5) carry a **count, never an identity**:
- `=` → both edges of that axis banded
- any other non-empty value → **exactly one** edge banded
- *(blank)* → none

### /!\ A single band always lands on edge 3 / edge 4 — you cannot choose

Measured against the live editor **2026-08-17** with a 12-row probe (one token per row, panels
otherwise identical). `-`, `_`, `1`, `3`, `13` in col 3 and `-`, `|`, `2`, `4` in col 5 all behaved
**identically**: col 3 banded **edge 3** (bottom), col 5 banded **edge 4** (left). The `=` control
banded 1+3 and 2+4 correctly. meble.pl's own `meblepl_przykladowy_rozkroj.csv` only ever uses `=`
and `-`, which is consistent with a count.

So the format is **provably lossy**: 2 columns × 3 states = 9 patterns against 16 real ones.
**"Band edge 1 only" and "band edge 3 only" are the same CSV cell**, and the importer resolves it to
edge 3. Same for 2 vs 4 → edge 4. This is not a bug in our export and no token works around it.

### The fix: export-time rotation (`tools/meble/normalize.py`)

A **180° in-plane rotation** maps 1↔3 and 2↔4, so an edge-1 band becomes an edge-3 band and the CSV
can express it. Width, height, grain direction and the `outer`/`inner` faces are all preserved — it
is a **rotation, not a mirror**. (A mirror would also move the band to edge 3, and would swap the
faces, putting every hole on the wrong side of the board. That distinction is the whole ballgame.)
The panel delivered is physically identical, just described from the opposite corner.

`normalize()` rotates a panel **only when it strictly helps**, so panels that were already
expressible are untouched. Both the CSV **and** the PDF apply it, and they must stay in step: the
CSV creates the panel and the PDF is what gets typed into it, so if only one rotated the banding
would sit at one end and the drilling at the other. Rotated PDF pages carry a banner saying so.

It runs at **export time, never in the YAML**: most holes on the affected panels are `fit`-stamped,
and `meble fit` re-derives them in the canonical frame, so a rotation stored in YAML would be
silently undone on the next run. The 3D viewer deliberately does not normalise — the rotation is a
relabel, so the assembled cabinet renders identically, and nothing is typed from the viewer.

**The CSV bytes do not change.** A `-` is a `-` whichever end the band is on. What changes is that
the band the importer *will* apply becomes the one the design wants, and the PDF's drilling moves to
match. Ordered dimensions, quantities and grain are untouched.

A panel whose two axes want opposite ends (edge 1 with edge 4) cannot be fixed by any rotation.
None exist today; if one appears, the CSV emits blank for that axis and appends
`/!\ TICK EDGE n BY HAND` to the **Nazwa** column — the only channel that reaches the editor UI —
and `meble csv` prints the list. A *missing* band is one click to add; a band on the *wrong* edge is
a finished panel that is scrap.

The editor's **edge numbering matches ours exactly** (1 top, 2 right, 3 bottom, 4 left) — its
per-panel diagram is labelled, and the probe confirms it. **Drilling entered by hand from the PDF
needs no remapping.**

**Grain (`Słoje`):** `0` = doesn't matter (optimizer may orient); `1` = grain along the **height**;
`2` or blank = grain along the **width** (first dimension). Our default **forces orientation** so panels
are never rotated → emit `2` unless the panel says otherwise (`grain: height` → `1`, `grain: any` → `0`).

Notes:
- The import carries **dimensions, quantity, grain, and the coarse per-axis banding marks** only. The
  band **model and thickness**, the drilling, and grooving are entered **manually** — that's what the
  PDF spec sheet is for. Note the band thickness in particular: the CSV says nothing about it and the
  editor defaults to **0.8 mm**, while this project uses 1 mm on carcasses and **2 mm on every visible
  front**. The PDF prints the model and thickness per panel for exactly that check.
- One CSV **per board** (the editor groups panels under a board model).
- Example files: `example.csv` (header + 2 rows) and `meblepl_przykladowy_rozkroj.csv` (a real list).

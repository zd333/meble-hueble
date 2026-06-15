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
2. **Size**: width + height. **No grain-direction / rotation option** — panels keep their orientation
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
5. **Drilling** — two independent groups:
   - **Edge drilling** (per hole): edge number (1–4); distance from 0 (always from **left/bottom**);
     bore Ø **4 or 8 mm**; depth **2–35 mm** (1 mm step); type **single | multi**; if multi → number of
     holes + distance between them.
   - **Surface drilling** (per hole): surface **back | front** (we model these as **inner | outer** — see
     `conventions.md`: outer → front/przód, inner → back/tył); **x, y** (from **left, bottom**); bore Ø
     **3 / 5 / 8 / 10 / 15 / 20 / 35 mm**; depth **2–15 mm** (1 mm step) **or drill-through**; type
     **single | multi**; if multi → number of holes + distance + direction (**X or Y axis**).

   **Prefer `multi` for regular series.** A `multi` hole is a *single editor entry* that produces a whole
   evenly-spaced row/column (shelf-pin columns, System-32 rows, repeated confirmats). Using it instead of
   N `single` holes drastically cuts manual entry and can be cheaper. Always collapse an evenly-spaced run
   into one `multi`; only use `single` for irregular positions.
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

**Banding marks** (cols 3 & 5), per the PRO100 0/1/2 convention shown as symbols:
- `=` → both edges of that axis banded (2)
- `-` → one edge banded (1)
- *(blank)* → none (0)

**Grain (`Słoje`):** `0` = doesn't matter (optimizer may orient); `1` = grain along the **height**;
`2` or blank = grain along the **width** (first dimension). Our default **forces orientation** so panels
are never rotated → emit `2` unless the panel says otherwise (`grain: height` → `1`, `grain: any` → `0`).

Notes:
- The import carries **dimensions, quantity, grain, and the coarse per-axis banding marks** only. The
  rich per-edge banding, the band model, drilling, and grooving are entered **manually** — that's what
  the PDF spec sheet is for.
- One CSV **per board** (the editor groups panels under a board model).
- Example files: `example.csv` (header + 2 rows) and `meblepl_przykladowy_rozkroj.csv` (a real list).

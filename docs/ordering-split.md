# Splitting the meble.pl order across whole boards

meble.pl charges for **whole boards**, and **one order carries one board format**. So the panel list has
to be split by decor *and* by sheet size, and the split should leave every sheet comfortably under 100 %
so their nesting optimiser has room.

Two stock sizes are offered:

| sheet | area |
|---|---|
| 2070 × 2800 ("big") | 5.80 m² |
| 2070 × 1032 ("small") | 2.14 m² |

## The decision: which optional panels go on the white board

Several panels are hidden or deliberately-white, so their decor is a free choice. Moving them between
U604 and W980 changes how each decor rounds up to whole sheets. Three options were costed
(conservative shelf packing, 5 mm kerf, 10 mm trim per sheet):

| | U604 | W980 | purchased | used |
|---|---|---|---|---|
| everything optional stays U604 | 3 big + 2 small | 2 small | 25.93 m² | 72 % |
| **only the never-seen panels → white** | **3 big + 1 small** | **2 small** | **23.80 m²** | **78 %** |
| + white drawer/carcass interiors | 3 big + 1 small | 1 big + 1 small | 27.46 m² | 68 % |

**The middle row is what this repo implements.** Note the third row is *worse* than the second: pushing
more onto the white board just moves the waste across, and it costs a big sheet. More is not better.

Only three panel entries (4 boards, 0.90 m²) carry `material: w980-18` for this reason:

| panel | size | why the decor does not matter |
|---|---|---|
| `wc-column` / `cover-spacer` | 550 × 1191 | sealed inside the lower box, never seen |
| `wm-wardrobe` / `rail-lower` | 726 × 200 | behind the washing machine |
| `sink-vanity` / `rail-back` ×2 | 524 × 100 | behind the drawers, against the wall |

That is exactly enough to drop U604 below the threshold for a second small sheet, while W980 absorbs
them without needing another sheet of its own (it goes from 46 % to 68 % full — dead area you were
paying for anyway).

## The three orders

Every panel `name` carries its order marker, so it shows on the PDF sheet, in the PDF index and in the
CSV's free-text `Nazwa` column (which does not affect nesting).

| order | decor | sheets | boards | panel area | fill |
|---|---|---|---|---|---|
| 1 | U604 | 3 × 2070×2800 | 33 | 14.15 m² | 81 % |
| 2 | U604 | 1 × 2070×1032 | 12 | 1.61 m² | 75 % |
| 3 | W980 | 2 × 2070×1032 | 14 | 2.89 m² | 68 % |

**Order 2 contents** (everything else U604 is order 1):

- `sink-vanity` — bottom panel, top drawer facade, and all four drawer side panels
- `wc-column` — right-compartment shelves ×2
- `wm-wardrobe` — right-compartment shelves ×4

The split falls on whole panel entries, so no CSV line is cut in half.

Ready-to-import files are written by `meble csv` plus a filter on the marker:
`out/csv/order1-u604-2070x2800.csv`, `order2-u604-2070x1032.csv`, `order3-w980-2070x1032.csv`.

## Why order 1 is safe at 81 %

The 33 boards of order 1 were packed onto 3 big sheets by a plain **shelf (first-fit-decreasing-height)**
packer with a 5 mm kerf on every panel and 10 mm trimmed off each sheet. A shelf packer is strictly worse
than a real nesting optimiser, so a list that fits here will fit at meble.pl with room to spare.

## Re-deriving this after a design change

**The markers are a snapshot.** Change any panel dimension, add a panel, or move one between decors and
the split is stale — the names will still claim an order that no longer balances. Re-run the analysis
before ordering:

1. Recompute the per-decor totals (`meble csv --apartment bohaterow` gives the panel list).
2. Re-pack: fill 3 big sheets, and whatever is left is order 2. Confirm it fits one small sheet.
3. Update the `[order N · …]` suffix on every affected panel `name`.

If the totals shift much, re-cost the three options above — the best split moves with the design.

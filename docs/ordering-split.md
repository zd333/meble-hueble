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
U604 and W1100 changes how each decor rounds up to whole sheets. Three options were costed
(conservative shelf packing, 5 mm kerf, 10 mm trim per sheet):

| | U604 | W1100 | purchased | used |
|---|---|---|---|---|
| everything optional stays U604 | 3 big + 1 small | 2 small | 23.80 m² | 68 % |
| **only the never-seen panels → white** | **3 big + 1 small** | **2 small** | **23.80 m²** | **68 %** |
| + white drawer/carcass interiors | 3 big + 1 small | 3 small | 25.93 m² | 62 % |

**The middle row is what this repo implements**, but note what changed when `wm-wardrobe` was redesigned
for a stacked washer + dryer: the first two rows now **buy exactly the same sheets**. The white-board
swap no longer saves a sheet, because the redesign deleted a centre gable and seven shelves and took
~2.5 m² of panel out of U604 on its own. It is kept anyway, for margin rather than for cost — it holds
0.76 m² off the U604 sheets, which are the tight ones, and puts it on white sheets that would otherwise
sit at 46 % (they go to 64 % — dead area you were paying for anyway).

The third row is still *worse*: pushing more onto the white board just moves the waste across, and it
costs a third small sheet. More is not better.

Only two panel entries (3 boards, 0.76 m²) carry `material: w1100-18` for this reason:

| panel | size | why the decor does not matter |
|---|---|---|
| `wc-column` / `cover-spacer` | 550 × 1191 | sealed inside the lower box, never seen |
| `sink-vanity` / `rail-back` ×2 | 524 × 100 | behind the drawers, against the wall |

`wm-wardrobe` / `rail-lower` used to be the third. It no longer exists: the redesign grew that 726 × 200
brace rail into a full-height 726 × 2470 back, which **is** seen — through the 63 mm gap at each side of
the stack, above the dryer, and as the back wall of the overhead cabinet whenever a door is open. It
stays `u604-18`. Do not move it to the white board to balance a future split; pick a genuinely hidden
panel instead.

## The three orders

Every panel `name` carries its order marker, so it shows on the PDF sheet, in the PDF index and in the
CSV's free-text `Nazwa` column (which does not affect nesting).

| order | decor | sheets | boards | panel area | fill |
|---|---|---|---|---|---|
| 1 | U604 | 3 × 2070×2800 | 34 | 11.78 m² | 84 / 63 / 58 % |
| 2 | U604 | 1 × 2070×1032 | 3 | 1.63 m² | 78 % |
| 3 | W1100 | 2 × 2070×1032 | 13 | 2.74 m² | 70 / 61 % |

**Order 2 contents** (everything else U604 is order 1):

- `wc-column` — back panel (700 × 1315) and centre gable (181 × 1297)
- `wm-wardrobe` — divider (726 × 657)

The split falls on whole panel entries, so no CSV line is cut in half.

Order 2 is only three boards now. It exists because the U604 list does not fit 3 big sheets under the
conservative packer below — six shelf-packing heuristics were tried and the best still spilled two
panels — and one small sheet is much cheaper than a fourth big one (2.14 m² against 5.80 m²). Those
three panels are simply the ones that fill a small sheet most usefully; the choice is free, so if
meble.pl would rather cut something else, any set of whole entries around 1.6 m² works.

Ready-to-import files are written by `meble csv` plus a filter on the marker:
`out/csv/order1-u604-2070x2800.csv`, `order2-u604-2070x1032.csv`, `order3-w1100-2070x1032.csv`.

## Why order 1 is safe at 84 %

The 34 boards of order 1 were packed onto 3 big sheets by a plain **shelf (first-fit-decreasing-height)**
packer with a 5 mm kerf on every panel and 10 mm trimmed off each sheet, with grain-locked panels held
to the sheet's grain axis and `grain: any` panels free to rotate. A shelf packer is strictly worse than
a real nesting optimiser, so a list that fits here will fit at meble.pl with room to spare.

Only the first sheet is tight; the other two land at 63 % and 58 %, because the three full-height panels
(two 2520 sides and the 2470 back) each claim most of a sheet's length and leave offcuts nothing else
is tall enough to use.

## Re-deriving this after a design change

**The markers are a snapshot.** Change any panel dimension, add a panel, or move one between decors and
the split is stale — the names will still claim an order that no longer balances. Re-run the analysis
before ordering:

1. Recompute the per-decor totals (`meble csv --apartment bohaterow` gives the panel list).
2. Re-pack: fill 3 big sheets, and whatever is left is order 2. Confirm it fits one small sheet.
3. Update the `[order N · …]` suffix on every affected panel `name`.

If the totals shift much, re-cost the three options above — the best split moves with the design.

**Last re-derived** after the `wm-wardrobe` stacked washer + dryer redesign was merged (2026-08-10).
That change is the worked example of why this section exists: it removed the centre gable, collapsed
eight shelves to one, and turned the brace rail into a full-height back. Sheet counts came out
unchanged — still 3 big + 1 small U604 and 2 small W1100, 23.80 m² purchased — but the *contents* of
every order moved, one of the three white-board panels stopped being optional, and utilisation fell
from 78 % to 68 % because the sheets you buy round up the same way over a smaller panel list.

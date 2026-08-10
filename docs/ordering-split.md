# Splitting the meble.pl order across whole sheets

meble.pl charges for **whole sheets**, and **one order carries one sheet format**. So the panel list
has to be split by decor *and* by format, and the split should leave every sheet comfortably under
100 % so their nesting optimiser has room.

**This is computed, not maintained by hand.** Run:

```bash
task pack                                             # or:
python -m meble pack --apartment bohaterow --balance   # recommend
python -m meble pack --apartment bohaterow --stamp     # write the markers into panel names
```

Sheet formats and the kerf/trim allowances are data — `library/materials.yaml`, `sheets:` and
`packing:`. This document records the *reasoning* behind the current answer; the numbers themselves
come from the tool.

## The two formats

| sheet | size | area |
|---|---|---|
| `full` | 2800 × 2070 | 5.80 m² |
| `half` | 2800 × 1032 | 2.89 m² |

**Both are 2800 long.** The half is the full sheet ripped down its length (1032 = 2070/2 less the saw
kerf), so it is *narrower, not shorter* — a 2520 mm gable or the 2470 mm wardrobe back fits a half
sheet perfectly well. This trips people up, and it once made this very document wrong: an earlier
revision recorded the half as 2070 × 1032, which silently barred every tall panel from it and cost a
sheet in the recommendation.

## The current split

| order | decor | sheets | boards | panel area | fill |
|---|---|---|---|---|---|
| 1 | U604 | 3 × full | 38 | 14.06 m² | 94 / 83 / 68 % |
| 2 | W1100 | 1 × half | 12 | 2.08 m² | 73 % |

Purchased **20.28 m²** for **16.15 m²** of panel — 80 % utilisation, in two orders.

Every panel `name` carries its `[order N · decor · sheet]` marker, so it shows on the PDF sheet, in
the PDF index and in the CSV's free-text `Nazwa` column (which does not affect nesting).

## The decision: which hidden panels go on which board

A panel that is genuinely never seen can be cut from either decor, and moving it changes how each
decor rounds up to whole sheets. Those panels declare `decor_optional:` and `pack --balance` tries
every combination.

Two panels qualify:

| panel | size | why the decor does not matter |
|---|---|---|
| `wc-column` / `cover-spacer` | 550 × 1191 | sealed inside the lower box, never seen |
| `sink-vanity` / `rail-back` ×2 | 524 × 100 | behind the drawers, against the wall |

**The answer is the opposite of what it used to be.** These panels were on the white board, to pull
U604 down under a sheet boundary. With the real formats that is backwards: W1100 is only 2.74 m² and
a half sheet holds 2.85, so moving `cover-spacer` (0.66 m²) **off** white is what drops W1100 from a
full sheet to a half — while U604 absorbs it inside the 3 full sheets it was buying anyway. That one
move is worth 2.90 m², a whole sheet, and `--balance` finds it in a second.

The general lesson: the useful move is whichever one gets a decor *under* a sheet boundary, and which
direction that is depends entirely on where the boundaries fall. Do not assume "hidden panels go on
the cheap board".

`wm-wardrobe` / `rail-lower` used to be a third entry. It no longer exists: the stacked washer + dryer
redesign grew that 726 × 200 brace rail into a full-height 726 × 2470 back, which **is** seen —
through the 63 mm gap at each side of the stack, above the dryer, and as the back wall of the overhead
cabinet whenever a door is open. It has no `decor_optional`, and must not be given one.

### What is deliberately NOT automated

Panels that are *visible but arguably could be white* — drawer box interiors, `wc-column`'s upper
back — are a **look** decision, not a free swap: a brighter interior in a deep cavity is a real
choice, and a cheaper carcass board is a real trade. Those never get `decor_optional`, so the packer
can never trade your interior finish away to save a sheet. Change them by hand if you want them.

## Why the recommendation can be trusted

`pack` uses plain **shelf (first-fit-decreasing-height)** packing — several sort heuristics, best
result kept — with a 5 mm kerf around every panel and 10 mm trimmed off each sheet. That is strictly
worse than a real nesting optimiser, which is the point: **a list that fits here fits at meble.pl with
room to spare.** It never under-reports a sheet.

It is a feasibility proof, not a cutting plan. Do not send its layout to anyone.

The sheet counts are searched exhaustively over small counts rather than by a greedy "fill the big
sheets first" rule, so the answer is optimal for this packer. Cost is `sheet.price` when
`materials.yaml` gives one and area otherwise; mixes within 1 % of each other are treated as the same
price and the tie goes to fewer sheets. **Add real prices** if a half ever costs more than half a
full — with area as the proxy, two halves look 0.3 % cheaper than one full, which is an artefact of
1032 × 2 being 6 mm shy of 2070 and not a purchasing fact.

## Re-deriving this after a design change

**The markers are a snapshot.** Change any panel dimension, add a panel, or move one between decors
and they are stale — the names will still claim an order that no longer balances.

1. `python -m meble pack --apartment bohaterow --balance` and read the recommendation.
2. If it moves a `decor_optional` panel, adopt it by editing that panel's `material:` **and its
   `edge_banding` band** to match, then re-run to confirm the answer is stable.
3. `python -m meble pack --apartment bohaterow --stamp` to write the markers.
4. Update the split table above if the shape of the answer changed.

**Last re-derived** 2026-08-10, after the `wm-wardrobe` stacked washer + dryer redesign was merged and
the sheet formats were corrected.

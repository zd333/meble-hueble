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
| 1 | U604 | 3 × full | 40 | 14.15 m² | 94 / 84 / 68 % |
| 2 | U899 | 1 × half | 10 | 1.98 m² | 69 % |

Purchased **20.28 m²** for **16.13 m²** of panel — 80 % utilisation, in two orders.

Every panel `name` carries its `[order N · decor · sheet]` marker, so it shows on the PDF sheet, in
the PDF index and in the CSV's free-text `Nazwa` column (which does not affect nesting).

**Order 1 is the bathroom, order 2 is the kitchen.** That is not a rule the packer enforces — it is
what the decors happen to be — but it is now true with no exceptions, which it was not before: the
kitchen used to share a white board with one bathroom panel.

## The white board is gone

Until 2026-08-12 the kitchen rode `w1100-18` Alpine White. The ready-made IKEA units turned out to be
the **METOD dark carcass** ("czarnoszary" — IKEA's near-black grey, NCS S 8500-N), so `open-900` and
`mounting-panels` moved to `u899-18` (Egger Czerń aksamitna U899 ST9, the same NCS), and W1100 stopped
being a board this project buys at all. `sink-vanity` / `rail-back`, which had been parked on white
purely to balance the decors, went home to the cabinet default.

**The swap was free.** Every variant, simulated against the packer:

```
                                   U604              U899                purchased
baseline (adopted)                 3×full            1×half               20.28 m²   ← optimal
+ wm-wardrobe/back      → U899     2×full + 1×half   1×full               20.28 m²   tie, rejected
+ wc-column/cover-spacer→ U899     3×full            1×full               23.18 m²   worse
+ both                  → U899     2×full + 1×half   1×full + 1×half      23.17 m²   worse
+ both + wc/back-upper  → U899     2×full + 1×half   1×full + 1×half      23.17 m²   worse
+ sink-vanity/rail-back → U899     3×full            1×half               20.28 m²   tie, pointless
```

Same sheet count, same order count, same order numbering (`u604-18` still sorts before `u899-18`).
Only **8 panel-name markers** changed: the 7 kitchen entries and `sink-vanity` / `rail-back`.

> ### ⚠ Derive this from the design you actually printed
>
> The first pass at this change was computed on `origin/main` (`ee4b652`) — but the printed PDF and
> CSVs came from `wardrobe-bay-and-banding` (`44bd87e`), which `main` did not yet contain. Three
> commits were missing: the appliance bay raised 1780 → 1810, the wardrobe doors 736 → 706 that follow
> from it, one shelf-pin height instead of three, and `open-900` banded all round instead of front-edge
> only. The material swap was redone on top of the merged design; the split is unchanged, but the
> banding and door heights would have been wrong in the order.
>
> **Before re-deriving, confirm the working tree is the tree you printed from.** `out/` is a symlink
> shared between worktrees, so an artifact sitting there is not evidence of which branch built it.
> The cheap check is to regenerate the CSV and diff it against the file you actually sent to meble.pl:
>
> ```bash
> git archive <commit> | tar -x -C /tmp/check && (cd /tmp/check && PYTHONPATH=tools python -m meble csv --apartment bohaterow)
> diff /tmp/check/out/csv/<board>.csv <the-csv-you-printed>.csv
> ```

## The decision: which hidden panels go on which board

A panel that is genuinely never seen can be cut from either decor, and moving it changes how each
decor rounds up to whole sheets. Those panels declare `decor_optional:` and `pack --balance` tries
every combination.

Two panels carry the flag:

| panel | size | why it may ride the dark board |
|---|---|---|
| `wc-column` / `cover-spacer` | 550 × 1191 | sealed inside the lower box, never seen |
| `wm-wardrobe` / `back` | 726 × 2470 | **visible** — flagged only on the owner's explicit sign-off |

**Neither moves today, and the flags are insurance, not a recommendation.** The bathroom is now the
*large* decor and the kitchen the small one, which inverts the old economics: U604 buys 3 full sheets
and has room to spare, while U899 buys a single half sheet at 69 % fill. Pushing a bathroom panel
across therefore cannot shrink U604 (it would need to drop below 11.59 m², and it is at 14.15) but can
easily burst the dark half sheet into a full one. That is why every row above except the tie is worse.

`sink-vanity` / `rail-back` deliberately has **no** flag any more. It is genuinely invisible, but there
is no longer a cheaper board to send it to, and a lone dark rail inside a light carcass buys nothing.

The general lesson stands, just pointing the other way now: the useful move is whichever one gets a
decor *under* a sheet boundary, and which direction that is depends entirely on where the boundaries
fall. This project has had the same panel correct on both boards. Do not assume "hidden panels go on
the cheap board".

### ⚠ `wm-wardrobe` / `back` is a flagged panel that is NOT hidden

This document previously said it "must not be given" a `decor_optional`, and the reasoning was right:
the 726 × 2470 back **is** seen — through the 63 mm gap at each side of the washer/dryer stack, above
the dryer, and as the back wall of the overhead cabinet whenever a door is open. The flag exists only
because the owner explicitly signed off (2026-08-12) on this one panel being acceptable in the dark
decor if it ever pays.

So it is the one `decor_optional` in this repo that must not be adopted mechanically. **If `--balance`
ever proposes moving it, look at it first.** Today it proposes nothing: the move is an exact cost tie,
and the 1 % `COST_TIE` band keeps the baseline. A tie is not a reason to make a visible panel a
different colour from the cabinet around it.

### What is deliberately NOT automated

Panels that are *visible but arguably could be another decor* — drawer box interiors, `wc-column`'s
upper back (`back-upper`, whose inner face is the back wall of the shelf compartments and is on show
whenever a door is open) — are a **look** decision, not a free swap. Those never get `decor_optional`,
so the packer can never trade your interior finish away to save a sheet. Change them by hand if you
want them. Note that the trade is now a *contrast* decision rather than a brightness one: the only
other board in the project is near-black.

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

**Last re-derived** 2026-08-12, after the kitchen moved from W1100 Alpine White to U899 Czerń aksamitna
to match the ready-made IKEA METOD dark carcasses.

---
name: plan-order-split
description: Work out how many stock sheets to buy and how to split the meble.pl order across them — which decor, which sheet format, how many of each — and stamp the resulting [order N] markers onto panel names. Use when the user asks what to order, how many boards/sheets are needed, how much material a design costs, whether panels fit on N sheets, or wants the order split recomputed after a design change.
---

# plan-order-split

meble.pl charges for **whole sheets**, and **one order carries one sheet format**. So the panel list
has to be split by decor *and* by format, and the real question is *how many sheets to buy* — not how
to cut them. meble.pl owns nesting; we only ever prove a list fits.

## Run
```bash
python -m meble pack --apartment bohaterow            # recommend the split
python -m meble pack --apartment bohaterow --balance  # also try moving `decor_optional` panels
python -m meble pack --apartment bohaterow --stamp    # write [order N · …] into panel names
python -m meble pack --set kitchen --sheets half      # restrict to one format
```

Sheet formats, prices and the kerf/trim allowances live in `library/materials.yaml` (`sheets:` and
`packing:`). Add `price:` to a sheet and the recommendation optimises money instead of area.

## Reading the result

- **`purchased` vs `panel`** — what you buy against what ends up in the furniture. Utilisation below
  ~65 % usually means a format is being bought for a handful of panels; try `--balance`, or check
  whether one decor is only just over a sheet boundary.
- **`fill` per sheet** — the last sheet in an order is normally the empty one. A first sheet above
  ~90 % is fine; the packer is pessimistic (see below).
- Every panel carries its marker in the free-text name, so it reaches the CSV's `Nazwa` column and the
  PDF sheets without affecting nesting.

## The packer is deliberately pessimistic

Plain **shelf (first-fit-decreasing-height)** packing, several sort heuristics, best result kept,
with a kerf around every panel and a trim off each sheet. That is strictly worse than a real nesting
optimiser — which is the point: **a list that fits here fits at meble.pl with room to spare.** It
never under-reports a sheet. Do not present its layout as a cutting plan; it is a feasibility proof.

`sheet.length` is the grain axis. Both of this project's formats are 2800 long — the half sheet is the
full one ripped lengthwise — so a narrower format does **not** mean shorter panels. A 2520 mm gable
fits a half sheet perfectly well.

## `decor_optional` and `--balance`

A panel that is genuinely never seen can carry `decor_optional: <other-board>`. `--balance` then tries
every on/off combination and keeps the cheapest, because moving a hidden panel between decors changes
how each decor rounds up to whole sheets — sometimes by a whole sheet.

**Only set `decor_optional` on a panel no face of which is visible in use.** Drawer interiors, open
carcass backs and anything seen through a door are a *look* decision, not a free swap — leave those to
the user and never let the packer trade them away.

`--balance` only prints a recommendation. Adopt it by editing `material:` (and the matching
`edge_banding` band) in the YAML, then re-run to confirm it is stable.

## After a design change

The markers are a snapshot. Any panel resized, added or moved between decors makes them stale — the
names will still claim an order that no longer balances. Re-run `pack --stamp` and re-read
`docs/ordering-split.md`, which records the reasoning behind the current split.

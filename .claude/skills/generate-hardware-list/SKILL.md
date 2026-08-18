---
name: generate-hardware-list
description: Work out what HARDWARE to buy — confirmats, minifix, hinges (split by overlay), shelf pins, drawer slides — from the cabinet designs in this meble repo, and export a printable shopping-list PDF. Use when the user asks what fittings/screws/hinges to order, what to buy, a bill of materials, or is preparing a trip to the shop.
---

# generate-hardware-list

Counts the hardware the designs **declare** and renders a one-page shopping list.

## Run
```bash
python -m meble hardware --apartment bohaterow   # or --set / --cabinet
# -> stdout summary + out/pdf/<scope>-hardware.pdf
```

## It counts FITTINGS, never drill holes

That is the whole design, and both alternatives are wrong:

- **A hole does not know what it is for.** There are 50 Ø5 blind holes in this project; most are
  hinge-plate and minifix-bolt holes. Counting them gives 50 shelf pins when the answer is 20.
- **The count is not the quantity.** A shelf-pin fitting's `at` is a list of shelf *heights*, and each
  shelf takes 4 pins. A drawer slide has no holes at all and still has to be bought.

## /!\ Hinges are the thing that goes wrong

Two fittings can share one `hardware:` id and still be **different things to buy**. In `wc-column`,
`door-l` lands on a side panel (**full** overlay) and `door-r` on the shared centre gable (**half**
overlay, crank ~9.5). The Ø35 cup and the 37 mm plate line are *identical*, so nothing on the panel
sheet distinguishes them — only `variant:` does. Ten full-overlay hinges leaves `door-r` unhangeable.

`meble review` cross-checks `variant` against the role of the panel the door mounts on
(`hinge-overlay` rule), and `test_designs.py` asserts it across the whole project.

## Declaring hardware on a fitting

| field | meaning |
|---|---|
| `variant:` | a purchasing difference the drilling cannot express (hinge overlay). Must exist in that hardware's `variants:` in `library/hardware.yaml`. |
| `quantity:` | how many to buy. Defaults to `len(at)`; state it when it differs. |
| `drilling:` | `stamped` (default — `meble fit` owns the holes) / `manual` (hand-derived, tagged `src:`) / `none` (no holes by design). `manual` and `none` are skipped by `fit` **silently**. |

```yaml
- {id: hg-door-r, hardware: hinge-clip-110, variant: half, drilling: manual,
   door: door-r, side: gable-mid, at: [1312, 1868, 2424]}
- {id: pins, hardware: shelf-pin-5, drilling: manual, at: [1630, 2068], quantity: 16,
   shelves: [shelf-l, shelf-r]}
- {id: sl-d1, hardware: slide-bb-350, drilling: none, quantity: 1, drawer: d1-bottom}
```

## SKUs, prices and who sells what

`library/hardware.yaml` carries `components:` (the logical parts of one fitting) and `sourcing:`
(offerings, each saying which components it `covers:`). A hinge is arm+cup **plus** a mounting plate;
Blum sells those as two article numbers, cheaper ranges as one bundle — so the split is a VENDOR fact,
looked up rather than assumed. `meble hardware --vendor centrum.meble.pl` resolves it.

**The important output is the gap report.** A component with no offering means a part of the joint
nobody is going to buy: 10 hinges with no plates hangs zero doors. Never quietly add a missing item to
the sheet by hand — put it in `sourcing:` so it is there next time.

/!\ **Prices are indicative and must carry `checked:`.** A test fails if a price has no date. They are
for budgeting, never quoting — `meble pack` was deleted from this project precisely because a local
number that looked authoritative invited confident decisions that turned out wrong.

Known for centrum.meble.pl today: Blum CLIP top 110° `71T3550` (nakładany) / `71T3650` (bliźniaczy,
i.e. half overlay) and plate `173L6100`. Confirmats, rafix, shelf pins and slides are **not yet
sourced** and the sheet says so.

## Notes
- **Shelf pins in a `depth: through` bore need a COLLAR.** A gable with shelves on both sides gets one
  shared bore, so two pins meet mid-panel at ~9 mm each — fine, but only with something to stop
  against. The tool counts these separately and says so on the sheet.
- The `buy` column adds spares for the small cheap things; `needed` is the exact figure.
- If `meble review` reports `missing-hardware`, a shelf/drawer has no fitting and will simply be
  absent from the list — fix the YAML rather than adding the item by hand.

Run `task test` after touching any of this. Run from the repo root with `PYTHONPATH=tools`.

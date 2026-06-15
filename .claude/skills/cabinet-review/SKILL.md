---
name: cabinet-review
description: Independent custom-cabinet domain-expert review of a design in this meble repo, before ordering. Catches well-known cabinetmaking mistakes — mirror mismatches, carcass arithmetic, holes on the wrong face, breakthrough/blowout, banding errors, wrong materials, structural gaps. Use before placing an order, when the user asks to review/check/sanity-check a cabinet or the whole project, or whenever trust in a design matters. Report-only — never edits.
---

# cabinet-review

A safety net so a fresh session can trust a design before money is spent on cut panels. Two layers:
a deterministic linter, then an **independent** skeptical expert pass. **Report-only — never edit designs
here.** If the user wants fixes applied, that's a separate `design-cabinet` step they approve.

## Workflow

1. **Run the deterministic linter** for the scope:
   ```bash
   python -m meble review --set <set>        # or --cabinet <id> / --apartment <id>
   ```
   Capture its findings (errors/warnings/info).

2. **Run an INDEPENDENT expert pass.** Launch a *separate subagent* (Agent tool, general-purpose) so the
   review isn't anchored to this session's assumptions. Give it: the cabinet YAML file(s) in scope,
   `CLAUDE.md`, `docs/conventions.md`, `docs/cabinet-construction.md`, and the **checklist below**. Tell it:
   *"You are a skeptical, experienced flat-pack cabinetmaker doing a final pre-order review. Go through the
   checklist against each panel and the assembly. For every concern, output: severity (error/warn/info),
   the panel/fitting, what's wrong, why it matters, and the suggested fix. Assume nothing is correct until
   checked. Do not edit files."*

3. **Consolidate** the linter + expert findings into one report, de-duplicated, ordered error → warn →
   info. For each: what, why, suggested fix. End with a clear verdict: **READY TO ORDER** or **ISSUES** (+
   count). Present it to the user; apply nothing.

4. If the user asks to fix items, hand off to `design-cabinet` (edit YAML, re-run `fit`), then re-review.

## Domain checklist (the known pitfalls)

**Geometry / arithmetic**
- Carcass: top/bottom length = `cabinet width − 2×side_thickness` (e.g. W−36). Off-by-thickness is the
  classic sheet-waster.
- Back panel size matches the chosen method (surface = full W×H; grooved = internal + 2×groove depth).
- Shelf width = internal − small clearance; shelf depth < carcass depth (finger gap, back clearance).
- Drawer box width = internal − 25.4 mm (ball-bearing); slide length ≤ internal depth.
- Overall envelope sane vs the space it must fit; plinth/leg + carcass + worktop = intended height.

**Orientation / faces (see `docs/conventions.md`)**
- Faces are `outer` (visible) / `inner` (cavity). Shelf-pin/System-32/hinge-plate holes belong on `inner`;
  confirmat heads on `outer`. A blind Ø5 on `outer`, or a through-head on `inner`, is almost always wrong.
- **Left & right sides are MIRROR parts** — front-edge banding on mirrored edges (2 vs 4); asymmetric holes
  mirror. Two identical sides on an asymmetric cabinet is a real bug.
- Front (visible) edges are banded; the edge that meets another panel or the wall need not be.

**Drilling**
- Blind surface holes: depth < panel thickness (else breakthrough). Edge holes ≥ ~50 mm from a panel end
  (confirmat) and never < ~16 mm (blowout).
- Holes on the 32 mm grid / 37 mm setback where they interface system hardware.
- Regular rows/columns expressed as **bulk `multi`**, not many singles (entry cost + price).
- Holes on both panels of a joint actually coincide (face hole ↔ edge hole at the same point).

**Joinery / structure**
- Every carcass panel is fixed to something (no floating panel).
- Enough fixings per joint (≥2 confirmats per seam; more on long edges). Shelves supported.
- Hinge count vs door height (2 ≤900 mm, 3 ≤1600, 4 above) — when fronts exist.

**Material / banding**
- Back is thin HDF (~3 mm), not 18 mm. Carcass 18 mm. Edge-band decor matches the board.
- Grain direction consistent across a visible run (woodgrains); `grain` set where it matters.

**Smell tests**
- Sink/hob base with a fixed full top (should be rails). Tall/wall unit depths plausible. Door/drawer
  reveals add up to the opening. Reused IKEA units use ACTUAL (not nominal) dimensions for fit.

## Maintaining this checklist
When a real-world issue slips through, **add it here** (and, if it's mechanically checkable, add a rule to
`tools/meble/review.py`). This checklist is meant to grow into the project's accumulated cabinetmaking
wisdom. Run from the repo root with the venv active and `PYTHONPATH=tools`.

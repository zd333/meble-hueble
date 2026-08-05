"""Domain linter — deterministic checks for well-known cabinetmaking pitfalls.

This is the always-on safety net (run `meble review`). It complements `validate` (which checks the
schema/bounds) with *physical* sanity: carcass arithmetic, left/right mirror mismatch, holes on the wrong
face, blind-hole breakthrough, unbanded visible edges, etc. Report-only — it never edits designs.

The `cabinet-review` skill runs this, then adds an independent expert (LLM) pass for judgement-level
issues. As we discover new pitfalls, encode the mechanical ones here and the rest in that skill.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import Cabinet, Project

# local edge that faces the cabinet front, per role (sides are mirror parts: left=2, right=4)
FRONT_EDGE = {"side-left": 2, "side-right": 4, "bottom": 1, "top": 1, "shelf": 1}
VERTICAL_EDGES = {2, 4}

# which face points toward the cavity, per role — default is "inner"; a `top` panel is the one
# exception, since its OUTER face is the one facing down into the cabinet (docs/conventions.md,
# "Horizontals: which face is up"). Roles with BOTH faces facing a cavity (an internal divider with a
# compartment on each side, or a shelf) have no visible face at all, so the wrong-face heuristic — which
# assumes "outer" means "visible exterior" — doesn't apply; skip them outright.
CAVITY_FACE = {"top": "outer"}
NO_VISIBLE_FACE_ROLES = {"gable", "shelf"}


@dataclass
class Finding:
    severity: str   # error | warn | info
    cabinet: str
    rule: str
    message: str


def _review_cabinet(proj: Project, cab: Cabinet, out: list) -> None:
    if cab.kind != "custom":
        return
    panels = cab.panels
    by_role: dict[str, list] = {}
    for p in panels:
        by_role.setdefault(p.role, []).append(p)

    def add(sev, rule, msg):
        out.append(Finding(sev, cab.id, rule, msg))

    sides = by_role.get("side-left", []) + by_role.get("side-right", []) + by_role.get("side", [])
    side_t = proj.panel_thickness(sides[0]) if sides else 18
    W = cab.dimensions.get("width")

    # 1. carcass arithmetic — top/bottom sit between the sides
    if W:
        expected = W - 2 * side_t
        for role in ("top", "bottom"):
            for p in by_role.get(role, []):
                if abs(p.width - expected) > 0.5:
                    add("error", "carcass-arithmetic",
                        f"{role} '{p.id}' width {p.width} ≠ width − 2×side ({W}−{2 * side_t}={expected}). "
                        f"Top/bottom go between the sides.")

    # 2. left/right mirror — front-edge banding must be mirrored (edge 2 left vs edge 4 right)
    L, R = by_role.get("side-left", []), by_role.get("side-right", [])
    if L and R:
        lb = L[0].edge_banding.banded_edges() & VERTICAL_EDGES
        rb = R[0].edge_banding.banded_edges() & VERTICAL_EDGES
        if lb and rb and lb == rb:
            add("warn", "mirror-pair",
                f"side-left and side-right band the same vertical edge {sorted(lb)}. They are MIRROR parts — "
                f"front edge is 2 on the left, 4 on the right; the banding should be mirrored.")

    fitting_panel_ids = set()
    for f in cab.fittings:
        for k in ("through", "into"):
            if f.get(k):
                fitting_panel_ids.add(f[k])

    for p in panels:
        t = proj.panel_thickness(p)
        cavity_face = CAVITY_FACE.get(p.role, "inner")
        check_face = p.role not in NO_VISIBLE_FACE_ROLES
        for h in p.holes:
            if h.is_surface:
                if check_face and h.dia == 5 and h.depth != "through" and h.face != cavity_face:
                    add("warn", "wrong-face",
                        f"'{p.id}': Ø5 blind hole on the {h.face.upper()} face — shelf-pin/system holes "
                        f"normally go toward the cavity ({cavity_face.upper()} here).")
                if check_face and h.dia == 8 and h.depth == "through" and h.face == cavity_face and h.src:
                    add("warn", "wrong-face",
                        f"'{p.id}': Ø8 through-hole (confirmat) on the {cavity_face.upper()} face — heads "
                        f"normally face away from the cavity.")
                if h.depth != "through" and isinstance(h.depth, (int, float)) and h.depth >= t:
                    add("error", "breakthrough",
                        f"'{p.id}': blind hole depth {h.depth} ≥ panel thickness {t} — it breaks through. "
                        f"Reduce depth or set 'through'.")
            if h.is_edge and (h.frm or 0) < 16:
                add("warn", "edge-blowout",
                    f"'{p.id}': edge hole {h.frm} mm from the end (<16 mm) — chipboard blowout risk.")

        fe = FRONT_EDGE.get(p.role)
        if fe and fe not in p.edge_banding.banded_edges():
            add("warn", "front-edge-unbanded",
                f"'{p.id}' ({p.role}): front edge ({fe}) is not banded — it's usually visible.")

        if p.role == "back":
            b = proj.board(p.material)
            if b and b.thickness >= 16:
                add("warn", "back-material",
                    f"'{p.id}': back panel is {b.thickness} mm — backs are usually ~3 mm HDF.")

        if p.role in ("side-left", "side-right", "top", "bottom") and not p.holes \
                and p.id not in fitting_panel_ids:
            add("warn", "floating-panel",
                f"'{p.id}' ({p.role}) has no joinery (no holes, no fitting referencing it) — is it attached?")

    # end margin — first/last screw of a seam must clear the panel end (confirmat etc.)
    pid_to_panel = {p.id: p for p in panels}
    for f in cab.fittings:
        hw = proj.hw(f.get("hardware"))
        at = f.get("at")
        tp = pid_to_panel.get(f.get("through"))
        if not (hw and at and tp):
            continue
        em = hw.raw.get("end_margin")
        if not em:
            continue
        te = (f.get("seam") or {}).get("through_edge")
        seam_len = tp.width if te in (1, 3) else tp.height
        if min(at) < em or (seam_len - max(at)) < em:
            add("warn", "end-margin",
                f"fitting '{f.get('id')}': screws span {min(at)}–{max(at)} mm on a {seam_len} mm edge; "
                f"violates the {em} mm end margin for {hw.id} (chipboard blowout at the ends).")

    # bulk-drilling hint: many identical singles that could be one multi
    for p in panels:
        groups: dict = {}
        for h in p.holes:
            if h.type == "single":
                groups.setdefault((h.face, h.dia, h.depth), []).append(h)
        for (face, dia, _), hs in groups.items():
            if len(hs) >= 3:
                add("info", "bulk-drilling",
                    f"'{p.id}': {len(hs)} single holes (face {face}, Ø{dia}) — if evenly spaced, use one "
                    f"bulk 'multi' hole to cut manual entry.")


def review(proj: Project, cabinets: list[Cabinet]) -> list[Finding]:
    out: list[Finding] = []
    for cab in cabinets:
        _review_cabinet(proj, cab, out)
    return out

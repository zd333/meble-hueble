"""Present a panel in the frame the meble.pl CSV import can actually express.

WHY THIS EXISTS
---------------
The import encodes edge banding as a COUNT PER AXIS, not an identity. `=` means both edges of that
axis; any other non-empty value means exactly one edge; blank means none. **Which** edge it picks is
fixed and unchoosable — measured against the live editor on 2026-08-17 with a 12-row probe, `-`, `_`,
`1`, `3`, `13` in the width column all banded **edge 3**, and `-`, `|`, `2`, `4` in the height column
all banded **edge 4**. meble.pl's own przykładowy_rozkroj.csv only ever uses `=` and `-`.

Two columns × three states is nine patterns against sixteen real ones, so the format is provably
lossy: "band edge 1 only" and "band edge 3 only" are the same CSV cell. Designs here band edge 1 (or
2) alone on 16 of 44 panels, and those imported with the band on the wrong edge.

THE FIX: a 180° in-plane rotation maps 1<->3 and 2<->4, so an edge-1 band becomes an edge-3 band and
the CSV can say it. Width, height, grain direction and the outer/inner faces are all preserved — it
is a ROTATION, not a mirror. (A mirror would also move the band to edge 3, and would swap the faces,
which puts every hole on the wrong side of the board. The distinction is the whole ballgame; see
test_normalize.py::test_faces_are_preserved.) The panel that arrives is physically identical, just
described from the opposite corner.

WHY AT EXPORT TIME AND NOT IN THE YAML
--------------------------------------
52 of the 54 holes on the affected panels are `fit`-stamped, and `meble fit` re-derives stamped holes
in the canonical frame. A rotation stored in the YAML would be silently undone on the next `fit`,
leaving banding rotated and drilling not — with nothing in the toolchain able to notice. So the YAML
stays canonical and this transform runs on the way out, for the CSV and the PDF together (they must
agree: the PDF is what gets typed into the panel the CSV created).

The 3D viewer deliberately does NOT normalise. The rotation is a relabel, so an assembled cabinet
renders identically either way, and nothing is typed from the viewer.
"""
from __future__ import annotations

import copy

from .model import HEIGHT_EDGES, WIDTH_EDGES, Hole, Panel

#: 180° in-plane rotation of the edge numbering. Note it maps width edges to width edges, so an
#: edge's LENGTH is unchanged by the rotation — which is why `_rotate_hole` can use one `L`.
ROT = {1: 3, 2: 4, 3: 1, 4: 2}

#: The edge the importer picks when a banding cell says "one edge". Not configurable — measured.
SINGLE_EDGE_IMPORTS_AS = {WIDTH_EDGES: 3, HEIGHT_EDGES: 4}


def axis_ok(banded: set, axis: tuple) -> bool:
    """Can the CSV express this axis' banding exactly?

    Both edges (`=`), neither (blank), or the single edge the importer happens to pick.
    """
    on = [e for e in axis if e in banded]
    if len(on) != 1:
        return True
    return on[0] == SINGLE_EDGE_IMPORTS_AS[axis]


def unexpressible_edges(banded: set) -> list[int]:
    """Edges that are banded in the design but that the CSV cannot ask for. Empty is the goal."""
    out = []
    for axis in (WIDTH_EDGES, HEIGHT_EDGES):
        on = [e for e in axis if e in banded]
        if len(on) == 1 and on[0] != SINGLE_EDGE_IMPORTS_AS[axis]:
            out.append(on[0])
    return sorted(out)


def should_rotate(panel: Panel) -> bool:
    """Rotate only when it strictly helps.

    A panel banding edge 1 on one axis and edge 4 on the other trades one problem for the other
    (gain 1, loss 1); rotating it would be churn, so it falls through to the caller's warning
    instead. No such panel exists in this project today, but the rule must not assume that.
    """
    banded = panel.edge_banding.banded_edges()
    rotated = {ROT[e] for e in banded}
    gain = loss = 0
    for axis in (WIDTH_EDGES, HEIGHT_EDGES):
        before, after = axis_ok(banded, axis), axis_ok(rotated, axis)
        gain += after and not before
        loss += before and not after
    return gain > 0 and loss == 0


def _rotate_hole(h: Hole, width: float, height: float) -> Hole:
    """Map one hole through the rotation.

    A multi run is re-anchored to its mapped FAR end, because the mapping reverses the order of the
    points: the run must still advance in +direction from its new start. `count` and `spacing` are
    unchanged, so the run stays one editor entry.
    """
    out = copy.deepcopy(h)
    if h.is_surface:
        pts = [(width - x, height - y) for x, y in h.surface_positions()]
        out.x, out.y = pts[-1]
        # face is NOT flipped: rotating in-plane keeps the same side of the board facing you
    elif h.is_edge:
        edge = h.edge_no
        length = width if edge in WIDTH_EDGES else height
        out.face = f"edge{ROT[edge]}"
        out.frm = min(length - p for p in h.edge_positions())
    return out


def rotate_panel(panel: Panel) -> Panel:
    """A copy of `panel` turned 180° in its own plane. Pure; the input is untouched."""
    if panel.grooving:
        raise NotImplementedError(
            f"panel '{panel.id}' has grooving, which this transform cannot rotate yet. "
            "Write that before a design uses it — tests/test_designs.py guards the assumption.")
    out = copy.deepcopy(panel)
    out.edge_banding.edges = {ROT[e]: v for e, v in panel.edge_banding.edges.items()}
    out.holes = [_rotate_hole(h, panel.width, panel.height) for h in panel.holes]
    return out


def normalize(panel: Panel) -> tuple[Panel, bool]:
    """-> (panel to export, whether it was rotated). The panel to export is the input when False."""
    if should_rotate(panel):
        return rotate_panel(panel), True
    return panel, False

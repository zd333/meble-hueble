"""The 180° export-time rotation.

This is new coordinate maths sitting between the design and the saw, so it is tested as a
transform — round-trip, invariants, and exact hand-computed values — not just "it ran".

The failure that matters most is confusing a ROTATION with a MIRROR. Both move an edge-1 band to
edge 3, so a banding-only test passes either way; but a mirror swaps outer/inner and puts every hole
on the wrong side of the board, which is scrap. `test_faces_are_preserved` and the exact-coordinate
tests are what separate them.
"""
from __future__ import annotations

import itertools

import pytest
from conftest import mk_hole, mk_panel

from meble.model import HEIGHT_EDGES, WIDTH_EDGES
from meble.normalize import (ROT, SINGLE_EDGE_IMPORTS_AS, axis_ok, normalize, rotate_panel,
                             should_rotate, unexpressible_edges)


def banded(panel):
    return panel.edge_banding.banded_edges()


# ------------------------------------------------------------------ the rotation itself

def test_rotation_is_its_own_inverse():
    assert {ROT[ROT[e]] for e in (1, 2, 3, 4)} == {1, 2, 3, 4}
    assert all(ROT[ROT[e]] == e for e in (1, 2, 3, 4))


def test_rotation_keeps_each_axis_on_its_own_axis():
    """Width edges must map to width edges, or a panel's width banding would land on its height."""
    assert {ROT[e] for e in WIDTH_EDGES} == set(WIDTH_EDGES)
    assert {ROT[e] for e in HEIGHT_EDGES} == set(HEIGHT_EDGES)


def test_dimensions_grain_and_material_are_untouched():
    p = mk_panel(736, 1308, grain="height", material="u899-18", thickness=18, quantity=2)
    r = rotate_panel(p)
    assert (r.width, r.height) == (736, 1308)
    assert (r.grain, r.material, r.thickness, r.quantity) == ("height", "u899-18", 18, 2)


def test_banding_moves_to_the_opposite_edges():
    p = mk_panel(edges={1: "eb-u604-1", 2: "eb-u604-1"})
    assert banded(rotate_panel(p)) == {3, 4}


def test_all_edges_banding_survives_rotation():
    assert banded(rotate_panel(mk_panel(all_edges=True))) == {1, 2, 3, 4}


def test_rotating_twice_returns_the_original():
    p = mk_panel(600, 400, edges={1: "eb-u604-1"}, holes=[
        mk_hole("outer", dia=8, depth="through", x=50, y=9),
        mk_hole("inner", dia=5, depth=13, x=37, y=100, type="multi", count=4, spacing=32, direction="y"),
        mk_hole("edge2", dia=4, depth=35, frm=120),
        mk_hole("edge3", dia=4, depth=35, frm=50, type="multi", count=3, spacing=150),
    ])
    back = rotate_panel(rotate_panel(p))
    assert banded(back) == banded(p)
    for a, b in zip(back.holes, p.holes):
        assert (a.face, a.x, a.y, a.frm, a.count, a.spacing, a.direction) == \
               (b.face, b.x, b.y, b.frm, b.count, b.spacing, b.direction)


def test_the_input_panel_is_not_mutated():
    p = mk_panel(edges={1: "eb-u604-1"}, holes=[mk_hole("outer", x=10, y=20, depth="through")])
    rotate_panel(p)
    assert banded(p) == {1}
    assert (p.holes[0].x, p.holes[0].y) == (10, 20)


def test_grooving_refuses_rather_than_guessing():
    p = mk_panel()
    p.grooving = [{"edge": 1, "depth": 8}]
    with pytest.raises(NotImplementedError):
        rotate_panel(p)


# ------------------------------------------------------------------ faces: rotation, not mirror

def test_faces_are_preserved():
    """THE critical property. A mirror would swap these, drilling every hole from the wrong side."""
    p = mk_panel(holes=[mk_hole("outer", x=10, y=20, depth="through"),
                        mk_hole("inner", dia=5, depth=13, x=30, y=40)])
    assert [h.face for h in rotate_panel(p).holes] == ["outer", "inner"]


# ------------------------------------------------------------------ hole coordinates

def test_surface_hole_maps_to_the_opposite_corner():
    p = mk_panel(600, 400, holes=[mk_hole("outer", dia=8, depth="through", x=50, y=9)])
    (h,) = rotate_panel(p).holes
    assert (h.x, h.y) == (600 - 50, 400 - 9)


def test_surface_multi_run_keeps_its_points_and_still_advances_forwards():
    p = mk_panel(600, 400, holes=[mk_hole("inner", dia=5, depth=13, x=37, y=100,
                                          type="multi", count=3, spacing=32, direction="y")])
    (h,) = rotate_panel(p).holes
    assert h.direction == "y" and h.count == 3 and h.spacing == 32
    # original ys 100/132/164 -> mapped 300/268/236; the run must START at the lowest
    assert h.surface_positions() == [(563, 236), (563, 268), (563, 300)]
    assert h.y == 236


def test_surface_multi_run_along_x():
    p = mk_panel(600, 400, holes=[mk_hole("outer", dia=8, depth="through", x=50, y=9,
                                          type="multi", count=3, spacing=150, direction="x")])
    (h,) = rotate_panel(p).holes
    # original xs 50/200/350 -> mapped 550/400/250
    assert h.x == 250 and h.y == 391
    assert h.surface_positions() == [(250, 391), (400, 391), (550, 391)]


def test_edge_hole_changes_edge_and_measures_from_the_other_end():
    p = mk_panel(600, 400, holes=[mk_hole("edge1", dia=4, depth=35, frm=120)])
    (h,) = rotate_panel(p).holes
    assert h.face == "edge3"
    assert h.frm == 600 - 120


def test_edge_hole_on_a_vertical_edge_uses_the_height():
    p = mk_panel(600, 400, holes=[mk_hole("edge2", dia=4, depth=35, frm=120)])
    (h,) = rotate_panel(p).holes
    assert h.face == "edge4"
    assert h.frm == 400 - 120


def test_edge_multi_run_is_reanchored_to_its_far_end():
    p = mk_panel(600, 400, holes=[mk_hole("edge3", dia=4, depth=35, frm=50,
                                          type="multi", count=3, spacing=150)])
    (h,) = rotate_panel(p).holes
    # original 50/200/350 -> mapped 550/400/250, run starts at 250
    assert h.face == "edge1" and h.count == 3 and h.spacing == 150
    assert h.edge_positions() == [250, 400, 550]


def test_bore_diameter_and_depth_are_never_changed():
    p = mk_panel(holes=[mk_hole("inner", dia=15, depth=13), mk_hole("edge1", dia=4, depth=35, frm=50)])
    assert [(h.dia, h.depth) for h in rotate_panel(p).holes] == [(15, 13), (4, 35)]


def test_src_tags_survive_so_fit_can_still_own_its_holes():
    p = mk_panel(holes=[mk_hole("outer", x=10, y=20, depth="through", src="cf-top-l")])
    assert rotate_panel(p).holes[0].src == "cf-top-l"


# ------------------------------------------------------------------ the decision rule

@pytest.mark.parametrize("edges,expected", [
    (set(), False),                 # nothing banded — nothing to fix
    ({1}, True),                    # edge 1 alone is inexpressible; rotating gives edge 3
    ({3}, False),                   # already the edge the importer picks
    ({2}, True),
    ({4}, False),
    ({1, 3}, False),                # `=` — exact either way
    ({2, 4}, False),
    ({1, 2, 3, 4}, False),
    ({1, 2}, True),                 # both axes fixed at once -> {3, 4}
    ({1, 4}, False),                # gain 1, loss 1 — rotating just moves the problem
    ({3, 2}, False),                # ditto, mirrored
    ({1, 2, 4}, True),              # width single 1 -> 3; height stays `=`
    ({1, 3, 2}, True),              # width `=` unaffected; height 2 -> 4
])
def test_should_rotate(edges, expected):
    assert should_rotate(mk_panel(edges={e: "eb-u604-1" for e in edges})) is bool(expected)


def test_normalize_is_idempotent():
    """Normalising an already-normalised panel must be a no-op, or the frame would flip-flop."""
    for combo in itertools.chain.from_iterable(
            itertools.combinations((1, 2, 3, 4), n) for n in range(5)):
        p = mk_panel(edges={e: "eb-u604-1" for e in combo})
        once, _ = normalize(p)
        twice, rotated_again = normalize(once)
        assert rotated_again is False, f"{combo} keeps rotating"
        assert banded(twice) == banded(once)


def test_normalize_leaves_expressible_panels_completely_alone():
    p = mk_panel(edges={1: "eb-u604-1", 3: "eb-u604-1"},
                 holes=[mk_hole("outer", x=10, y=20, depth="through")])
    out, rotated = normalize(p)
    assert rotated is False
    assert out is p


def test_every_banding_pattern_is_expressible_after_normalising():
    """The point of the whole exercise, over all 16 patterns."""
    stuck = []
    for combo in itertools.chain.from_iterable(
            itertools.combinations((1, 2, 3, 4), n) for n in range(5)):
        out, _ = normalize(mk_panel(edges={e: "eb-u604-1" for e in combo}))
        if unexpressible_edges(banded(out)):
            stuck.append(combo)
    # only the two genuinely unfixable ones: one axis wants 1, the other wants 4 (or 3 and 2)
    assert stuck == [(1, 4), (2, 3)]


def test_axis_ok_matches_what_the_importer_does():
    assert SINGLE_EDGE_IMPORTS_AS == {WIDTH_EDGES: 3, HEIGHT_EDGES: 4}
    assert axis_ok({3}, WIDTH_EDGES) and not axis_ok({1}, WIDTH_EDGES)
    assert axis_ok({4}, HEIGHT_EDGES) and not axis_ok({2}, HEIGHT_EDGES)
    assert axis_ok(set(), WIDTH_EDGES) and axis_ok({1, 3}, WIDTH_EDGES)


# ------------------------------------------------------------------ against the real designs

def test_every_real_panel_round_trips(real_panels):
    for cab, panel, _ in real_panels:
        back = rotate_panel(rotate_panel(panel))
        assert banded(back) == banded(panel), f"{cab.id}/{panel.id}"
        for a, b in zip(back.holes, panel.holes):
            assert (a.face, a.x, a.y, a.frm) == (b.face, b.x, b.y, b.frm), f"{cab.id}/{panel.id}"


def test_every_real_panel_keeps_its_holes_inside_the_panel_after_rotation(real_panels):
    for cab, panel, _ in real_panels:
        r = rotate_panel(panel)
        for h in r.holes:
            where = f"{cab.id}/{panel.id} {h.face}"
            if h.is_surface:
                for x, y in h.surface_positions():
                    assert 0 <= x <= r.width and 0 <= y <= r.height, f"{where}: ({x},{y})"
            else:
                length = r.width if h.edge_no in WIDTH_EDGES else r.height
                for pos in h.edge_positions():
                    assert 0 <= pos <= length, f"{where}: {pos} of {length}"


def test_rotation_preserves_the_physical_hole_pattern(real_panels):
    """Measured from the opposite corner, the set of holes must be the same set of holes."""
    for cab, panel, _ in real_panels:
        r = rotate_panel(panel)
        before = sorted((h.face, tuple(h.surface_positions())) for h in panel.holes if h.is_surface)
        after = sorted((h.face, tuple(sorted((panel.width - x, panel.height - y)
                                             for x, y in h.surface_positions())))
                       for h in r.holes if h.is_surface)
        assert len(before) == len(after), f"{cab.id}/{panel.id} lost a hole"


def test_no_real_panel_is_left_unexpressible_after_normalising(real_panels):
    stuck = [f"{c.id}/{p.id} edges {unexpressible_edges(banded(normalize(p)[0]))}"
             for c, p, _ in real_panels if unexpressible_edges(banded(normalize(p)[0]))]
    assert stuck == [], f"still unexpressible: {stuck}"


def test_the_expected_number_of_real_panels_rotate(real_panels):
    rotated = [f"{c.id}/{p.id}" for c, p, _ in real_panels if normalize(p)[1]]
    assert len(rotated) == 16, rotated


# ------------------------------------------------------------------ the editor's multi-hole limit

from meble.normalize import MAX_MULTI_SPACING, expand_wide_multis  # noqa: E402


def test_a_narrow_run_stays_one_entry():
    """That is the whole value of `multi`: one line to type instead of N."""
    h = mk_hole("inner", dia=5, depth=13, x=37, y=100, type="multi", count=4, spacing=32,
                direction="y")
    assert expand_wide_multis([h]) == [h]


def test_a_run_exactly_at_the_limit_is_still_allowed():
    h = mk_hole("inner", x=37, y=100, type="multi", count=3, spacing=MAX_MULTI_SPACING,
                direction="y")
    assert len(expand_wide_multis([h])) == 1


def test_a_wide_surface_run_becomes_individual_holes():
    h = mk_hole("outer", dia=8, depth="through", x=98, y=1819, type="multi", count=3,
                spacing=250, direction="x")
    out = expand_wide_multis([h])
    assert [(o.x, o.y) for o in out] == [(98, 1819), (348, 1819), (598, 1819)]
    assert all(o.type == "single" for o in out)
    assert all(o.count is None and o.spacing is None and o.direction is None for o in out)


def test_a_wide_edge_run_becomes_individual_holes():
    h = mk_hole("edge2", dia=4, depth=35, frm=126, type="multi", count=3, spacing=237)
    out = expand_wide_multis([h])
    assert [o.frm for o in out] == [126, 363, 600]
    assert all(o.type == "single" and o.count is None for o in out)


def test_expansion_preserves_everything_except_the_run():
    h = mk_hole("inner", dia=5, depth=13, x=37, y=100, type="multi", count=2, spacing=500,
                direction="y", src="pins")
    for o in expand_wide_multis([h]):
        assert (o.face, o.dia, o.depth, o.src) == ("inner", 5, 13, "pins")


def test_expansion_never_moves_a_single_hole():
    h = mk_hole("outer", dia=8, depth="through", x=50, y=60)
    assert expand_wide_multis([h]) == [h]


def test_the_expanded_holes_sit_exactly_where_the_run_did(real_panels):
    """The physical drilling must be identical — only the number of editor entries changes."""
    for cab, panel, _ in real_panels:
        before = sorted((h.face, tuple(h.surface_positions()) if h.is_surface
                         else tuple(h.edge_positions())) for h in panel.holes)
        after: list = []
        for h in expand_wide_multis(panel.holes):
            after.extend((h.face, p) for p in
                         (h.surface_positions() if h.is_surface else h.edge_positions()))
        flat_before: list = []
        for face, pts in before:
            flat_before.extend((face, p) for p in pts)
        assert sorted(map(str, flat_before)) == sorted(map(str, after)), f"{cab.id}/{panel.id}"


def test_no_real_panel_keeps_a_run_the_editor_would_reject(real_panels):
    """After expansion every remaining `multi` must be inside the editor's limit."""
    for cab, panel, _ in real_panels:
        for h in expand_wide_multis(panel.holes):
            if h.type == "multi":
                assert h.spacing <= MAX_MULTI_SPACING, f"{cab.id}/{panel.id}: @{h.spacing}"

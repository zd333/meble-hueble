"""Each `meble review` rule fires on a crafted bad panel and stays silent on a good one.

`review` is the always-on safety net for physical mistakes — the ones that produce a panel which is
dimensionally correct and still useless. Every rule here corresponds to a way somebody has actually
ruined a carcass.
"""
from __future__ import annotations

from conftest import mk_cabinet, mk_hole, mk_panel

from meble.review import review


def rules(proj, panels, *, dimensions=None, fittings=()):
    cab = mk_cabinet(panels, fittings=fittings)
    cab.dimensions = dict(dimensions or {})
    return [f.rule for f in review(proj, [cab])]


def side(role, edge, **kw):
    return mk_panel(560, 720, id=role, role=role, edges={edge: "eb-u604-1"}, **kw)


# ------------------------------------------------------------------ carcass arithmetic

def test_top_between_sides_must_be_width_minus_two_thicknesses(proj):
    """W−2t is the single most common carcass error and it wastes the whole panel."""
    good = mk_panel(564, 560, id="t", role="top", edges={1: "eb-u604-1"},
                    holes=[mk_hole("outer", depth="through", x=10, y=10)])
    bad = mk_panel(600, 560, id="t", role="top", edges={1: "eb-u604-1"},
                   holes=[mk_hole("outer", depth="through", x=10, y=10)])
    assert "carcass-arithmetic" not in rules(proj, [good], dimensions={"width": 600})
    assert "carcass-arithmetic" in rules(proj, [bad], dimensions={"width": 600})


# ------------------------------------------------------------------ mirror pair

def test_left_and_right_sides_banding_the_same_vertical_edge_warns(proj):
    """Left and right are mirror parts; identical banding means one of them is wrong."""
    same = [side("side-left", 2), side("side-right", 2)]
    mirrored = [side("side-left", 2), side("side-right", 4)]
    assert "mirror-pair" in rules(proj, same)
    assert "mirror-pair" not in rules(proj, mirrored)


# ------------------------------------------------------------------ drilling

def test_blind_hole_at_or_past_panel_thickness_breaks_through(proj):
    p = mk_panel(600, 400, thickness=18, holes=[mk_hole("inner", dia=5, depth=18, x=50, y=50)])
    assert "breakthrough" in rules(proj, [p])
    ok = mk_panel(600, 400, thickness=18, holes=[mk_hole("inner", dia=5, depth=13, x=50, y=50)])
    assert "breakthrough" not in rules(proj, [ok])


def test_edge_hole_too_close_to_the_end_warns_about_blowout(proj):
    p = mk_panel(600, 400, holes=[mk_hole("edge1", dia=8, depth=35, frm=10)])
    assert "edge-blowout" in rules(proj, [p])


def test_shelf_pin_hole_on_the_wrong_face_warns(proj):
    """A Ø5 blind pin hole belongs on the cavity face; on `outer` it shows on the outside."""
    bad = mk_panel(600, 400, role="side-left", edges={2: "eb-u604-1"},
                   holes=[mk_hole("outer", dia=5, depth=13, x=37, y=100)])
    good = mk_panel(600, 400, role="side-left", edges={2: "eb-u604-1"},
                    holes=[mk_hole("inner", dia=5, depth=13, x=37, y=100)])
    assert "wrong-face" in rules(proj, [bad])
    assert "wrong-face" not in rules(proj, [good])


def test_a_top_panel_inverts_the_cavity_face(proj):
    """docs/conventions.md: a `top` panel's OUTER face points DOWN into the cabinet. The rule has to
    follow the joinery, not the everyday sense of 'outer'."""
    on_outer = mk_panel(564, 560, role="top", edges={1: "eb-u604-1"},
                        holes=[mk_hole("outer", dia=5, depth=13, x=37, y=100)])
    on_inner = mk_panel(564, 560, role="top", edges={1: "eb-u604-1"},
                        holes=[mk_hole("inner", dia=5, depth=13, x=37, y=100)])
    assert "wrong-face" not in rules(proj, [on_outer])
    assert "wrong-face" in rules(proj, [on_inner])


def test_gable_and_shelf_are_exempt_from_the_face_rule(proj):
    """Both faces front a cavity, so 'outer' carries no meaning — flagging them is noise."""
    for role in ("gable", "shelf"):
        p = mk_panel(600, 400, role=role, edges={1: "eb-u604-1", 2: "eb-u604-1"},
                     holes=[mk_hole("outer", dia=5, depth=13, x=37, y=100)])
        assert "wrong-face" not in rules(proj, [p]), role


# ------------------------------------------------------------------ banding and structure

def test_unbanded_front_edge_warns_per_role(proj):
    """Front edge is 2 on a left side, 4 on a right side, 1 on horizontals."""
    assert "front-edge-unbanded" in rules(proj, [side("side-left", 4)])
    assert "front-edge-unbanded" not in rules(proj, [side("side-left", 2)])
    assert "front-edge-unbanded" in rules(proj, [side("side-right", 2)])
    assert "front-edge-unbanded" not in rules(proj, [side("side-right", 4)])


def test_thick_back_panel_warns(proj):
    p = mk_panel(600, 400, role="back", material="u604-18", edges={1: "eb-u604-1"})
    assert "back-material" in rules(proj, [p])


def test_structural_panel_with_no_joinery_warns(proj):
    lonely = mk_panel(560, 720, id="s", role="side-left", edges={2: "eb-u604-1"})
    assert "floating-panel" in rules(proj, [lonely])


def test_a_fitting_referencing_the_panel_satisfies_the_joinery_check(proj):
    """The holes may not be stamped yet; a fitting that names the panel is enough."""
    lonely = mk_panel(560, 720, id="s", role="side-left", edges={2: "eb-u604-1"})
    got = rules(proj, [lonely], fittings=[{"id": "cf1", "through": "s", "into": "s"}])
    assert "floating-panel" not in got


def test_three_identical_singles_suggest_a_multi_hole(proj):
    """Bulk drilling is one editor entry instead of N — the whole point of the PDF workflow."""
    holes = [mk_hole("inner", dia=5, depth=13, x=37, y=y) for y in (100, 132, 164)]
    assert "bulk-drilling" in rules(proj, [mk_panel(600, 400, role="gable", holes=holes)])


def test_real_project_has_no_review_errors(proj):
    from meble.model import cabinets_for_scope
    findings = review(proj, cabinets_for_scope(proj, apartment="bohaterow"))
    assert [f for f in findings if f.severity == "error"] == []

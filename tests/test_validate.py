"""Every `validate` check fires on a bad panel and stays silent on a good one.

These catch the errors that reach the saw as scrap: a hole off the edge of a panel, a bore diameter
the machine does not have, a band that does not exist.
"""
from __future__ import annotations

import pytest
from conftest import mk_cabinet, mk_hole, mk_panel

from meble.validate import validate, validate_cabinet


def run(proj, panels, **cab_kw):
    err, warn = [], []
    validate_cabinet(proj, mk_cabinet(panels, **cab_kw), err.append, warn.append)
    return err, warn


def test_clean_panel_produces_nothing(proj):
    err, warn = run(proj, [mk_panel(holes=[mk_hole("outer", dia=8, depth="through", x=50, y=50)])])
    assert err == [] and warn == []


def test_real_project_validates_clean(proj):
    """The designs on disk must stay valid — this is the one that guards the actual order."""
    from meble.model import cabinets_for_scope
    errors, _ = validate(proj, cabinets_for_scope(proj, apartment="bohaterow"))
    assert errors == []


# ------------------------------------------------------------------ bounds

def test_surface_hole_outside_panel_is_an_error(proj):
    err, _ = run(proj, [mk_panel(600, 400, holes=[mk_hole("outer", x=650, y=50, depth="through")])])
    assert any("outside panel" in e for e in err)


def test_multi_surface_run_extending_past_the_edge_is_an_error(proj):
    """The last hole of the run is what falls off — a single-point check would miss this."""
    h = mk_hole("inner", dia=5, depth=13, type="multi", x=100, y=100,
                count=10, spacing=100, direction="x")
    err, _ = run(proj, [mk_panel(600, 400, holes=[h])])
    assert any("outside panel" in e for e in err)


def test_edge_hole_past_the_end_of_its_edge_is_an_error(proj):
    err, _ = run(proj, [mk_panel(600, 400, holes=[mk_hole("edge1", dia=8, depth=35, frm=700)])])
    assert any("outside edge length" in e for e in err)


def test_edge_hole_length_is_measured_on_the_right_axis(proj):
    """edge1/3 run along the width, edge2/4 along the height. Confusing them hides real overruns."""
    # 500 is fine on the 600-wide edge 1, but past the end of the 400-high edge 2
    ok, _ = run(proj, [mk_panel(600, 400, holes=[mk_hole("edge1", dia=8, depth=35, frm=500)])])
    bad, _ = run(proj, [mk_panel(600, 400, holes=[mk_hole("edge2", dia=8, depth=35, frm=500)])])
    assert ok == []
    assert any("outside edge length" in e for e in bad)


# ------------------------------------------------------------------ legal value sets

@pytest.mark.parametrize("dia", [5, 6, 10])
def test_illegal_edge_bore_is_an_error(proj, dia):
    err, _ = run(proj, [mk_panel(holes=[mk_hole("edge1", dia=dia, depth=35, frm=100)])])
    assert any("edge bore" in e for e in err)


@pytest.mark.parametrize("dia", [4, 6, 12])
def test_illegal_surface_bore_is_an_error(proj, dia):
    err, _ = run(proj, [mk_panel(holes=[mk_hole("outer", dia=dia, depth=10, x=50, y=50)])])
    assert any("surface bore" in e for e in err)


def test_surface_depth_over_15_must_be_through(proj):
    err, _ = run(proj, [mk_panel(holes=[mk_hole("outer", dia=8, depth=20, x=50, y=50)])])
    assert any("surface depth" in e for e in err)


def test_multi_hole_without_count_or_spacing_is_an_error(proj):
    err, _ = run(proj, [mk_panel(holes=[mk_hole("edge1", dia=8, depth=35, frm=50, type="multi")])])
    assert any("needs count + spacing" in e for e in err)


def test_multi_surface_hole_without_direction_is_an_error(proj):
    h = mk_hole("outer", dia=8, depth="through", x=50, y=50, type="multi", count=3, spacing=32)
    err, _ = run(proj, [mk_panel(holes=[h])])
    assert any("direction" in e for e in err)


# ------------------------------------------------------------------ faces and refs

def test_deprecated_front_back_face_names_are_rejected(proj):
    """`front`/`back` are the editor's words; ours are outer/inner. Mixing them flips the drill side."""
    err, _ = run(proj, [mk_panel(holes=[mk_hole("front", dia=8, depth="through", x=50, y=50)])])
    assert any("deprecated" in e for e in err)


def test_unknown_material_is_an_error(proj):
    err, _ = run(proj, [mk_panel(material="nope-18")])
    assert any("not in library/materials.yaml" in e for e in err)


def test_unknown_edge_band_is_an_error(proj):
    err, _ = run(proj, [mk_panel(edges={1: "eb-does-not-exist"})])
    assert any("not in library/edgebands.yaml" in e for e in err)


def test_banding_edge_outside_1_to_4_is_an_error(proj):
    err, _ = run(proj, [mk_panel(edges={5: "eb-u604-1"})])
    assert any("must be 1..4" in e for e in err)


def test_zero_dimension_is_an_error(proj):
    err, _ = run(proj, [mk_panel(0, 400)])
    assert any("must be > 0" in e for e in err)


def test_orphan_stamped_hole_warns(proj):
    """A hole whose `src` fitting is gone is a leftover from a deleted joint — it still gets drilled."""
    p = mk_panel(holes=[mk_hole("outer", dia=8, depth="through", x=50, y=50, src="cf-gone")])
    _, warn = run(proj, [p])
    assert any("orphan stamp" in w for w in warn)


def test_fitting_referencing_a_missing_panel_is_an_error(proj):
    err, _ = run(proj, [mk_panel(id="a")],
                 fittings=[{"id": "f1", "through": "a", "into": "ghost"}])
    assert any("into panel 'ghost' not found" in e for e in err)


def test_fitting_with_unknown_hardware_is_an_error(proj):
    err, _ = run(proj, [mk_panel(id="a")],
                 fittings=[{"id": "f1", "hardware": "no-such-screw", "through": "a", "into": "a"}])
    assert any("not in library/hardware.yaml" in e for e in err)


def test_bad_seam_edge_is_an_error(proj):
    err, _ = run(proj, [mk_panel(id="a")],
                 fittings=[{"id": "f1", "through": "a", "into": "a", "seam": {"through_edge": 7}}])
    assert any("seam.through_edge must be 1..4" in e for e in err)

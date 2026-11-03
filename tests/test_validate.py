"""Every `validate` check fires on a bad panel and stays silent on a good one.

These catch the errors that reach the saw as scrap: a hole off the edge of a panel, a bore diameter
the machine does not have, a band that does not exist.
"""
from __future__ import annotations

import pytest
from conftest import mk_cabinet, mk_hole, mk_notch, mk_panel

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


# ------------------------------------------------------------------ buyable-hardware fields

def test_a_fitting_that_buys_nothing_is_an_error(proj):
    """No `at` and no `quantity` means it silently contributes zero to the shopping list — the one
    failure that is only discovered at assembly, with the shops shut."""
    err, _ = run(proj, [mk_panel(id="a")], fittings=[{"id": "f1", "hardware": "confirmat-7x50"}])
    assert any("buys nothing" in e for e in err)


def test_quantity_below_one_is_an_error(proj):
    err, _ = run(proj, [mk_panel(id="a")],
                 fittings=[{"id": "f1", "hardware": "confirmat-7x50", "quantity": 0}])
    assert any("quantity must be" in e for e in err)


def test_unknown_drilling_mode_is_an_error(proj):
    err, _ = run(proj, [mk_panel(id="a")],
                 fittings=[{"id": "f1", "hardware": "confirmat-7x50", "at": [1], "drilling": "later"}])
    assert any("drilling 'later'" in e for e in err)


def test_unknown_variant_is_an_error(proj):
    err, _ = run(proj, [mk_panel(id="a")],
                 fittings=[{"id": "f1", "hardware": "hinge-clip-110", "at": [1], "variant": "sideways"}])
    assert any("variant 'sideways'" in e for e in err)


def test_a_variant_on_hardware_with_none_declared_is_an_error(proj):
    err, _ = run(proj, [mk_panel(id="a")],
                 fittings=[{"id": "f1", "hardware": "confirmat-7x50", "at": [1], "variant": "full"}])
    assert any("declares no variants" in e for e in err)


def test_known_variant_is_accepted(proj):
    err, _ = run(proj, [mk_panel(id="a")],
                 fittings=[{"id": "f1", "hardware": "hinge-clip-110", "at": [1], "variant": "half"}])
    assert err == []


def test_drilling_none_with_holes_is_a_contradiction(proj):
    """One of the two statements is wrong, and neither is safe to assume."""
    p = mk_panel(id="a", holes=[mk_hole("outer", depth="through", x=10, y=10, src="sl1")])
    err, _ = run(proj, [p], fittings=[{"id": "sl1", "hardware": "slide-bb-350",
                                       "drilling": "none", "quantity": 1}])
    assert any("drilling is 'none' but panels carry holes" in e for e in err)


def test_drilling_manual_with_no_holes_warns(proj):
    _, warn = run(proj, [mk_panel(id="a")],
                  fittings=[{"id": "hg1", "hardware": "hinge-clip-110", "at": [1],
                             "drilling": "manual"}])
    assert any("no hole references it" in w for w in warn)


def test_list_valued_panel_refs_are_resolved(proj):
    err, _ = run(proj, [mk_panel(id="shelf-a")],
                 fittings=[{"id": "pins", "hardware": "shelf-pin-5", "quantity": 4,
                            "drilling": "manual", "shelves": ["shelf-a", "ghost"]}])
    assert any("shelves panel 'ghost' not found" in e for e in err)


# ------------------------------------------------------------------ notches

def test_notch_in_a_corner_is_clean(proj):
    err, warn = run(proj, [mk_panel(1050, 875, notches=[mk_notch("bottom-left"), mk_notch("bottom-right")],
                                    holes=[mk_hole("outer", depth="through", x=500, y=50)])])
    assert err == [] and warn == []


def test_notch_with_unknown_corner_is_an_error(proj):
    err, _ = run(proj, [mk_panel(notches=[mk_notch("front-left")])])
    assert any("corner 'front-left'" in e for e in err)


def test_notch_as_big_as_the_panel_is_an_error(proj):
    err, _ = run(proj, [mk_panel(600, 400, notches=[mk_notch(width=600, height=50)])])
    assert any("smaller than the panel" in e for e in err)


def test_overlapping_notches_are_an_error(proj):
    err, _ = run(proj, [mk_panel(600, 400, notches=[mk_notch("top-left", 400, 50),
                                                    mk_notch("top-right", 300, 80)])])
    assert any("overlap" in e for e in err)


def test_notches_that_meet_are_an_error(proj):
    """They take edge 4 away entirely; the outline the viewer extrudes would double back on itself."""
    err, _ = run(proj, [mk_panel(1000, 400, notches=[mk_notch("bottom-left", 600, 100),
                                                     mk_notch("top-left", 600, 300)])])
    assert any("overlap or meet" in e for e in err)


def test_surface_hole_in_the_cut_away_corner_is_an_error(proj):
    err, _ = run(proj, [mk_panel(1050, 875, notches=[mk_notch("bottom-left")],
                                 holes=[mk_hole("inner", dia=5, depth=13, x=10, y=50)])])
    assert any("cut-away corner" in e for e in err)


def test_surface_hole_breaking_into_the_notch_is_an_error(proj):
    """Centre outside the notch, bore crossing into it: the edge of the hole is open."""
    err, _ = run(proj, [mk_panel(1050, 875, notches=[mk_notch("bottom-left")],
                                 holes=[mk_hole("outer", dia=20, depth=13, x=24, y=50)])])
    assert any("cut-away corner" in e for e in err)


def test_edge_hole_in_the_cut_away_part_of_its_edge_is_an_error(proj):
    err, _ = run(proj, [mk_panel(1050, 875, notches=[mk_notch("bottom-left")],
                                 holes=[mk_hole("edge4", dia=8, depth=30, frm=50)])])
    assert any("cut-away corner" in e for e in err)


def test_edge_hole_on_an_edge_the_notch_does_not_touch_is_fine(proj):
    err, _ = run(proj, [mk_panel(1050, 875, notches=[mk_notch("bottom-left")],
                                 holes=[mk_hole("edge2", dia=8, depth=30, frm=50)])])
    assert err == []


def test_banded_edge_without_a_band_model_is_an_error(proj):
    """The CSV bands it; the PDF, which carries the band model, would print it as unbanded."""
    p = mk_panel(all_edges=True)
    p.edge_banding.band = None
    err, _ = run(proj, [p])
    assert any("name no band model" in e for e in err)
    p.edge_banding.band = "eb-nope"
    err, _ = run(proj, [p])
    assert any("'eb-nope' not in library" in e for e in err)


def test_banded_part_below_the_supplier_minimum_is_an_error(proj):
    """meble.pl's editor blocks banding anything under 59.6 × 199.6, whichever way round."""
    for w, h in ((200, 40), (40, 200), (190, 150)):       # short side, or long side, too small
        err, _ = run(proj, [mk_panel(w, h, all_edges=True)])
        assert any("smallest banded part" in e for e in err), (w, h)
    err, _ = run(proj, [mk_panel(200, 60, all_edges=True)])
    assert not any("smallest banded part" in e for e in err)
    err, _ = run(proj, [mk_panel(200, 40)])                      # unbanded: the saw does not care
    assert not any("smallest banded part" in e for e in err)

"""The bill of materials.

The regression that created this module: `wc-column`'s two doors both use `hinge-clip-110`, but one
lands on a side panel (full overlay) and the other on the shared centre gable (half overlay). The
drilling is identical, so nothing in the holes can separate them — only `variant:` can. Collapsing
them into "10 hinges" buys three that will not let the door shut.
"""
from __future__ import annotations

import pytest
from conftest import mk_cabinet, mk_hole, mk_panel

from meble.hardware import Line, bill_of_materials, collared_pins, fitting_quantity
from meble.model import cabinets_for_scope


def bom(proj, cab):
    return {(l.hardware, l.variant): l.quantity for l in bill_of_materials(proj, [cab])}


def hinge(fid, variant, side="side-l", at=(100, 200)):
    return {"id": fid, "hardware": "hinge-clip-110", "variant": variant, "drilling": "manual",
            "door": "door", "side": side, "at": list(at)}


# ------------------------------------------------------------------ quantity

def test_quantity_defaults_to_the_number_of_positions():
    assert fitting_quantity({"at": [50, 200, 350]}) == 3


def test_explicit_quantity_wins_over_the_positions():
    """A shelf-pin fitting's `at` is a list of shelf HEIGHTS; each shelf takes 4 pins."""
    assert fitting_quantity({"at": [1630, 2068], "quantity": 16}) == 16


def test_a_fitting_with_no_positions_still_counts_when_it_says_how_many():
    """Drawer slides have no holes at all — they are mounted on site — but still get bought."""
    assert fitting_quantity({"quantity": 2}) == 2


def test_a_fitting_with_neither_counts_zero_here_and_is_caught_by_validate():
    assert fitting_quantity({"id": "x"}) == 0


# ------------------------------------------------------------------ grouping

def test_same_hardware_different_variant_stays_two_lines(proj):
    """THE regression. One `hardware:` id, two things to buy."""
    cab = mk_cabinet([mk_panel(id="door"), mk_panel(id="side-l"), mk_panel(id="gable")],
                     fittings=[hinge("hg-l", "full", side="side-l"),
                               hinge("hg-r", "half", side="gable")])
    assert bom(proj, cab) == {("hinge-clip-110", "full"): 2, ("hinge-clip-110", "half"): 2}


def test_same_hardware_same_variant_is_summed(proj):
    cab = mk_cabinet([mk_panel(id="door"), mk_panel(id="side-l")],
                     fittings=[hinge("hg-l", "full"), hinge("hg-r", "full")])
    assert bom(proj, cab) == {("hinge-clip-110", "full"): 4}


def test_variantless_hardware_groups_under_a_single_line(proj):
    cab = mk_cabinet([mk_panel(id="a"), mk_panel(id="b")], fittings=[
        {"id": "cf1", "hardware": "confirmat-7x50", "through": "a", "into": "b", "at": [50, 200]},
        {"id": "cf2", "hardware": "confirmat-7x50", "through": "a", "into": "b", "at": [50]},
    ])
    assert bom(proj, cab) == {("confirmat-7x50", None): 3}


def test_unknown_hardware_is_skipped_not_crashed(proj):
    """validate.py reports the broken ref; the buy list must not blow up on it."""
    cab = mk_cabinet([mk_panel(id="a")],
                     fittings=[{"id": "x", "hardware": "no-such", "at": [1]}])
    assert bom(proj, cab) == {}


def test_lines_carry_the_per_cabinet_split(proj):
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    for line in bill_of_materials(proj, cabs):
        assert sum(line.per_cabinet.values()) == line.quantity, line.label
        assert line.per_cabinet, line.label


def test_readymade_cabinets_contribute_nothing(proj):
    from meble.model import Cabinet
    assert bill_of_materials(proj, [Cabinet(id="ikea", kind="readymade")]) == []


def test_sold_as_comes_from_the_library(proj):
    cab = mk_cabinet([mk_panel(id="d1-bottom")], fittings=[
        {"id": "sl", "hardware": "slide-bb-350", "drilling": "none", "quantity": 1,
         "drawer": "d1-bottom"}])
    (line,) = bill_of_materials(proj, [cab])
    assert line.sold_as == "pair" and line.quantity == 1


def test_label_is_short_and_variant_name_keeps_the_shop_wording():
    line = Line(hardware="h", variant="half", name="Hinge", variant_name="half overlay (półnakładany)")
    assert line.label == "Hinge — half overlay"
    assert "półnakładany" in line.variant_name


# ------------------------------------------------------------------ collared pins

def test_a_through_bore_needs_two_collared_pins(proj):
    """One bore in a gable serves a shelf on each side, so it takes a pin from each direction."""
    cab = mk_cabinet([mk_panel(id="gable", holes=[
        mk_hole("inner", dia=5, depth="through", x=37, y=100, src="pins")])],
        fittings=[{"id": "pins", "hardware": "shelf-pin-5", "drilling": "manual",
                   "at": [100], "quantity": 4}])
    assert collared_pins(proj, [cab]) == 2


def test_blind_pin_bores_need_no_collar(proj):
    cab = mk_cabinet([mk_panel(id="side", holes=[
        mk_hole("inner", dia=5, depth=13, x=37, y=100, src="pins")])],
        fittings=[{"id": "pins", "hardware": "shelf-pin-5", "drilling": "manual",
                   "at": [100], "quantity": 4}])
    assert collared_pins(proj, [cab]) == 0


def test_a_through_hole_that_is_not_a_pin_is_not_counted(proj):
    """Ø5 through holes also occur as confirmat/other stamps; only pin fittings count."""
    cab = mk_cabinet([mk_panel(id="p", holes=[
        mk_hole("outer", dia=5, depth="through", x=37, y=100, src="cf-x")])],
        fittings=[{"id": "cf-x", "hardware": "confirmat-7x50", "at": [100]}])
    assert collared_pins(proj, [cab]) == 0


# ------------------------------------------------------------------ against the real designs

EXPECTED = {
    ("confirmat-7x50", None): 85,
    ("hinge-clip-110", "full"): 7,
    ("hinge-clip-110", "half"): 3,
    ("minifix-15", None): 18,
    ("shelf-pin-5", None): 20,
    ("slide-bb-350", None): 2,
}


def test_the_real_bill_of_materials(proj):
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    got = {(l.hardware, l.variant): l.quantity for l in bill_of_materials(proj, cabs)}
    assert got == EXPECTED


def test_the_two_hinge_types_are_never_merged(proj):
    """Stated separately from the table above because it is the whole point of the feature."""
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    hinges = [l for l in bill_of_materials(proj, cabs) if l.hardware == "hinge-clip-110"]
    assert len(hinges) == 2, "the two overlays collapsed into one line"
    assert sorted(l.variant for l in hinges) == ["full", "half"]
    half = next(l for l in hinges if l.variant == "half")
    assert list(half.per_cabinet) == ["wc-column"], "only wc-column shares a gable between two doors"


def test_the_real_collared_pin_count(proj):
    assert collared_pins(proj, cabinets_for_scope(proj, apartment="bohaterow")) == 8


@pytest.mark.parametrize("cab_id,expected", [
    ("wc-column", 4), ("wm-wardrobe", 1), ("sink-vanity", 0), ("open-900", 0),
])
def test_shelf_pin_totals_are_four_per_shelf(proj, cab_id, expected):
    cab = proj.cabinet(cab_id)
    shelves = sum(q for p, q in proj.expanded_panels(cab) if p.role == "shelf")
    assert shelves == expected
    pins = {l.hardware: l.quantity for l in bill_of_materials(proj, [cab])}.get("shelf-pin-5", 0)
    assert pins == expected * 4

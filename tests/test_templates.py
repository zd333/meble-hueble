"""`meble scaffold` seeds a new cabinet. It is one-shot, but the carcass maths it seeds is the maths
everything downstream inherits, so a wrong W−2t here becomes a wrong panel in the order.
"""
from __future__ import annotations

import pytest

from meble.model import Cabinet, Panel
from meble.templates import KINDS, scaffold, to_yaml


def panels(cab: dict) -> dict:
    return {p["id"]: p for p in cab["panels"]}


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_scaffolds_and_round_trips_through_the_model(kind):
    cab = scaffold(kind, width=600, height=720, depth=560)
    parsed = Cabinet.from_dict(cab)
    assert parsed.panels
    assert all(isinstance(p, Panel) for p in parsed.panels)
    assert to_yaml(cab).strip()


def test_top_and_bottom_go_between_the_sides():
    """W − 2t. The rule the `carcass-arithmetic` linter exists to defend."""
    cab = panels(scaffold("base", width=600, height=720, depth=560))
    assert cab["bottom"]["width"] == 600 - 2 * 18
    assert cab["top"]["width"] == 600 - 2 * 18


def test_sides_are_depth_by_height():
    cab = panels(scaffold("base", width=600, height=720, depth=560))
    for pid in ("side-l", "side-r"):
        assert (cab[pid]["width"], cab[pid]["height"]) == (560, 720)


def test_sides_are_mirror_parts():
    """Front edge is 2 on the left and 4 on the right — never the same edge."""
    cab = panels(scaffold("base", width=600, height=720, depth=560))
    assert list(cab["side-l"]["edge_banding"]["edges"]) == [2]
    assert list(cab["side-r"]["edge_banding"]["edges"]) == [4]


def test_shelf_pin_columns_are_bulk_holes_on_the_inner_face():
    cab = panels(scaffold("base", width=600, height=720, depth=560))
    pins = cab["side-l"]["holes"]
    assert pins, "expected shelf-pin columns"
    for h in pins:
        assert h["face"] == "inner", "a through Ø5 would show on the outside of a side panel"
        assert h["type"] == "multi" and h["spacing"] == 32 and h["dia"] == 5


def test_pin_columns_use_the_37mm_system32_setback():
    cab = panels(scaffold("base", width=600, height=720, depth=560))
    xs = sorted(h["x"] for h in cab["side-l"]["holes"])
    assert xs == [37, 560 - 37]


def test_back_is_thin_board_not_carcass_board():
    cab = panels(scaffold("base", width=600, height=720, depth=560))
    assert cab["back"]["material"] == "hdf-3"


def test_scaffold_rejects_an_unknown_kind():
    with pytest.raises((KeyError, ValueError)):
        scaffold("spaceship", width=600, height=720, depth=560)

"""The CSV is what gets imported and cut. Every column is locked here.

The import is POSITIONAL and silent: a wrong value in column 3 does not fail, it just produces a
different panel. So these tests assert exact strings, not "looks reasonable".
"""
from __future__ import annotations

import pytest
from conftest import mk_cabinet, mk_panel

from meble.csv_export import _band_mark, _num, _sloje, export_csv
from meble.model import HEIGHT_EDGES, WIDTH_EDGES


def rows(proj, panels, tmp, **cab_kw):
    written = export_csv(proj, [mk_cabinet(panels, **cab_kw)], tmp)
    out = {}
    for p in written:
        lines = [ln for ln in p.read_text(encoding="utf-8").split("\n") if ln.strip()]
        out[p.name] = [ln.rstrip("\r").split(";") for ln in lines[1:]]
    return out


def one_row(proj, panel, tmp):
    got = rows(proj, [panel], tmp)
    assert len(got) == 1
    (only,) = got.values()
    assert len(only) == 1
    return only[0]


# ------------------------------------------------------------------ banding marks

@pytest.mark.parametrize("edges,expected", [
    ({}, ""),
    ({1: "eb-u604-1"}, "-"),
    ({3: "eb-u604-1"}, "-"),
    ({1: "eb-u604-1", 3: "eb-u604-1"}, "="),
    ({2: "eb-u604-1"}, ""),                       # height-axis band, not width
])
def test_width_axis_band_mark(edges, expected):
    banded = {e for e, v in edges.items() if v}
    assert _band_mark(banded, WIDTH_EDGES) == expected


@pytest.mark.parametrize("edges,expected", [
    ({}, ""),
    ({2: "eb-u604-1"}, "-"),
    ({4: "eb-u604-1"}, "-"),
    ({2: "eb-u604-1", 4: "eb-u604-1"}, "="),
    ({1: "eb-u604-1"}, ""),
])
def test_height_axis_band_mark(edges, expected):
    banded = {e for e, v in edges.items() if v}
    assert _band_mark(banded, HEIGHT_EDGES) == expected


def test_all_edges_marks_both_axes():
    assert _band_mark({1, 2, 3, 4}, WIDTH_EDGES) == "="
    assert _band_mark({1, 2, 3, 4}, HEIGHT_EDGES) == "="


def test_width_edges_are_top_and_bottom():
    """Proven against the live editor: `=` in column 3 checks edges 1 and 3."""
    assert WIDTH_EDGES == (1, 3)
    assert HEIGHT_EDGES == (2, 4)


# ------------------------------------------------------------------ grain

@pytest.mark.parametrize("grain,expected", [
    ("any", "0"),
    ("height", "1"),
    ("width", "2"),
    (None, "2"),        # default FORCES orientation so the optimiser cannot rotate the panel
])
def test_sloje_mapping(grain, expected):
    assert _sloje(grain) == expected


# ------------------------------------------------------------------ dimensions

def test_dimensions_are_written_as_whole_millimetres(proj, tmp_path):
    """CLAUDE.md: the CSV writes integers, so a half-mm is silently rounded away in the order."""
    row = one_row(proj, mk_panel(736.4, 1308.6), tmp_path)
    assert row[1] == "736"
    assert row[3] == "1309"


def test_num_rounds_half_away_from_the_nearest_even_trap():
    assert _num(736) == "736"
    assert _num(736.0) == "736"
    assert _num("736") == "736"


def test_thickness_has_two_decimals(proj, tmp_path):
    assert one_row(proj, mk_panel(thickness=18), tmp_path)[5] == "18.00"


def test_quantity_comes_through(proj, tmp_path):
    assert one_row(proj, mk_panel(quantity=3), tmp_path)[6] == "3"


def test_name_is_prefixed_with_the_cabinet_id(proj, tmp_path):
    row = one_row(proj, mk_panel(name="Left side"), tmp_path)
    assert row[0] == "cab Left side"


# ------------------------------------------------------------------ grouping and filtering

def test_one_file_per_board(proj, tmp_path):
    got = rows(proj, [mk_panel(id="a", material="u604-18"),
                      mk_panel(id="b", material="u899-18")], tmp_path)
    assert sorted(got) == ["u604-18.csv", "u899-18.csv"]


def test_non_panel_element_types_are_not_exported(proj, tmp_path):
    """`front` and `countertop` are separate meble.pl products, ordered elsewhere."""
    got = rows(proj, [mk_panel(id="a"), mk_panel(id="f", element_type="front")], tmp_path)
    assert sum(len(v) for v in got.values()) == 1


def test_readymade_cabinets_contribute_nothing(proj, tmp_path):
    from meble.model import Cabinet
    written = export_csv(proj, [Cabinet(id="ikea", kind="readymade")], tmp_path)
    assert written == []


def test_panel_falls_back_to_the_cabinet_default_material(proj, tmp_path):
    p = mk_panel(material=None)
    got = rows(proj, [p], tmp_path, defaults={"material": "u899-18"})
    assert sorted(got) == ["u899-18.csv"]

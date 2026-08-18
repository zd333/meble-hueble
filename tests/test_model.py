"""The loader and the small helpers every exporter leans on."""
from __future__ import annotations

from conftest import mk_hole, mk_panel

from meble.model import EdgeBanding, Hole, Panel


# ------------------------------------------------------------------ edge banding

def test_all_edges_beats_the_explicit_map():
    assert EdgeBanding(all_edges=True).banded_edges() == {1, 2, 3, 4}


def test_falsy_edge_values_are_not_banded():
    """`{1: null}` in YAML means 'listed but not banded' — treating it as banded adds a band."""
    eb = EdgeBanding(edges={1: "eb-u604-1", 2: None, 3: False})
    assert eb.banded_edges() == {1}


def test_edge_keys_are_coerced_to_int():
    """YAML may hand us string keys; edge 1 and edge '1' must not be different edges."""
    eb = EdgeBanding.from_dict({"edges": {"1": "eb-u604-1", 2: "eb-u604-1"}})
    assert eb.banded_edges() == {1, 2}


def test_band_for_prefers_the_per_edge_model_then_the_panel_default():
    eb = EdgeBanding(band="eb-default", edges={1: "eb-special", 2: True})
    assert eb.band_for(1) == "eb-special"
    assert eb.band_for(2) == "eb-default"
    assert eb.band_for(3) is None


# ------------------------------------------------------------------ hole expansion

def test_single_edge_hole_expands_to_one_position():
    assert mk_hole("edge1", frm=100).edge_positions() == [100]


def test_multi_edge_hole_expands_at_its_spacing():
    h = mk_hole("edge1", frm=50, type="multi", count=4, spacing=32)
    assert h.edge_positions() == [50, 82, 114, 146]


def test_multi_surface_hole_expands_along_its_direction():
    x = mk_hole("inner", x=37, y=100, type="multi", count=3, spacing=32, direction="x")
    y = mk_hole("inner", x=37, y=100, type="multi", count=3, spacing=32, direction="y")
    assert x.surface_positions() == [(37, 100), (69, 100), (101, 100)]
    assert y.surface_positions() == [(37, 100), (37, 132), (37, 164)]


def test_surface_hole_without_direction_does_not_advance():
    h = mk_hole("inner", x=37, y=100, type="multi", count=3, spacing=32)
    assert h.surface_positions() == [(37, 100)] * 3


def test_edge_and_surface_faces_are_distinguished():
    assert mk_hole("edge3").is_edge and not mk_hole("edge3").is_surface
    assert mk_hole("edge3").edge_no == 3
    assert mk_hole("outer").is_surface and not mk_hole("outer").is_edge
    assert mk_hole("outer").edge_no is None


# ------------------------------------------------------------------ project

def test_panel_thickness_prefers_the_panel_then_the_board(proj):
    assert proj.panel_thickness(mk_panel(thickness=12)) == 12
    assert proj.panel_thickness(mk_panel(thickness=None, material="u604-18")) == 18


def test_expanded_panels_multiplies_referenced_part_quantities(proj):
    """A part referenced ×2 (a drawer box, say) must order twice its panels, not once."""
    for cab in proj.cabinets.values():
        if cab.kind == "custom" and cab.parts:
            own = {p.id for p in cab.panels}
            extra = [(p, q) for p, q in proj.expanded_panels(cab) if p.id not in own]
            assert extra, f"{cab.id} references parts but contributed no panels"
            break


def test_panel_from_dict_defaults_material_from_the_cabinet():
    p = Panel.from_dict({"id": "x", "width": 100, "height": 100}, "u899-18")
    assert p.material == "u899-18"
    assert p.quantity == 1 and p.element_type == "panel"


def test_hole_from_dict_maps_the_yaml_from_key():
    """YAML says `from`, which is a Python keyword — the dataclass calls it `frm`."""
    assert Hole.from_dict({"face": "edge1", "dia": 8, "from": 120}).frm == 120


def test_real_project_loads_every_cabinet_in_every_set(proj):
    for apt in proj.apartments.values():
        for fs in apt.sets.values():
            for cid in fs.cabinet_ids:
                assert proj.cabinet(cid) is not None, f"{fs.id} references missing cabinet {cid}"

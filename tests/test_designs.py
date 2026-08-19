"""Invariants over the DESIGNS on disk, not over the code.

If one of these fails, a YAML file is wrong, not a function. They encode rules from CLAUDE.md that
no other tool enforces, and they run against whatever is in `apartments/` today.
"""
from __future__ import annotations

from meble.model import HEIGHT_EDGES, WIDTH_EDGES


def test_every_ordered_dimension_is_a_whole_millimetre(real_panels):
    """The CSV writes integers, so a 366.5 would be silently rounded away in the order.
    CLAUDE.md picks envelope numbers specifically to keep every derived size whole."""
    bad = [f"{c.id}/{p.id} {p.width}×{p.height}"
           for c, p, _ in real_panels
           if float(p.width) != int(p.width) or float(p.height) != int(p.height)]
    assert bad == [], f"fractional dimensions would be rounded in the order: {bad}"


def test_every_panel_has_a_positive_size_and_quantity(real_panels):
    for cab, p, qty in real_panels:
        assert p.width > 0 and p.height > 0, f"{cab.id}/{p.id}"
        assert qty >= 1, f"{cab.id}/{p.id}"


def test_every_hole_lies_inside_its_panel(real_panels):
    """Belt and braces over `validate` — this one runs on the real designs unconditionally."""
    for cab, p, _ in real_panels:
        for h in p.holes:
            where = f"{cab.id}/{p.id} {h.face}"
            if h.is_surface:
                for x, y in h.surface_positions():
                    assert 0 <= x <= p.width, f"{where}: x={x} outside 0..{p.width}"
                    assert 0 <= y <= p.height, f"{where}: y={y} outside 0..{p.height}"
            elif h.is_edge:
                length = p.width if h.edge_no in WIDTH_EDGES else p.height
                for pos in h.edge_positions():
                    assert 0 <= pos <= length, f"{where}: {pos} outside 0..{length}"


def test_no_blind_hole_breaks_through(proj, real_panels):
    for cab, p, _ in real_panels:
        t = proj.panel_thickness(p)
        for h in p.holes:
            if h.is_surface and h.depth != "through":
                assert h.depth < t, f"{cab.id}/{p.id}: blind {h.depth} into {t} mm"


def test_grooving_is_empty_everywhere(real_panels):
    """Reserved but unimplemented. The export-time normaliser refuses to transform grooving, so if
    this ever stops being true that code must be written before a design uses it."""
    for cab, p, _ in real_panels:
        assert p.grooving == [], f"{cab.id}/{p.id} has grooving — normalize.py cannot rotate it yet"


def test_every_reference_resolves(proj, real_panels):
    for cab, p, _ in real_panels:
        assert proj.board(p.material), f"{cab.id}/{p.id}: unknown material {p.material}"
        for band in p.edge_banding.edges.values():
            if isinstance(band, str):
                assert proj.edgeband(band), f"{cab.id}/{p.id}: unknown band {band}"


def test_banding_edges_are_1_to_4(real_panels):
    for cab, p, _ in real_panels:
        for edge in p.edge_banding.edges:
            assert edge in (1, 2, 3, 4), f"{cab.id}/{p.id}: edge {edge}"


def test_edge_numbering_covers_both_axes_exactly_once():
    assert set(WIDTH_EDGES) | set(HEIGHT_EDGES) == {1, 2, 3, 4}
    assert not set(WIDTH_EDGES) & set(HEIGHT_EDGES)


def test_left_and_right_sides_are_mirror_parts(proj):
    """Never identical: the front edge is 2 on the left and 4 on the right."""
    for cab in proj.cabinets.values():
        if cab.kind != "custom":
            continue
        by_role: dict = {}
        for p in cab.panels:
            by_role.setdefault(p.role, []).append(p)
        L, R = by_role.get("side-left"), by_role.get("side-right")
        if not (L and R):
            continue
        lb = L[0].edge_banding.banded_edges() & set(HEIGHT_EDGES)
        rb = R[0].edge_banding.banded_edges() & set(HEIGHT_EDGES)
        if lb and rb and lb != {2, 4}:
            assert lb != rb, f"{cab.id}: sides band the same vertical edge {lb}"


# ------------------------------------------------------------------ buyable hardware is declared

def test_every_fitting_buys_something(proj):
    """A fitting with neither `at` nor `quantity` contributes zero to the shopping list, silently."""
    from meble.hardware import fitting_quantity
    for cab in proj.cabinets.values():
        if cab.kind != "custom":
            continue
        for f in cab.fittings:
            assert fitting_quantity(f) >= 1, f"{cab.id}/{f.get('id')}"


def test_every_hinge_declares_its_overlay(proj):
    """The drilling is identical for all three overlays, so this is the ONLY place the difference can
    be recorded — and getting it wrong buys hinges that will not let the door shut."""
    for cab in proj.cabinets.values():
        if cab.kind != "custom":
            continue
        for f in cab.fittings:
            hw = proj.hw(f.get("hardware"))
            if hw and hw.raw.get("type") == "hinge":
                assert f.get("variant"), f"{cab.id}/{f.get('id')} has no variant"
                assert f["variant"] in (hw.raw.get("variants") or {}), f"{cab.id}/{f.get('id')}"


def test_hinge_overlay_matches_what_the_door_lands_on(proj):
    """A door on a shared gable/divider covers only part of it -> half overlay; on an outer side
    panel it covers the whole thickness -> full."""
    expected = {"gable": "half", "divider": "half", "side-left": "full", "side-right": "full"}
    for cab in proj.cabinets.values():
        if cab.kind != "custom":
            continue
        by_id = {p.id: p for p in cab.panels}
        for f in cab.fittings:
            hw = proj.hw(f.get("hardware"))
            if not hw or hw.raw.get("type") != "hinge":
                continue
            mount = by_id.get(f.get("side"))
            want = expected.get(mount.role) if mount else None
            if want:
                assert f.get("variant") == want, \
                    f"{cab.id}/{f['id']} mounts on {mount.id} ({mount.role}) -> expected {want}"


def test_every_shelf_and_drawer_has_its_hardware_declared(proj):
    """Otherwise it is simply absent from the buy list, and nobody notices until assembly."""
    want = {"shelf": "shelf-pin", "drawer-bottom": "slide"}
    for cab in proj.cabinets.values():
        if cab.kind != "custom":
            continue
        served: dict = {}
        for f in cab.fittings:
            hw = proj.hw(f.get("hardware"))
            if not hw:
                continue
            for ref in ("door", "side", "drawer", "through", "into", "shelves"):
                val = f.get(ref)
                for pid in (val if isinstance(val, list) else [val] if val else []):
                    served.setdefault(pid, set()).add(hw.raw.get("type"))
        for p in cab.panels:
            if p.role in want:
                assert want[p.role] in served.get(p.id, set()), \
                    f"{cab.id}/{p.id} ({p.role}) has no {want[p.role]} fitting"


def test_manual_fittings_actually_have_holes(proj):
    """`drilling: manual` claims the holes exist and are tagged. If none reference the fitting,
    either the holes were never drawn or the tag is wrong."""
    for cab in proj.cabinets.values():
        if cab.kind != "custom":
            continue
        srcs = {h.src for p in cab.panels for h in p.holes if h.src}
        for f in cab.fittings:
            if f.get("drilling") == "manual":
                assert f["id"] in srcs, f"{cab.id}/{f['id']}: no hole carries its src"


def test_no_fitting_declares_holes_it_does_not_have(proj):
    for cab in proj.cabinets.values():
        if cab.kind != "custom":
            continue
        srcs = {h.src for p in cab.panels for h in p.holes if h.src}
        for f in cab.fittings:
            if f.get("drilling") == "none":
                assert f["id"] not in srcs, f"{cab.id}/{f['id']}: says no holes but holes reference it"


# ------------------------------------------------------------------ supplier limits

#: meble.pl will CUT a panel longer than this but will not DRILL it (told to us 2026-08-18 while
#: entering the order). A panel over the limit with holes on it cannot be ordered as drawn: either it
#: shrinks, or its holes come off and get drilled by hand.
MAX_DRILLED_LENGTH = 2500


def test_no_drilled_panel_exceeds_the_suppliers_drilling_limit(real_panels):
    over = [f"{c.id}/{p.id} {int(p.width)}×{int(p.height)} ({len(p.holes)} holes)"
            for c, p, _ in real_panels
            if p.holes and max(p.width, p.height) > MAX_DRILLED_LENGTH]
    assert over == [], (
        f"meble.pl will not drill a panel longer than {MAX_DRILLED_LENGTH} mm: {over}")

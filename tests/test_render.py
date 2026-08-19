"""Smoke tests for the two renderers.

Their output is judged by eye, so these do not assert pixels — they assert that every real panel
gets a page, that the fields a person types from are actually on it, and that the 3D scene is
geometrically sane. A renderer that raises, silently drops a panel, or emits NaN is caught here.
"""
from __future__ import annotations

import math

from conftest import pdf_text

from meble.model import cabinets_for_scope
from meble.pdf_export import EDGE_NAMES, export_pdf
from meble.scene import build_scene
from meble.viewer import build_viewer_html


def test_edge_names_match_the_editor():
    """The PDF is typed straight into the editor, whose diagram is labelled 1 top / 2 right /
    3 bottom / 4 left (confirmed from a screenshot of the live editor)."""
    assert EDGE_NAMES == {1: "1 top", 2: "2 right", 3: "3 bottom", 4: "4 left"}


# ------------------------------------------------------------------ PDF

def test_pdf_renders_and_gives_every_panel_a_page(proj, real_panels, tmp_path):
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    text = pdf_text(export_pdf(proj, cabs, tmp_path / "b.pdf", title="t"))
    for cab, panel, _ in real_panels:
        assert panel.name.split("  [")[0][:20] in text, f"missing page for {cab.id}/{panel.id}"


def test_pdf_carries_the_numbers_a_person_types(proj, tmp_path):
    """Size, quantity, banding and drilling all get re-typed by hand; if one is missing from the
    sheet it gets guessed."""
    cab = proj.cabinet("open-900")
    text = pdf_text(export_pdf(proj, [cab], tmp_path / "o.pdf", title="t"))
    assert "864" in text and "600" in text        # bottom panel size
    assert "OUTER" in text and "INNER" in text     # which face the drill enters
    assert "Drilling — surface" in text            # the editor's own section order
    assert "Edge banding" in text                  # which band to fit (not in the CSV)


def test_pdf_page_count_matches_the_csv_row_count(proj, real_panels, tmp_path):
    """One page per ordered panel — the PDF and the CSV must describe the same order."""
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    text = pdf_text(export_pdf(proj, cabs, tmp_path / "b.pdf", title="t"))
    assert text.count("panel sheet P") == len(real_panels) == 44


def test_pdf_handles_a_single_cabinet_scope(proj, tmp_path):
    out = export_pdf(proj, [proj.cabinet("open-900")], tmp_path / "one.pdf", title="t")
    assert out.exists() and out.stat().st_size > 1000


# ------------------------------------------------------------------ 3D scene

def test_scene_builds_for_the_whole_apartment(proj):
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    scene = build_scene(proj, cabs, name="bohaterow")
    assert scene["objects"], "no objects in the scene"


def test_scene_geometry_is_finite_and_positive(proj):
    """A NaN or a zero-sized box renders as nothing at all, which reads as 'panel missing'."""
    scene = build_scene(proj, cabinets_for_scope(proj, apartment="bohaterow"), name="b")
    for obj in scene["objects"]:
        for key in ("size", "pos"):
            for v in obj.get(key, []):
                assert isinstance(v, (int, float)) and math.isfinite(v), f"{obj.get('id')}: {key}={v}"
        for v in obj.get("size", []):
            assert v > 0, f"{obj.get('id')}: zero-sized"


def test_viewer_html_is_self_contained(proj, root):
    scene = build_scene(proj, [proj.cabinet("open-900")], name="open-900")
    html = build_viewer_html(scene, root / "viewer" / "template.html")
    assert "<html" in html.lower()
    assert "open-900" in html


# ------------------------------------------------------------------ sheet layout matches the editor

def test_surface_drilling_comes_before_edge_drilling(proj, tmp_path):
    """The editor presents surface first; a sheet in the other order makes you hunt up and down."""
    text = pdf_text(export_pdf(proj, [proj.cabinet("wm-wardrobe")], tmp_path / "o.pdf", title="t"))
    page = next(p for p in text.split("\f") if "Drilling — surface" in p)
    assert page.index("Drilling — surface") < page.index("Drilling — edge")


def test_hole_rows_are_numbered_from_one_in_each_section(proj, tmp_path):
    text = pdf_text(export_pdf(proj, [proj.cabinet("wc-column")], tmp_path / "o.pdf", title="t"))
    page = next(p for p in text.split("\f") if "Drilling — surface" in p and "Drilling — edge" in p)
    surf, edge = page.split("Drilling — edge")
    for section in (surf.split("Drilling — surface")[1], edge):
        rows = [ln for ln in section.splitlines()
                if ln.strip() and ln.split()[0].isdigit()]
        if rows:
            assert [int(r.split()[0]) for r in rows] == list(range(1, len(rows) + 1))


def test_the_per_edge_banding_table_is_gone_but_the_band_survives(proj, tmp_path):
    """Which edges are banded is on the diagram and in the CSV. WHICH BAND is in neither — the CSV
    carries no model or thickness, and the editor defaults to 0.8 mm while the fronts need 2 mm."""
    text = pdf_text(export_pdf(proj, [proj.cabinet("wc-column")], tmp_path / "o.pdf", title="t"))
    page = next(p for p in text.split("\f") if "Front cover" in p and "Edge banding" in p)
    assert "band model" not in page, "the four-row banding table is still there"
    assert "2 mm" in page, "the 2 mm band thickness must survive — it is order-critical"


def test_no_surface_row_offers_a_run_the_editor_would_reject(proj, tmp_path):
    """A surface `multi ×N @ Xmm` over the limit cannot be typed in at all. Edge rows are exempt —
    that group has no spacing limit, so splitting them would only add work."""
    import re
    from meble.normalize import MAX_SURFACE_MULTI_SPACING
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    text = pdf_text(export_pdf(proj, cabs, tmp_path / "b.pdf", title="t"))
    for page in text.split("\f"):
        if "Drilling — surface" not in page:
            continue
        surface = page.split("Drilling — surface")[1].split("Drilling — edge")[0]
        wide = [int(m) for m in re.findall(r"multi ×\d+ @ (\d+)mm", surface)
                if int(m) > MAX_SURFACE_MULTI_SPACING]
        assert wide == [], f"surface rows offer runs the editor rejects: {sorted(set(wide))}"

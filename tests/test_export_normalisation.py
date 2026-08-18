"""The normaliser as the exporters use it.

The single most important property is that the CSV and the PDF agree. They are read together: the
CSV creates the panel, the PDF is what gets typed into it. If only one of them rotated, the banding
would sit at one end and the drilling at the other, and the result would be scrap that looks fine
on paper.
"""
from __future__ import annotations

from conftest import pdf_text
from reportlab.pdfbase import pdfmetrics

from meble.csv_export import export_csv
from meble.model import cabinets_for_scope
from meble.normalize import normalize, unexpressible_edges
from meble.pdf_export import MARGIN, PW, ROTATED_BANNER, export_pdf


def test_no_real_panel_needs_a_by_hand_banding_fix(proj, capsys, tmp_path):
    """The user's original complaint, gone: after normalising nothing is left for them to tick."""
    export_csv(proj, cabinets_for_scope(proj, apartment="bohaterow"), tmp_path)
    assert "TICK EDGE" not in capsys.readouterr().out


def test_every_exported_panel_bands_an_edge_the_import_can_actually_set(proj, real_panels):
    for cab, panel, _ in real_panels:
        out, _ = normalize(panel)
        assert unexpressible_edges(out.edge_banding.banded_edges()) == [], f"{cab.id}/{panel.id}"


def _data_columns(paths):
    """Every CSV column except the free-text name — i.e. everything that affects the cut."""
    out = {}
    for p in paths:
        rows = [l.rstrip("\r") for l in p.read_text(encoding="utf-8").split("\n") if l.strip()]
        out[p.name] = [r.split(";")[1:] for r in rows[1:]]
    return out


def test_normalising_changes_nothing_that_gets_cut(proj, tmp_path):
    """A `-` is a `-` whichever end the band is on — the CSV literally cannot tell the difference.

    Worth stating explicitly, because it is the reassuring half of the fix: dimensions, banding
    marks, thickness, quantity and grain are all untouched. What the rotation changes is the PDF —
    the band the importer *will* apply becomes the one the design wants, and the drilling moves to
    match. The only CSV difference is the by-hand warning in the name column, which normalising
    removes because there is no longer anything to warn about.
    """
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    on = _data_columns(export_csv(proj, cabs, tmp_path / "on"))
    off = _data_columns(export_csv(proj, cabs, tmp_path / "off", normalise=False))
    assert on == off


def test_pdf_marks_exactly_the_rotated_panels(proj, real_panels, tmp_path):
    expected = sum(1 for _, p, _ in real_panels if normalize(p)[1])
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    text = pdf_text(export_pdf(proj, cabs, tmp_path / "b.pdf", title="t"))
    assert text.count("SHOWN ROTATED") == expected == 16


def test_no_rotation_banner_when_normalisation_is_off(proj, tmp_path):
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    text = pdf_text(export_pdf(proj, cabs, tmp_path / "b.pdf", title="t", normalise=False))
    assert "SHOWN ROTATED" not in text


def test_the_banner_fits_inside_the_text_column():
    """reportlab does not wrap. A warning that runs off the edge of the paper is not a warning."""
    usable = PW - 2 * MARGIN
    for line in ROTATED_BANNER:
        width = pdfmetrics.stringWidth(line, "Helvetica-Bold", 7.5)
        assert width <= usable, f"{width:.0f}pt > {usable:.0f}pt: {line!r}"


def test_pdf_and_csv_describe_the_same_orientation(proj, tmp_path):
    """Spot-check the panel that motivated the whole change.

    `wc-column Centre gable` is 181×1297 and bands edge 2 (its front edge). Edge 2 alone cannot be
    imported, so it exports rotated: the band moves to edge 4, and its holes must move with it.
    """
    cab = proj.cabinet("wc-column")
    panel = next(p for p in cab.panels if p.id == "gable-mid")
    out, rotated = normalize(panel)
    assert rotated is True
    assert panel.edge_banding.banded_edges() == {2}
    assert out.edge_banding.banded_edges() == {4}

    text = pdf_text(export_pdf(proj, [cab], tmp_path / "wc.pdf", title="t"))
    page = next(p for p in text.split("\f") if "Centre gable" in p and "Drilling" in p)
    assert "SHOWN ROTATED" in page
    assert "4 left" in page and "yes" in page


def test_a_panel_that_was_already_expressible_is_untouched_in_the_pdf(proj, tmp_path):
    """`wm-wardrobe Back` bands 1+3 (`=`), which is exact — it must NOT be rotated."""
    cab = proj.cabinet("wm-wardrobe")
    panel = next(p for p in cab.panels if p.id == "back")
    out, rotated = normalize(panel)
    assert rotated is False and out is panel
    text = pdf_text(export_pdf(proj, [cab], tmp_path / "wm.pdf", title="t"))
    page = next(p for p in text.split("\f") if "Back (full height)" in p and "Drilling" in p)
    assert "SHOWN ROTATED" not in page

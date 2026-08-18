"""Snapshot the real project's exports.

These are the highest-value tests in the repo: they are the only thing standing between an
accidental behaviour change and a wrong order. When one fails, the question is never "how do I make
it pass" — it is "did I mean to change what gets cut?".

To adopt a deliberate change:  .venv/bin/python tests/regen_golden.py   then READ the diff.
"""
from __future__ import annotations

from pathlib import Path

from conftest import pdf_text, read_golden

from meble.csv_export import export_csv
from meble.model import cabinets_for_scope
from meble.pdf_export import export_pdf


def _export_csvs(proj, tmp: Path) -> dict[str, str]:
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    return {p.name: p.read_text(encoding="utf-8") for p in export_csv(proj, cabs, tmp)}


def test_csv_matches_golden(proj, tmp_path):
    got = _export_csvs(proj, tmp_path)
    assert sorted(got) == ["u604-18.csv", "u899-18.csv"], "board grouping changed"
    for name, text in got.items():
        assert text == read_golden(name), f"{name} changed — is the new output what you want ordered?"


def test_pdf_text_matches_golden(proj, tmp_path):
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    pdf = export_pdf(proj, cabs, tmp_path / "b.pdf", title="Panele — bohaterow")
    assert pdf_text(pdf) == read_golden("bohaterow.pdf.txt")


def test_pdf_is_deterministic_apart_from_its_timestamp(proj, tmp_path):
    """Two runs over an unchanged design differ only in the embedded creation date.

    This is what licenses the text-based golden above, and what let us prove the user's printed
    copy was still current.
    """
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    a = export_pdf(proj, cabs, tmp_path / "a.pdf", title="t").read_bytes()
    b = export_pdf(proj, cabs, tmp_path / "b.pdf", title="t").read_bytes()
    assert len(a) == len(b)
    differing = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    # only the /CreationDate + /ModDate strings and the doc-id hash derived from them
    assert len(differing) < 200, f"{len(differing)} bytes differ — PDF gained a new source of nondeterminism"


def test_csv_is_semicolon_separated_with_crlf_and_trailing_separator(proj, tmp_path):
    """The importer is positional; a lost column or line ending silently shifts every field."""
    for text in _export_csvs(proj, tmp_path).values():
        raw = text
        assert raw.startswith("Nazwa (nie wpływa na rozkrój);")
        lines = [ln for ln in raw.split("\n") if ln.strip()]
        for ln in lines:
            assert ln.endswith(";\r") or ln.endswith(";"), f"row lost its trailing ';': {ln!r}"
        for ln in lines[1:]:
            assert len(ln.rstrip("\r").split(";")) == 9, f"row has wrong column count: {ln!r}"


def test_hardware_matches_golden(proj):
    """What you buy is as order-critical as what you cut. A design change that moves the shopping
    list must show up as a reviewable diff, not as a surprise at the counter."""
    from regen_golden import render_bom
    cabs = cabinets_for_scope(proj, apartment="bohaterow")
    assert render_bom(proj, cabs) == read_golden("hardware.txt")

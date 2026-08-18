"""Regenerate the golden snapshots in tests/golden/.

    .venv/bin/python tests/regen_golden.py

Run this ONLY when you have deliberately changed export behaviour, and then **read the diff** —
these files are the record of what actually gets ordered. A golden updated without reading it is
worse than no golden at all.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from meble.csv_export import export_csv          # noqa: E402
from meble.model import cabinets_for_scope, load_project  # noqa: E402
from meble.pdf_export import export_pdf          # noqa: E402

GOLDEN = Path(__file__).parent / "golden"


def main() -> int:
    GOLDEN.mkdir(exist_ok=True)
    proj = load_project(ROOT)
    cabs = cabinets_for_scope(proj, apartment="bohaterow")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for path in export_csv(proj, cabs, tmp / "csv"):
            dest = GOLDEN / path.name
            dest.write_bytes(path.read_bytes())
            print(f"  {dest.relative_to(ROOT)}")

        pdf = export_pdf(proj, cabs, tmp / "bohaterow.pdf", title="Panele — bohaterow")
        res = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                             capture_output=True, text=True)
        if res.returncode != 0:
            print("  ! pdftotext unavailable — PDF golden not written", file=sys.stderr)
        else:
            dest = GOLDEN / "bohaterow.pdf.txt"
            dest.write_text(res.stdout, encoding="utf-8")
            print(f"  {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

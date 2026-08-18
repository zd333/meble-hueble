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
from meble.hardware import (bill_of_materials, collared_pins,  # noqa: E402
                            resolve_sourcing)
from meble.model import cabinets_for_scope, load_project  # noqa: E402
from meble.pdf_export import export_pdf          # noqa: E402

GOLDEN = Path(__file__).parent / "golden"


def render_bom(proj, cabs) -> str:
    """The shopping list as stable text. A design change that moves what you buy shows up as a diff
    here — which is the point: the buy list is as order-critical as the panel list."""
    out = []
    for line in bill_of_materials(proj, cabs):
        where = " ".join(f"{k}={v}" for k, v in sorted(line.per_cabinet.items()))
        out.append(f"{line.hardware:16} {line.variant or '-':6} {line.quantity:>4} "
                   f"{line.sold_as:6} {where}")
    out.append(f"{'collared-pins':16} {'-':6} {collared_pins(proj, cabs):>4}")
    # SKUs and prices too: a supplier change is as order-critical as a quantity change, and it should
    # never land without somebody reading the diff.
    out.append("")
    out.append("-- sourcing (centrum.meble.pl) --")
    for line in bill_of_materials(proj, cabs):
        buys, missing = resolve_sourcing(proj, line, vendor="centrum.meble.pl")
        for b in buys:
            price = f"{b.price:.2f}" if b.price is not None else "-"
            out.append(f"{line.hardware:16} {line.variant or '-':6} {b.component:8} "
                       f"{b.sku:10} {price:>7} {b.checked}")
        for m in missing:
            out.append(f"{line.hardware:16} {line.variant or '-':6} NO SUPPLIER RECORDED")
    return "\n".join(out) + "\n"


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

        dest = GOLDEN / "hardware.txt"
        dest.write_text(render_bom(proj, cabs), encoding="utf-8")
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

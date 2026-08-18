"""Shared fixtures.

Two kinds of test live here, and they are deliberately different:

  * **synthetic** — hand-built `Panel`/`Hole` objects that never touch disk. Use these for rules and
    transforms, so a test failure names the rule and not the design that happened to trip it.
  * **the real project** — the actual YAML under `apartments/`. Use these for goldens and for
    invariants that are about *these designs*, not about the code.

The panels in this repo get ordered and cut; a silently wrong export costs a sheet of MFC and a
re-order. That is why the goldens exist.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from meble.model import Cabinet, EdgeBanding, Hole, Panel, load_project  # noqa: E402

GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def proj():
    """The real project, loaded once."""
    return load_project(ROOT)


@pytest.fixture(scope="session")
def real_panels(proj):
    """(cabinet, panel, qty) for every ordered panel in the real project."""
    out = []
    for cab in proj.cabinets.values():
        if cab.kind != "custom":
            continue
        for panel, qty in proj.expanded_panels(cab):
            if panel.element_type == "panel":
                out.append((cab, panel, qty))
    return out


# ------------------------------------------------------------------ synthetic builders

def mk_panel(width: float = 600, height: float = 400, *, id="p", name=None, edges=None,
             all_edges=False, holes=(), grain: Any = None, material: Any = "u604-18",
             thickness: Any = 18, quantity=1, role="", element_type="panel") -> Panel:
    """A panel with just enough filled in to exercise one rule.

    `edges` is the plain {edge_no: band_id} mapping the YAML uses.
    """
    return Panel(
        id=id, name=name if name is not None else id, element_type=element_type, role=role,
        material=material, width=width, height=height, thickness=thickness, quantity=quantity,
        grain=grain,
        edge_banding=EdgeBanding(all_edges=all_edges, band="eb-u604-1",
                                 edges=dict(edges or {}), glue_type="long"),
        holes=list(holes),
    )


def mk_hole(face="outer", *, dia=8, depth: Any = 13, type="single", frm=None, x=None, y=None,
            count=None, spacing=None, direction=None, src=None) -> Hole:
    return Hole(face=face, dia=dia, depth=depth, type=type, frm=frm, x=x, y=y,
                count=count, spacing=spacing, direction=direction, src=src)


def mk_cabinet(panels, *, id="cab", name="Cab", defaults=None, fittings=()) -> Cabinet:
    return Cabinet(id=id, name=name, panels=list(panels), fittings=list(fittings),
                   defaults=dict(defaults or {"material": "u604-18"}))


# ------------------------------------------------------------------ golden helpers

def read_golden(name: str) -> str:
    path = GOLDEN / name
    if not path.exists():
        pytest.fail(f"missing golden {path}. Regenerate with tests/regen_golden.py and review the diff.")
    return path.read_text(encoding="utf-8")


def pdf_text(path: Path) -> str:
    """Text of a PDF. Text, not bytes: the PDF embeds a creation timestamp, which is the ONLY
    thing that differs between two runs over an unchanged design (verified 2026-08-17)."""
    res = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                         capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip("pdftotext not available")
    return res.stdout

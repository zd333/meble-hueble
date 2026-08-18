"""Export the panel list to the centrum.meble.pl PRO100 CSV (dimensions + grain + coarse banding).

One CSV per board model (the editor groups panels under a board). The rich per-edge banding, band
model, drilling and grooving are entered manually from the PDF spec sheet — the CSV carries only what
the import accepts. We never produce a cutting layout (meble.pl owns nesting).

Banding is written through `normalize`: the import can only ever put a single band on edge 3 or
edge 4, so a panel banding edge 1 or 2 alone is exported turned 180°, which says the same thing in a
frame the importer can express. See normalize.py for the measurement behind that. The PDF applies
the SAME transform, so the sheet you type from matches the panel the CSV created.
"""
from __future__ import annotations

from pathlib import Path

from .model import Cabinet, Project, WIDTH_EDGES, HEIGHT_EDGES
from .normalize import normalize, unexpressible_edges

HEADER = (
    "Nazwa (nie wpływa na rozkrój);Szerokość;Oklejanie szerokości;Wysokość;Oklejanie wysokości;"
    "Grubość płyty;Ilość sztuk;"
    "Słoje [0 = bez znaczenia / 1 = po drugim wymiarze (po wysokości) / "
    "2 lub puste = po pierwszym wymiarze (po szerokości)];"
)


def _band_mark(banded: set, axis_edges: tuple) -> str:
    n = sum(1 for e in axis_edges if e in banded)
    return {2: "=", 1: "-", 0: ""}[n]


def _sloje(grain) -> str:
    # default (None) forces orientation along the width = "2" so panels are never rotated
    return {"any": "0", "height": "1", "width": "2", None: "2"}.get(grain, "2")


def _num(v) -> str:
    return str(int(round(float(v))))


def _flag(name: str, edges: list[int]) -> str:
    """Warn, in the one field that reaches the editor's UI, about banding the CSV could not set.

    Only reachable for a panel whose two axes want opposite things (edge 1 with edge 4, say), which
    no rotation can fix. Better an obviously missing band the user adds in one click than a
    plausible-looking band on the wrong edge, which produces a finished panel that is scrap.
    """
    if not edges:
        return name
    return f"{name}  /!\\ TICK EDGE {'+'.join(map(str, edges))} BY HAND (CSV cannot set it)"


def export_csv(proj: Project, cabinets: list[Cabinet], outdir: Path,
               normalise: bool = True) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    # board id -> list of CSV row strings
    rows_by_board: dict[str, list[str]] = {}
    manual: list[tuple[str, str, list[int]]] = []

    for cab in cabinets:
        if cab.kind != "custom":
            continue
        for panel, qty in proj.expanded_panels(cab):
            if panel.element_type != "panel":      # fronts/countertops export elsewhere (later)
                continue
            board_id = panel.material or cab.defaults.get("material") or "unknown"
            thickness = proj.panel_thickness(panel)
            if normalise:
                panel, _ = normalize(panel)
            banded = panel.edge_banding.banded_edges()
            todo = unexpressible_edges(banded)
            if todo:
                manual.append((cab.id, panel.name, todo))
            name = _flag(f"{cab.id} {panel.name}".strip(), todo)
            row = ";".join([
                name,
                _num(panel.width),
                _band_mark(banded, WIDTH_EDGES),
                _num(panel.height),
                _band_mark(banded, HEIGHT_EDGES),
                f"{float(thickness):.2f}",
                str(qty),
                _sloje(panel.grain),
            ]) + ";"
            rows_by_board.setdefault(board_id, []).append(row)

    written: list[Path] = []
    for board_id, rows in sorted(rows_by_board.items()):
        path = outdir / f"{board_id}.csv"
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(HEADER + "\n")
            for r in rows:
                f.write(r + "\n")
        written.append(path)

    if manual:
        print(f"\n  /!\\ {len(manual)} panel(s) band one edge the import cannot address, and cannot be "
              f"rotated onto one it can (their two axes want opposite ends). They import UNBANDED on "
              f"that axis — tick it by hand; each row's Nazwa says which:")
        for cab_id, pname, edges in manual:
            print(f"        {cab_id}/{pname} -> edge {'+'.join(map(str, edges))}")
    return written

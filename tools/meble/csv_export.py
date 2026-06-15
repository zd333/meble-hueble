"""Export the panel list to the centrum.meble.pl PRO100 CSV (dimensions + grain + coarse banding).

One CSV per board model (the editor groups panels under a board). The rich per-edge banding, band
model, drilling and grooving are entered manually from the PDF spec sheet — the CSV carries only what
the import accepts. We never produce a cutting layout (meble.pl owns nesting).
"""
from __future__ import annotations

from pathlib import Path

from .model import Cabinet, Project, WIDTH_EDGES, HEIGHT_EDGES

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


def export_csv(proj: Project, cabinets: list[Cabinet], outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    # board id -> list of CSV row strings
    rows_by_board: dict[str, list[str]] = {}

    for cab in cabinets:
        if cab.kind != "custom":
            continue
        for panel, qty in proj.expanded_panels(cab):
            if panel.element_type != "panel":      # fronts/countertops export elsewhere (later)
                continue
            board_id = panel.material or cab.defaults.get("material") or "unknown"
            thickness = proj.panel_thickness(panel)
            banded = panel.edge_banding.banded_edges()
            name = f"{cab.id} {panel.name}".strip()
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
    return written

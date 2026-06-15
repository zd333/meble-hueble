"""Static consistency checks. No regeneration safety-net exists (panels are the source of truth), so
this is where we catch broken refs, out-of-bounds holes, illegal value sets, and orphaned stamps.
"""
from __future__ import annotations

from .model import Cabinet, Hole, Panel, Project

EDGE_DIA = {4, 8}
SURFACE_DIA = {3, 5, 8, 10, 15, 20, 35}


def _edge_length(panel: Panel, edge: int) -> float:
    return panel.width if edge in (1, 3) else panel.height


def _check_hole(panel: Panel, h: Hole, err, warn, where: str) -> None:
    if h.is_edge:
        e = h.edge_no
        if e not in (1, 2, 3, 4):
            err(f"{where}: bad edge '{h.face}'"); return
        if h.dia not in EDGE_DIA:
            err(f"{where}: edge bore Ø{h.dia} not in {sorted(EDGE_DIA)}")
        if not (isinstance(h.depth, (int, float)) and 2 <= h.depth <= 35):
            err(f"{where}: edge depth {h.depth} out of 2..35")
        length = _edge_length(panel, e)
        last = (h.frm or 0) + ((h.count - 1) * h.spacing if h.type == "multi" and h.count and h.spacing else 0)
        if h.frm is None or h.frm < 0 or last > length:
            err(f"{where}: edge hole at {h.frm} (..{last}) outside edge length {length}")
        if h.type == "multi" and (not h.count or not h.spacing):
            err(f"{where}: multi edge hole needs count + spacing")
    elif h.is_surface:
        if h.dia not in SURFACE_DIA:
            err(f"{where}: surface bore Ø{h.dia} not in {sorted(SURFACE_DIA)}")
        if h.depth != "through" and not (isinstance(h.depth, (int, float)) and 2 <= h.depth <= 15):
            err(f"{where}: surface depth {h.depth} must be 2..15 or 'through'")
        x, y = h.x or 0, h.y or 0
        ext_x = x + ((h.count - 1) * h.spacing if h.type == "multi" and h.direction == "x" and h.count and h.spacing else 0)
        ext_y = y + ((h.count - 1) * h.spacing if h.type == "multi" and h.direction == "y" and h.count and h.spacing else 0)
        if x < 0 or y < 0 or ext_x > panel.width or ext_y > panel.height:
            err(f"{where}: surface hole ({x},{y})..({ext_x},{ext_y}) outside panel {panel.width}×{panel.height}")
        if h.type == "multi" and (not h.count or not h.spacing or h.direction not in ("x", "y")):
            err(f"{where}: multi surface hole needs count + spacing + direction(x|y)")
    else:
        err(f"{where}: bad face '{h.face}' (expected edge1..4 | front | back)")


def validate_cabinet(proj: Project, cab: Cabinet, err, warn) -> None:
    if cab.kind == "readymade":
        dims = cab.raw.get("dimensions") or {}
        if not all(dims.get(k, 0) > 0 for k in ("width", "depth", "height")):
            err(f"cabinet '{cab.id}': readymade needs positive width/depth/height (actual mm)")
        return

    panel_ids = {p.id for p in cab.panels}
    fitting_ids = {f.get("id") for f in cab.fittings}

    for p in cab.panels:
        w = f"cabinet '{cab.id}' panel '{p.id}'"
        if not (p.width > 0 and p.height > 0):
            err(f"{w}: width/height must be > 0")
        if p.material and not proj.board(p.material):
            err(f"{w}: material '{p.material}' not in library/materials.yaml")
        if not p.material:
            err(f"{w}: no material (and cabinet has no defaults.material)")
        for edge, band in p.edge_banding.edges.items():
            if edge not in (1, 2, 3, 4):
                err(f"{w}: banding edge '{edge}' must be 1..4")
            if isinstance(band, str) and not proj.edgeband(band):
                err(f"{w}: edge band '{band}' not in library/edgebands.yaml")
        for i, h in enumerate(p.holes):
            _check_hole(p, h, err, warn, f"{w} hole #{i}")
            if h.src and h.src not in fitting_ids:
                warn(f"{w} hole #{i}: src '{h.src}' has no matching fitting (orphan stamp)")

    for f in cab.fittings:
        w = f"cabinet '{cab.id}' fitting '{f.get('id')}'"
        if f.get("hardware") and not proj.hw(f["hardware"]):
            err(f"{w}: hardware '{f.get('hardware')}' not in library/hardware.yaml")
        for ref in ("through", "into"):
            if f.get(ref) and f[ref] not in panel_ids:
                err(f"{w}: {ref} panel '{f[ref]}' not found")
        seam = f.get("seam") or {}
        for k in ("through_edge", "into_edge"):
            if k in seam and seam[k] not in (1, 2, 3, 4):
                err(f"{w}: seam.{k} must be 1..4")


def validate(proj: Project, cabinets: list[Cabinet]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for cab in cabinets:
        validate_cabinet(proj, cab, errors.append, warnings.append)
    return errors, warnings

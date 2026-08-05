"""Resolve a set/cabinet scope into a flat JSON scene of boxes for the interactive 3D viewer.

VIZ-ONLY (placement is never order-relevant). Custom panels are laid out from their `role` + the cabinet
envelope; an explicit `panel.placement` overrides. Readymade units render as a single box. Each object
also carries identity (cabinet/panel/role), its cut size, and material name so the viewer can label,
isolate, and explode panels. Output is mm; the viewer renders these directly. No Blender.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .model import BAND_COLOR_DEFAULT, Cabinet, Panel, Project, band_color_map, dia_color

DEFAULT_COLOR = [0.85, 0.85, 0.83]

# ---------------------------------------------------------------------------- panel orientation
#
# To draw a drill hole we need more than the panel's bounding box: we need which way its local frame
# points. A panel's local axes are u = width, v = height, w = thickness, with **w = u × v pointing out
# of the OUTER face** (docs/conventions.md defines the x,y frame as seen from the outer face, so local
# w runs 0 = inner surface -> t = outer surface).
#
# Below, u and v are given per role in the CABINET frame: X = width (left -> right), Y = depth
# (0 = FRONT, D = wall), Z = height (0 = floor). Taken from docs/conventions.md plus the joinery in the
# d60-base worked example, which pins down the horizontals: a top/bottom panel's edge 4 is the cabinet
# LEFT (cf-*-l joins into_edge 4) and its edge 1 is the FRONT.
#
# CONSEQUENCE WORTH KNOWING: for a horizontal, edge4 = left and edge1 = front force w to point DOWN.
# So on a `bottom` panel `outer` is the down face (as conventions.md says) — but on a `top` panel
# `inner` is the UP face and `outer` the DOWN face, which is the opposite of what that table's `top`
# row implies. The two can't both hold in a right-handed frame; the joinery wins.
ROLE_FRAME = {
    "side-left":  ((0, -1, 0), (0, 0, 1)),    # outer faces left; +u = toward the front (edge 2)
    "side-right": ((0, 1, 0), (0, 0, 1)),     # mirror: outer faces right; edge 4 is the front
    "bottom":     ((1, 0, 0), (0, -1, 0)),    # +u = right (edge 4 = left), +v = toward the front
    "top":        ((1, 0, 0), (0, -1, 0)),
    "shelf":      ((1, 0, 0), (0, -1, 0)),
    "divider":    ((1, 0, 0), (0, -1, 0)),
    "back":       ((-1, 0, 0), (0, 0, 1)),    # outer faces the wall
    "front":      ((1, 0, 0), (0, 0, 1)),     # door / applied front: outer faces the room
}


def _cross(a, b) -> tuple:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _rot_matrix(rot) -> list:
    """Rotation matrix (columns = where the local axes land) from `placement.rot` Euler degrees."""
    if not rot or all(abs(float(a)) < 1e-6 for a in rot):
        return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    rx, ry, rz = (math.radians(float(a)) for a in rot)
    cx, sx, cy, sy, cz, sz = (math.cos(rx), math.sin(rx), math.cos(ry),
                              math.sin(ry), math.cos(rz), math.sin(rz))
    return [[cy * cz, cz * sx * sy - cx * sz, cx * cz * sy + sx * sz],
            [cy * sz, cx * cz + sx * sy * sz, cx * sy * sz - cz * sx],
            [-sy,     cy * sx,                cx * cy]]


def _panel_matrix(panel: Panel) -> list:
    """Local->world axis matrix: explicit `placement.rot` wins, else the panel's role, else identity."""
    if panel.placement.get("rot"):
        return _rot_matrix(panel.placement["rot"])
    uv = ROLE_FRAME.get(panel.role)
    if uv:
        u, v = uv
        w = _cross(u, v)
        return [[u[i], v[i], w[i]] for i in range(3)]
    return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def _rot_size(size, rot) -> tuple:
    """Map a panel's local (width, height, thickness) onto world (x, y, z) extents through `rot`.

    `placement.rot` is Euler degrees (schema.md). For a box only axis-aligned rotations are meaningful,
    so we take |R| and read off which world axis each local axis ends up along. Absent or zero rot is the
    identity — the panel keeps width->X, height->Y, thickness->Z, as before.
    """
    r = _rot_matrix(rot)
    return tuple(sum(abs(r[i][j]) * size[j] for j in range(3)) for i in range(3))


def _local_origin(r: list, extents: tuple, aabb_min: tuple) -> tuple:
    """World position of the panel's local (0,0,0) corner, given its drawn world AABB minimum.

    world_i(L) = origin_i + Σ_j r[i][j]·L_j for L in the local box, so the AABB minimum sits at
    origin_i − Σ_j max(0, −r[i][j])·extents_j. Invert that.
    """
    return tuple(aabb_min[i] + sum(max(0.0, -r[i][j]) * extents[j] for j in range(3))
                 for i in range(3))


def _to_world(r: list, origin: tuple, local: tuple) -> tuple:
    return tuple(origin[i] + sum(r[i][j] * local[j] for j in range(3)) for i in range(3))


def _dir_world(r: list, local_dir: tuple) -> tuple:
    return tuple(sum(r[i][j] * local_dir[j] for j in range(3)) for i in range(3))


def _hole_instances(panel: Panel, t: float) -> list:
    """Every drilled hole of a panel as (local_start, local_dir, depth, hole) in the panel's frame.

    Local frame: u = 0..width, v = 0..height, w = 0 (inner surface) .. t (outer surface). A surface hole
    starts on its face and is drilled inward; an edge hole starts on that edge, centred in the thickness
    (the editor has no across-thickness parameter for edge drilling), and is drilled inward.
    """
    out = []
    for h in panel.holes:
        through = h.depth == "through"
        depth = float(t) if through else float(h.depth or 0)
        if h.is_surface:
            start_w, dw = (t, -1.0) if h.face == "outer" else (0.0, 1.0)
            for (x, y) in h.surface_positions():
                out.append(((x, y, start_w), (0.0, 0.0, dw), depth, h))
        elif h.is_edge:
            e = h.edge_no
            for p in h.edge_positions():
                if e == 1:
                    start, d = (p, panel.height, t / 2), (0.0, -1.0, 0.0)
                elif e == 3:
                    start, d = (p, 0.0, t / 2), (0.0, 1.0, 0.0)
                elif e == 2:
                    start, d = (panel.width, p, t / 2), (-1.0, 0.0, 0.0)
                else:
                    start, d = (0.0, p, t / 2), (1.0, 0.0, 0.0)
                out.append((start, d, depth, h))
    return out


_BAND_EPS = 0.15   # nudge the band's visible face clear of the panel's own face (stops z-fighting)


def _panel_bands(proj: Project, panel: Panel, t: float, size: tuple, center: tuple,
                 cab_id: str, colors: dict, owner: str | None = None) -> list:
    """World-space edge-band strips for one panel, for the viewer to draw as thin boxes.

    Panel dimensions are FINISHED sizes (band included — see CLAUDE.md), so a strip lies *inside* the
    panel footprint: its visible face is flush with the panel's edge and its thickness runs inward.
    `glue_type` is honoured: with `long` (default, "kryjące długie") the band on the panel's long edges
    runs the full length and the short edges butt into it — which is also what keeps the corners from
    overlapping in the render.
    """
    eb = panel.edge_banding
    banded = eb.banded_edges()
    if not banded:
        return []
    owner = owner or f"{cab_id}/{panel.id}"

    def band_thickness(e: int) -> float:
        if e not in banded:
            return 0.0
        bid = eb.band_for(e)
        b = proj.edgeband(bid) if bid else None
        return float(b.thickness) if b else 1.0

    long_edges = {2, 4} if panel.height >= panel.width else {1, 3}
    covering = long_edges if eb.glue_type != "short" else ({1, 2, 3, 4} - long_edges)

    r = _panel_matrix(panel)
    aabb_min = tuple(center[i] - size[i] / 2 for i in range(3))
    origin = _local_origin(r, (panel.width, panel.height, t), aabb_min)

    recs = []
    for e in sorted(banded):
        b = band_thickness(e)
        if b <= 0:
            continue
        # `along_i` = local axis the strip runs along; the other in-plane axis carries its thickness
        along_i = 0 if e in (1, 3) else 1
        run = panel.width if e in (1, 3) else panel.height
        perp_lo, perp_hi = (4, 2) if e in (1, 3) else (3, 1)
        s0 = 0.0 if e in covering else band_thickness(perp_lo)
        s1 = run if e in covering else run - band_thickness(perp_hi)
        length = s1 - s0
        if length <= 0:
            continue

        sign = 1.0 if e in (1, 2) else -1.0            # which way is "out of the panel"
        bax = 1 if e in (1, 3) else 0                  # local axis normal to this edge
        boundary = (panel.height if e == 1 else 0.0) if e in (1, 3) else (panel.width if e == 2 else 0.0)

        face_c = [0.0, 0.0, t / 2]
        face_c[along_i] = (s0 + s1) / 2
        face_c[bax] = boundary + sign * _BAND_EPS
        normal_l = [0.0, 0.0, 0.0]; normal_l[bax] = sign
        along_l = [0.0, 0.0, 0.0]; along_l[along_i] = 1.0

        band_id = eb.band_for(e)
        lib = proj.edgeband(band_id) if band_id else None
        recs.append({
            "name": f"{owner}/e{e}",
            "panel": panel.id, "cabinet": cab_id, "owner": owner,
            "edge": e, "band": band_id or "(unspecified)",
            "band_name": (lib.name if lib else (band_id or "unspecified")),
            "thickness": b, "covering": e in covering,
            "color": colors.get(band_id, BAND_COLOR_DEFAULT),
            "qty": panel.quantity,
            "face_center": [round(v, 2) for v in _to_world(r, origin, tuple(face_c))],
            "normal": [round(v, 4) for v in _dir_world(r, tuple(normal_l))],
            "along": [round(v, 4) for v in _dir_world(r, tuple(along_l))],
            "length": round(length, 2), "span": round(max(t - 2 * _BAND_EPS, 0.2), 2),
        })
    return recs


def _panel_holes(panel: Panel, t: float, size: tuple, center: tuple, cab_id: str,
                 owner: str | None = None) -> list:
    """World-space drill records for one panel, for the viewer to draw as cylinders."""
    r = _panel_matrix(panel)
    aabb_min = tuple(center[i] - size[i] / 2 for i in range(3))
    origin = _local_origin(r, (panel.width, panel.height, t), aabb_min)
    owner = owner or f"{cab_id}/{panel.id}"
    recs = []
    for i, (ls, ld, depth, h) in enumerate(_hole_instances(panel, t)):
        recs.append({
            "name": f"{owner}#{i}",
            "panel": panel.id, "cabinet": cab_id, "owner": owner,
            "start": [round(v, 2) for v in _to_world(r, origin, ls)],
            "dir": [round(v, 4) for v in _dir_world(r, ld)],
            "depth": round(depth, 2), "dia": h.dia, "face": h.face,
            "through": h.depth == "through", "color": dia_color(h.dia), "src": h.src,
        })
    return recs


def _rgb(hex_color: str | None) -> list[float]:
    if not hex_color or not hex_color.startswith("#") or len(hex_color) != 7:
        return list(DEFAULT_COLOR)
    return [int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]


def _cabinet_origin(cab: Cabinet) -> tuple[float, float, float]:
    p = cab.position or {}
    return float(p.get("x", 0)), float(p.get("y", 0)), float(p.get("z", 0))


def _box(name, size, center, color, **meta) -> dict:
    obj = {"name": name, "type": "box",
           "size": [round(v, 2) for v in size],
           "center": [round(v, 2) for v in center],
           "color": color}
    obj.update({k: v for k, v in meta.items() if v is not None})
    return obj


def _custom_boxes(proj: Project, cab: Cabinet, holes_out: list | None = None,
                  bands_out: list | None = None, band_colors: dict | None = None) -> list[dict]:
    W = float(cab.dimensions.get("width", 0))
    D = float(cab.dimensions.get("depth", 0))
    H = float(cab.dimensions.get("height", 0))
    ox, oy, oz = _cabinet_origin(cab)
    boxes: list[dict] = []

    for p in cab.panels:
        t = proj.panel_thickness(p)
        board = proj.board(p.material) if p.material else None
        color = _rgb(board.color if board else None)
        role = p.role or ""

        if p.placement.get("pos"):                     # explicit placement wins (min-corner + size W,H,t)
            px, py, pz = (float(v) for v in p.placement["pos"])
            size = _rot_size((p.width, p.height, t), p.placement.get("rot"))
            center = (ox + px + size[0] / 2, oy + py + size[1] / 2, oz + pz + size[2] / 2)
        elif role == "side-left":
            size = (t, D, H); center = (ox + t / 2, oy + D / 2, oz + H / 2)
        elif role == "side-right":
            size = (t, D, H); center = (ox + W - t / 2, oy + D / 2, oz + H / 2)
        elif role == "bottom":
            size = (W - 2 * t, D, t); center = (ox + W / 2, oy + D / 2, oz + t / 2)
        elif role == "top":
            size = (W - 2 * t, D, t); center = (ox + W / 2, oy + D / 2, oz + H - t / 2)
        elif role == "shelf":
            sd = p.height or D
            size = (W - 2 * t, sd, t); center = (ox + W / 2, oy + sd / 2, oz + H / 2)
        elif role == "back":
            size = (W, t, H); center = (ox + W / 2, oy + D - t / 2, oz + H / 2)
        else:                                          # unknown role -> lay flat on the floor in front
            size = (p.width, p.height, t)
            center = (ox + W / 2, oy + D + 50 + p.height / 2, oz + t / 2)

        # `placement.step` renders a panel entry's whole `quantity` as a stepped run (identical shelves on
        # a pitch, say) instead of a single box. The count comes from `quantity` so the two can't disagree;
        # without `step` we draw exactly one box, as before.
        step = p.placement.get("step")
        offsets = ([tuple(float(step[k]) * i for k in range(3))
                    for i in range(max(int(p.quantity or 1), 1))] if step else [(0.0, 0.0, 0.0)])
        count = len(offsets)
        for i, off in enumerate(offsets):
            c = tuple(center[k] + off[k] for k in range(3))
            nm = f"{cab.id}/{p.id}" if i == 0 else f"{cab.id}/{p.id}~{i + 1}"
            boxes.append(_box(nm, size, c, color,
                              cabinet=cab.id, panel=p.id, role=role,
                              instance=(i + 1 if count > 1 else None),
                              instances=(count if count > 1 else None),
                              cut=[round(p.width, 1), round(p.height, 1), round(t, 1)],
                              material=(board.name if board else p.material)))
            if holes_out is not None and p.holes:
                holes_out += _panel_holes(p, t, tuple(size), tuple(c), cab.id, owner=nm)
            if bands_out is not None:
                bands_out += _panel_bands(proj, p, t, tuple(size), tuple(c), cab.id,
                                          band_colors or {}, owner=nm)
    return boxes


def _readymade_box(cab: Cabinet) -> dict:
    d = cab.raw.get("dimensions") or {}
    W, D, H = float(d.get("width", 0)), float(d.get("depth", 0)), float(d.get("height", 0))
    ox, oy, oz = _cabinet_origin(cab)
    return _box(f"{cab.id}", (W, D, H), (ox + W / 2, oy + D / 2, oz + H / 2),
                _rgb(cab.raw.get("color")),
                cabinet=cab.id, role=cab.raw.get("unit_type", "readymade"),
                cut=[round(W, 1), round(D, 1), round(H, 1)], material=cab.raw.get("system"))


def build_scene(proj: Project, cabinets: list[Cabinet], name: str = "scene") -> dict:
    objects: list[dict] = []
    holes: list[dict] = []
    bands: list[dict] = []
    colors = band_color_map(proj.edgebands.keys())
    for cab in cabinets:
        if cab.kind == "readymade":
            objects.append(_readymade_box(cab))
        else:
            objects += _custom_boxes(proj, cab, holes_out=holes, bands_out=bands,
                                     band_colors=colors)
    return {"name": name, "units": "mm", "objects": objects, "holes": holes, "bands": bands}


def write_scene(proj: Project, cabinets: list[Cabinet], out_path: Path, name: str = "scene") -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(build_scene(proj, cabinets, name=name), f, indent=2)
    return out_path

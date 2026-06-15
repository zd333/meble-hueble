"""Resolve a set/cabinet scope into a flat JSON scene of boxes for the Blender compiler.

This is a VIZ-ONLY derivation (placement is never order-relevant). Custom panels are laid out from
their `role` + the cabinet envelope; an explicit `panel.placement` overrides. Readymade units render as
a single box (or, later, their `model_ref`). Output is mm; render/compile.py scales to metres.
"""
from __future__ import annotations

import json
from pathlib import Path

from .model import Cabinet, Project

DEFAULT_COLOR = [0.85, 0.85, 0.83]


def _rgb(hex_color: str | None) -> list[float]:
    if not hex_color or not hex_color.startswith("#") or len(hex_color) != 7:
        return list(DEFAULT_COLOR)
    return [int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]


def _cabinet_origin(cab: Cabinet) -> tuple[float, float, float]:
    p = cab.position or {}
    return float(p.get("x", 0)), float(p.get("y", 0)), float(p.get("z", 0))


def _box(name, size, center, color):
    return {"name": name, "type": "box",
            "size": [round(v, 2) for v in size],
            "center": [round(v, 2) for v in center],
            "color": color}


def _custom_boxes(proj: Project, cab: Cabinet) -> list[dict]:
    W = float(cab.dimensions.get("width", 0))
    D = float(cab.dimensions.get("depth", 0))
    H = float(cab.dimensions.get("height", 0))
    ox, oy, oz = _cabinet_origin(cab)
    boxes: list[dict] = []

    for p in cab.panels:
        t = proj.panel_thickness(p)
        color = _rgb(proj.board(p.material).color if proj.board(p.material) else None)
        role = p.role or ""

        if p.placement.get("pos"):                     # explicit placement wins (min-corner + size W,H,t)
            px, py, pz = (float(v) for v in p.placement["pos"])
            size = (p.width, p.height, t)
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
        boxes.append(_box(f"{cab.id}/{p.id}", size, center, color))

    return boxes


def _readymade_box(cab: Cabinet) -> dict:
    d = cab.raw.get("dimensions") or {}
    W, D, H = float(d.get("width", 0)), float(d.get("depth", 0)), float(d.get("height", 0))
    ox, oy, oz = _cabinet_origin(cab)
    return _box(f"{cab.id}", (W, D, H), (ox + W / 2, oy + D / 2, oz + H / 2),
                _rgb(cab.raw.get("color")))


def build_scene(proj: Project, cabinets: list[Cabinet], name: str = "scene") -> dict:
    objects: list[dict] = []
    for cab in cabinets:
        if cab.kind == "readymade":
            obj = _readymade_box(cab)
            mref = cab.raw.get("model_ref")
            if mref:
                obj["model_ref"] = mref
            objects.append(obj)
        else:
            objects += _custom_boxes(proj, cab)
    return {"name": name, "units": "mm", "objects": objects}


def write_scene(proj: Project, cabinets: list[Cabinet], out_path: Path, name: str = "scene") -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scene = build_scene(proj, cabinets, name=name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scene, f, indent=2)
    return out_path

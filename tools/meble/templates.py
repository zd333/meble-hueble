"""One-shot cabinet scaffolds. They SEED a new cabinet's panels + confirmat fittings from a few
parameters; you then save the YAML, own it, and edit freely. Nothing live-binds afterward — re-running
scaffold makes a fresh cabinet, it does not re-derive an existing one.

Run `meble fit` on the saved cabinet to stamp the confirmat holes onto the panels.
"""
from __future__ import annotations

import io

from ruamel.yaml import YAML

_yaml = YAML()
_yaml.default_flow_style = False
_yaml.width = 4096

KINDS = ("base", "wall", "tall", "wardrobe")


def _band(edge: int, band_id: str) -> dict:
    return {"edges": {edge: band_id}, "glue_type": "long"}


def _shelf_pin_columns(depth: int, height: int) -> list:
    """Two bulk (multi) Ø5 pin columns for an adjustable shelf, on the INNER face — 37 mm from each end."""
    n = max(4, min(12, (height - 200) // 32))
    return [
        {"face": "inner", "x": depth - 37, "y": 100, "dia": 5, "depth": 13,
         "type": "multi", "count": n, "spacing": 32, "direction": "y"},
        {"face": "inner", "x": 37, "y": 100, "dia": 5, "depth": 13,
         "type": "multi", "count": n, "spacing": 32, "direction": "y"},
    ]


def _carcass(cab_id, name, category, width, height, depth, material, edgeband,
             thickness=18, with_shelf=True, plinth=None) -> dict:
    t = thickness
    inner_w = width - 2 * t
    at = [50, round(depth / 2), depth - 50]
    pins = _shelf_pin_columns(depth, height) if with_shelf else []

    panels = [
        {"id": "side-l", "name": "Left side", "element_type": "panel", "role": "side-left",
         "width": depth, "height": height, "edge_banding": _band(2, edgeband), "holes": list(pins)},
        {"id": "side-r", "name": "Right side", "element_type": "panel", "role": "side-right",
         "width": depth, "height": height, "edge_banding": _band(4, edgeband), "holes": list(pins)},
        {"id": "bottom", "name": "Bottom panel", "element_type": "panel", "role": "bottom",
         "width": inner_w, "height": depth, "edge_banding": _band(1, edgeband)},
        {"id": "top", "name": "Top panel", "element_type": "panel", "role": "top",
         "width": inner_w, "height": depth, "edge_banding": _band(1, edgeband)},
    ]
    if with_shelf:
        panels.append({"id": "shelf", "name": "Shelf", "element_type": "panel", "role": "shelf",
                       "width": inner_w, "height": depth - 20, "edge_banding": _band(1, edgeband),
                       "holes": []})
    panels.append({"id": "back", "name": "Back (HDF)", "element_type": "panel", "role": "back",
                   "material": "hdf-3", "width": width, "height": height, "grain": "any",
                   "edge_banding": {}})

    fittings = [
        {"id": "cf-bot-l", "hardware": "confirmat-7x50", "through": "side-l", "into": "bottom",
         "seam": {"through_edge": 3, "into_edge": 4}, "at": at},
        {"id": "cf-bot-r", "hardware": "confirmat-7x50", "through": "side-r", "into": "bottom",
         "seam": {"through_edge": 3, "into_edge": 2}, "at": at},
        {"id": "cf-top-l", "hardware": "confirmat-7x50", "through": "side-l", "into": "top",
         "seam": {"through_edge": 1, "into_edge": 4}, "at": at},
        {"id": "cf-top-r", "hardware": "confirmat-7x50", "through": "side-r", "into": "top",
         "seam": {"through_edge": 1, "into_edge": 2}, "at": at},
    ]

    cab = {
        "id": cab_id, "name": name, "kind": "custom", "category": category,
        "construction": "confirmat",
        "dimensions": {"width": width, "height": height, "depth": depth},
        "position": {"x": 0, "y": 0, "z": 0, "rotation": 0},
        "defaults": {"material": material, "edgeband": edgeband},
        "back": {"type": "surface"},
    }
    if plinth:
        cab["plinth"] = {"height": plinth}
    cab["panels"] = panels
    cab["assembly"] = {"fittings": fittings}
    cab["parts"] = []
    return cab


def scaffold(kind: str, width: float, height: float, depth: float,
             cab_id: str | None = None, name: str | None = None,
             material: str = "w1100-18", edgeband: str = "eb-w1100-1",
             thickness: int = 18) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown scaffold kind '{kind}' (choose from {', '.join(KINDS)})")
    defaults = {
        "base": dict(category="base", plinth=100, with_shelf=True),
        "wall": dict(category="wall", plinth=None, with_shelf=True),
        "tall": dict(category="tall", plinth=100, with_shelf=True),
        "wardrobe": dict(category="wardrobe", plinth=100, with_shelf=True),
    }[kind]
    cab_id = cab_id or f"{kind}-{int(width)}"
    name = name or f"{kind.capitalize()} cabinet {int(width)}"
    return _carcass(cab_id, name, defaults["category"], int(width), int(height), int(depth),
                    material, edgeband, thickness=thickness, with_shelf=defaults["with_shelf"],
                    plinth=defaults["plinth"])


def to_yaml(cab: dict) -> str:
    buf = io.StringIO()
    _yaml.dump(cab, buf)
    return buf.getvalue()

"""Load the YAML design into Python objects and resolve library references.

Read-only consumers (validate / csv / pdf / scene) use this. The `fit` command edits cabinet files
directly via ruamel round-trip (see fittings.py) so it does NOT go through these dataclasses.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ruamel.yaml import YAML

_yaml = YAML(typ="safe")

# Edge numbering shared everywhere: 1=top, 2=right, 3=bottom, 4=left.
WIDTH_EDGES = (1, 3)   # top + bottom — their length equals the panel width
HEIGHT_EDGES = (2, 4)  # right + left — their length equals the panel height

# Bore-diameter colour palette — shared by the PDF spec sheets and the 3D viewer so a Ø5 is the same
# green on paper and on screen. Keep it here (not in a renderer) so the two can never drift apart.
DIA_COLORS = {3: "#00B8D4", 4: "#1565C0", 5: "#2E7D32", 8: "#E65100",
              10: "#6A1B9A", 15: "#795548", 20: "#C2185B", 35: "#B71C1C"}
DIA_COLOR_DEFAULT = "#455A64"


def dia_color(dia) -> str:
    return DIA_COLORS.get(int(dia) if dia else 0, DIA_COLOR_DEFAULT)


# Bright palette assigned per edge-band id (deterministic: sorted order). Also shared by the PDF and the
# 3D viewer, so a band is the same colour in both.
BAND_PALETTE = ["#D81B60", "#8E24AA", "#3949AB", "#00897B", "#7CB342",
                "#FB8C00", "#6D4C41", "#00ACC1", "#C0CA33", "#5E35B1"]
BAND_COLOR_DEFAULT = "#90A4AE"


def band_color_map(band_ids) -> dict:
    return {bid: BAND_PALETTE[i % len(BAND_PALETTE)] for i, bid in enumerate(sorted(band_ids))}


def load_yaml(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return _yaml.load(f)


def find_root(start: Optional[Path] = None) -> Path:
    """Walk up from `start` (default cwd) to the repo root (has library/ and apartments/)."""
    cur = (start or Path.cwd()).resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "library").is_dir() and (cand / "apartments").is_dir():
            return cand
    raise FileNotFoundError(
        "Could not find the meble repo root (a directory containing library/ and apartments/). "
        f"Started from {cur}."
    )


# ---------------------------------------------------------------------------- library entities


@dataclass
class Board:
    id: str
    name: str = ""
    vendor: str = ""
    decor_code: str = ""
    texture: str = ""
    thickness: float = 18
    grain_directional: bool = False
    color: str = "#DDDDDD"

    @classmethod
    def from_dict(cls, d: dict) -> "Board":
        return cls(**{k: d.get(k, getattr(cls, k, None)) for k in
                      ("id", "name", "vendor", "decor_code", "texture", "thickness",
                       "grain_directional", "color")})


@dataclass
class Sheet:
    """A stock sheet format. `length` is the grain axis — see materials.yaml."""
    id: str
    name: str = ""
    length: float = 0
    width: float = 0
    price: Optional[float] = None      # per sheet; any currency, only ratios matter

    @property
    def area(self) -> float:
        """m²."""
        return self.length * self.width / 1e6

    @property
    def cost(self) -> float:
        """What `meble pack` minimises. Falls back to area when no price is given."""
        return self.price if self.price is not None else self.area

    def usable(self, trim: float) -> tuple[float, float]:
        return self.length - trim, self.width - trim

    @classmethod
    def from_dict(cls, d: dict) -> "Sheet":
        return cls(**{k: d.get(k, getattr(cls, k, None)) for k in
                      ("id", "name", "length", "width", "price")})


@dataclass
class PackParams:
    kerf: float = 5
    trim: float = 10

    @classmethod
    def from_dict(cls, d: dict) -> "PackParams":
        return cls(kerf=d.get("kerf", 5), trim=d.get("trim", 10))


@dataclass
class EdgeBand:
    id: str
    name: str = ""
    decor_code: str = ""
    texture: str = ""
    thickness: float = 1

    @classmethod
    def from_dict(cls, d: dict) -> "EdgeBand":
        return cls(**{k: d.get(k) for k in ("id", "name", "decor_code", "texture", "thickness")})


@dataclass
class Hardware:
    id: str
    type: str = ""
    name: str = ""
    drill: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Hardware":
        return cls(id=d["id"], type=d.get("type", ""), name=d.get("name", ""),
                   drill=dict(d.get("drill") or {}), raw=dict(d))


# ---------------------------------------------------------------------------- panel-level entities


@dataclass
class EdgeBanding:
    all_edges: bool = False
    band: Optional[str] = None
    edges: dict = field(default_factory=dict)   # int edge no -> band id (or True)
    glue_type: str = "long"

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "EdgeBanding":
        d = d or {}
        edges = {}
        for k, v in (d.get("edges") or {}).items():
            edges[int(k)] = v
        return cls(all_edges=bool(d.get("all_edges", False)), band=d.get("band"),
                   edges=edges, glue_type=d.get("glue_type", "long"))

    def banded_edges(self) -> set[int]:
        if self.all_edges:
            return {1, 2, 3, 4}
        return {e for e, v in self.edges.items() if v}

    def band_for(self, edge: int) -> Optional[str]:
        if edge in self.edges and self.edges[edge] not in (True, None):
            return self.edges[edge]
        if (self.all_edges or edge in self.edges) and self.band:
            return self.band
        return None


@dataclass
class Hole:
    face: str
    dia: float
    depth: Any = None          # int mm or "through"
    type: str = "single"
    frm: Optional[float] = None   # edge holes: distance from 0
    x: Optional[float] = None     # surface holes
    y: Optional[float] = None
    count: Optional[int] = None
    spacing: Optional[float] = None
    direction: Optional[str] = None
    src: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Hole":
        return cls(face=d["face"], dia=d.get("dia"), depth=d.get("depth"),
                   type=d.get("type", "single"), frm=d.get("from"),
                   x=d.get("x"), y=d.get("y"), count=d.get("count"),
                   spacing=d.get("spacing"), direction=d.get("direction"), src=d.get("src"))

    @property
    def is_edge(self) -> bool:
        return str(self.face).startswith("edge")

    @property
    def is_surface(self) -> bool:
        return self.face in ("outer", "inner")

    @property
    def edge_no(self) -> Optional[int]:
        return int(self.face[4:]) if self.is_edge else None

    def edge_positions(self) -> list:
        """Expand a multi EDGE hole into its individual distances-from-0."""
        if self.type == "multi" and self.count and self.spacing:
            return [(self.frm or 0) + i * self.spacing for i in range(self.count)]
        return [self.frm or 0]

    def surface_positions(self) -> list:
        """Expand a multi SURFACE hole into its individual (x, y) points."""
        n = self.count if (self.type == "multi" and self.count) else 1
        sp = self.spacing or 0
        pts = []
        for i in range(n):
            x, y = self.x or 0, self.y or 0
            if self.direction == "x":
                x += i * sp
            elif self.direction == "y":
                y += i * sp
            pts.append((x, y))
        return pts


@dataclass
class Panel:
    id: str
    name: str = ""
    element_type: str = "panel"
    role: str = ""
    material: Optional[str] = None
    width: float = 0
    height: float = 0
    thickness: Optional[float] = None
    quantity: int = 1
    grain: Optional[str] = None
    #: Another board this panel could equally be cut from, because it is hidden or its decor is a
    #: free choice. `meble pack --balance` may move it there to round the order up more cheaply.
    #: Never set this on a panel any face of which is visible in use.
    decor_optional: Optional[str] = None
    edge_banding: EdgeBanding = field(default_factory=EdgeBanding)
    holes: list[Hole] = field(default_factory=list)
    grooving: list = field(default_factory=list)
    placement: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict, default_material: Optional[str] = None) -> "Panel":
        return cls(
            id=d["id"], name=d.get("name", d["id"]),
            element_type=d.get("element_type", "panel"), role=d.get("role", ""),
            material=d.get("material", default_material),
            width=d.get("width", 0), height=d.get("height", 0),
            thickness=d.get("thickness"), quantity=int(d.get("quantity", 1) or 1),
            grain=d.get("grain"), decor_optional=d.get("decor_optional"),
            edge_banding=EdgeBanding.from_dict(d.get("edge_banding")),
            holes=[Hole.from_dict(h) for h in (d.get("holes") or [])],
            grooving=list(d.get("grooving") or []),
            placement=dict(d.get("placement") or {}),
        )


@dataclass
class Cabinet:
    id: str
    name: str = ""
    kind: str = "custom"
    category: str = ""
    construction: str = ""
    dimensions: dict = field(default_factory=dict)
    position: dict = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)
    back: dict = field(default_factory=dict)
    plinth: dict = field(default_factory=dict)
    panels: list[Panel] = field(default_factory=list)
    fittings: list[dict] = field(default_factory=list)
    parts: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    source_path: Optional[Path] = None

    @classmethod
    def from_dict(cls, d: dict, source_path: Optional[Path] = None) -> "Cabinet":
        default_material = (d.get("defaults") or {}).get("material")
        return cls(
            id=d["id"], name=d.get("name", d["id"]), kind=d.get("kind", "custom"),
            category=d.get("category", ""), construction=d.get("construction", ""),
            dimensions=dict(d.get("dimensions") or {}), position=dict(d.get("position") or {}),
            defaults=dict(d.get("defaults") or {}), back=dict(d.get("back") or {}),
            plinth=dict(d.get("plinth") or {}),
            panels=[Panel.from_dict(p, default_material) for p in (d.get("panels") or [])],
            fittings=list((d.get("assembly") or {}).get("fittings") or []),
            parts=list(d.get("parts") or []),
            raw=dict(d), source_path=source_path,
        )


@dataclass
class FurnitureSet:
    id: str
    name: str = ""
    room: str = ""
    cabinet_ids: list[str] = field(default_factory=list)
    layout: dict = field(default_factory=dict)
    directory: Optional[Path] = None


@dataclass
class Apartment:
    id: str
    name: str = ""
    rooms: list[str] = field(default_factory=list)
    sets: dict[str, FurnitureSet] = field(default_factory=dict)
    directory: Optional[Path] = None


# ---------------------------------------------------------------------------- project


@dataclass
class Project:
    root: Path
    boards: dict[str, Board] = field(default_factory=dict)
    sheets: dict[str, Sheet] = field(default_factory=dict)
    packing: "PackParams" = field(default_factory=lambda: PackParams())
    edgebands: dict[str, EdgeBand] = field(default_factory=dict)
    hardware: dict[str, Hardware] = field(default_factory=dict)
    parts: dict[str, dict] = field(default_factory=dict)          # raw part dicts
    units: dict[str, dict] = field(default_factory=dict)          # raw readymade-unit dicts
    apartments: dict[str, Apartment] = field(default_factory=dict)
    cabinets: dict[str, Cabinet] = field(default_factory=dict)    # by cabinet id (across apartments)

    # ---- lookups
    def board(self, id_: str) -> Optional[Board]:
        return self.boards.get(id_)

    def edgeband(self, id_: str) -> Optional[EdgeBand]:
        return self.edgebands.get(id_)

    def hw(self, id_: str) -> Optional[Hardware]:
        return self.hardware.get(id_)

    def panel_thickness(self, panel: Panel) -> float:
        if panel.thickness is not None:
            return panel.thickness
        b = self.board(panel.material) if panel.material else None
        return b.thickness if b else 18

    def cabinet(self, id_: str) -> Optional[Cabinet]:
        return self.cabinets.get(id_)

    def set(self, id_: str) -> Optional[FurnitureSet]:
        for ap in self.apartments.values():
            if id_ in ap.sets:
                return ap.sets[id_]
        return None

    def expanded_panels(self, cab: Cabinet) -> list[tuple[Panel, int]]:
        """Panels of a cabinet, plus panels of referenced parts, as (panel, effective_quantity)."""
        out: list[tuple[Panel, int]] = [(p, p.quantity) for p in cab.panels]
        for ref in cab.parts:
            pid = ref.get("ref")
            qty = int(ref.get("quantity", 1) or 0)
            part = self.parts.get(pid)
            if part and qty:
                dm = (part.get("defaults") or {}).get("material")
                for pd in (part.get("panels") or []):
                    pn = Panel.from_dict(pd, dm)
                    out.append((pn, pn.quantity * qty))
        return out


def load_project(root: Optional[Path] = None) -> Project:
    root = root or find_root()
    proj = Project(root=root)

    lib = root / "library"
    materials = load_yaml(lib / "materials.yaml") or {}
    for b in materials.get("boards", []):
        proj.boards[b["id"]] = Board.from_dict(b)
    for s in materials.get("sheets", []):
        proj.sheets[s["id"]] = Sheet.from_dict(s)
    proj.packing = PackParams.from_dict(materials.get("packing") or {})
    for e in (load_yaml(lib / "edgebands.yaml") or {}).get("edgebands", []):
        proj.edgebands[e["id"]] = EdgeBand.from_dict(e)
    for h in (load_yaml(lib / "hardware.yaml") or {}).get("hardware", []):
        proj.hardware[h["id"]] = Hardware.from_dict(h)
    if (lib / "parts").is_dir():
        for p in sorted((lib / "parts").glob("*.yaml")):
            d = load_yaml(p)
            if d:
                proj.parts[d["id"]] = d
    if (lib / "units").is_dir():
        for u in sorted((lib / "units").glob("*.yaml")):
            d = load_yaml(u)
            if d:
                proj.units[d["id"]] = d

    apts = root / "apartments"
    if apts.is_dir():
        for apt_dir in sorted(p for p in apts.iterdir() if p.is_dir()):
            ad = load_yaml(apt_dir / "apartment.yaml")
            if not ad:
                continue
            apt = Apartment(id=ad["id"], name=ad.get("name", ad["id"]),
                            rooms=list(ad.get("rooms") or []), directory=apt_dir)
            sets_dir = apt_dir / "sets"
            if sets_dir.is_dir():
                for set_dir in sorted(p for p in sets_dir.iterdir() if p.is_dir()):
                    sd = load_yaml(set_dir / "set.yaml")
                    if not sd:
                        continue
                    fs = FurnitureSet(id=sd["id"], name=sd.get("name", sd["id"]),
                                      room=sd.get("room", ""),
                                      cabinet_ids=list(sd.get("cabinets") or []),
                                      layout=dict(sd.get("layout") or {}), directory=set_dir)
                    apt.sets[fs.id] = fs
                    cab_dir = set_dir / "cabinets"
                    if cab_dir.is_dir():
                        for cf in sorted(cab_dir.glob("*.yaml")):
                            cd = load_yaml(cf)
                            if cd:
                                cab = Cabinet.from_dict(cd, source_path=cf)
                                proj.cabinets[cab.id] = cab
            proj.apartments[apt.id] = apt

    return proj


def cabinets_for_scope(proj: Project, apartment: Optional[str] = None,
                       set_: Optional[str] = None, cabinet: Optional[str] = None) -> list[Cabinet]:
    """Resolve a CLI scope to a list of cabinets."""
    if cabinet:
        cab = proj.cabinet(cabinet)
        if not cab:
            raise KeyError(f"cabinet '{cabinet}' not found")
        return [cab]
    if set_:
        fs = proj.set(set_)
        if not fs:
            raise KeyError(f"set '{set_}' not found")
        return [proj.cabinet(cid) for cid in fs.cabinet_ids if proj.cabinet(cid)]
    if apartment:
        apt = proj.apartments.get(apartment)
        if not apt:
            raise KeyError(f"apartment '{apartment}' not found")
        out: list[Cabinet] = []
        for fs in apt.sets.values():
            out += [proj.cabinet(cid) for cid in fs.cabinet_ids if proj.cabinet(cid)]
        return out
    return list(proj.cabinets.values())

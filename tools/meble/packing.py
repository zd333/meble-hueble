"""Test-pack panels onto stock sheets and recommend how to split the meble.pl order.

meble.pl charges for WHOLE sheets and one order carries one (decor, sheet format) pair, so the
question this module answers is *which sheets to buy*, not how to cut them — meble.pl owns nesting.

The packer is a plain **shelf (first-fit-decreasing-height)** algorithm with a kerf around every
panel and a trim off each sheet. That is strictly worse than a real nesting optimiser, which is the
point: a list that fits here fits at meble.pl with room to spare. It never under-reports a sheet.

GRAIN. `sheet.length` is the grain axis. A panel with `grain: height` must have its height along
that axis, `grain: width` its width; `grain: any` is free to rotate. Both of this project's formats
are 2800 long (the half sheet is the full one ripped lengthwise), so a narrower format does NOT mean
shorter panels — a 2520 mm gable fits a half sheet perfectly well.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import combinations, product
from typing import Iterable, Optional

from .model import Cabinet, PackParams, Project, Sheet

# Sort orders tried when packing. Shelf packing is heuristic-sensitive, so we run several and keep
# the best result rather than trusting any single one.
SORTS = {
    "max-dim desc": lambda p: (-max(p.w, p.h), -min(p.w, p.h)),
    "height desc": lambda p: (-p.h, -p.w),
    "width desc": lambda p: (-p.w, -p.h),
    "area desc": lambda p: (-p.w * p.h,),
    "grain-locked first": lambda p: (p.grain == "any", -max(p.w, p.h)),
}


@dataclass(frozen=True)
class Piece:
    """One physical board to be cut (a panel entry with quantity n yields n pieces)."""
    cab: str
    pid: str
    name: str
    w: float
    h: float
    grain: str
    board: str

    @property
    def label(self) -> str:
        return f"{self.cab}/{self.pid}"

    @property
    def area(self) -> float:
        return self.w * self.h / 1e6

    def orientations(self, kerf: float) -> list[tuple[float, float]]:
        """(along_grain, across_grain) options, kerf included."""
        a, b = self.h + kerf, self.w + kerf      # h along grain, w across
        if self.grain == "any":
            return [(a, b), (b, a)]
        if self.grain == "width":
            return [(b, a)]
        return [(a, b)]                          # 'height' (and anything unknown) — conservative


@dataclass
class Shelf:
    across: float                 # shelf depth, across the grain
    used_along: float = 0.0
    items: list = field(default_factory=list)


@dataclass
class PackedSheet:
    sheet: Sheet
    params: PackParams
    shelves: list[Shelf] = field(default_factory=list)

    @property
    def _limits(self) -> tuple[float, float]:
        """(along grain, across grain) usable."""
        return self.sheet.length - self.params.trim, self.sheet.width - self.params.trim

    @property
    def used_across(self) -> float:
        return sum(s.across for s in self.shelves)

    @property
    def pieces(self) -> list[Piece]:
        return [p for s in self.shelves for p, _, _ in s.items]

    @property
    def area_used(self) -> float:
        return sum(p.area for p in self.pieces)

    @property
    def fill(self) -> float:
        along, across = self._limits
        return self.area_used / (along * across / 1e6) * 100

    def try_place(self, piece: Piece) -> bool:
        along_max, across_max = self._limits
        opts = [(a, c) for a, c in piece.orientations(self.params.kerf)
                if a <= along_max and c <= across_max]
        for a, c in opts:                                    # existing shelf first
            for sh in self.shelves:
                if c <= sh.across and sh.used_along + a <= along_max:
                    sh.used_along += a
                    sh.items.append((piece, a, c))
                    return True
        for a, c in opts:                                    # else open a new shelf
            if self.used_across + c <= across_max:
                sh = Shelf(across=c, used_along=a)
                sh.items.append((piece, a, c))
                self.shelves.append(sh)
                return True
        return False


def pack(pieces: Iterable[Piece], sheet: Sheet, count: int,
         params: PackParams) -> tuple[list[PackedSheet], list[Piece]]:
    """Best-of-several-heuristics FFDH onto `count` sheets. Returns (sheets, leftovers)."""
    pieces = list(pieces)
    best: Optional[tuple[list[PackedSheet], list[Piece]]] = None
    for key in SORTS.values():
        sheets = [PackedSheet(sheet, params) for _ in range(count)]
        left = []
        for p in sorted(pieces, key=key):
            if not any(s.try_place(p) for s in sheets):
                left.append(p)
        if best is None or len(left) < len(best[1]):
            best = (sheets, left)
        if not left:
            break
    assert best is not None
    return best


def fits(pieces: Iterable[Piece], sheet: Sheet, count: int, params: PackParams) -> bool:
    return not pack(pieces, sheet, count, params)[1]


@dataclass
class Order:
    """One meble.pl order: a single decor on a single sheet format."""
    number: int
    board: str
    sheet: Sheet
    packed: list[PackedSheet]
    pieces: list[Piece]
    decor: str = ""            # the vendor decor code (U604), which is what you quote when ordering

    @property
    def area(self) -> float:
        return sum(p.area for p in self.pieces)

    @property
    def purchased(self) -> float:
        return len(self.packed) * self.sheet.area

    @property
    def marker(self) -> str:
        return (f"[order {self.number} · {self.decor or self.board} · "
                f"sheet {self.sheet.length:.0f}×{self.sheet.width:.0f}]")


#: Two mixes within this fraction of each other count as the same price, and the tie goes to the
#: one with fewer sheets. Two half sheets and one full differ by 0.3% of area, which is nobody's
#: real purchasing decision — without prices in materials.yaml that gap is an artefact of 1032×2
#: being 6 mm shy of 2070, and it should not be what picks the recommendation.
COST_TIE = 0.01


def _cheapest_mix(pieces: list[Piece], sheets: list[Sheet], params: PackParams,
                  cap: int = 8) -> Optional[dict[str, int]]:
    """Cheapest combination of sheet formats that holds every piece.

    Searched exhaustively over small counts rather than by a greedy rule like 'fill the big sheets
    first', so the answer is optimal for this packer. Cost is `sheet.cost` — the price when
    materials.yaml gives one, otherwise area. Near-ties are broken toward fewer sheets.
    """
    if not pieces:
        return {}
    combos = []
    for counts in product(range(cap + 1), repeat=len(sheets)):
        if any(counts):
            combos.append((sum(c * s.cost for c, s in zip(counts, sheets)), sum(counts), counts))
    combos.sort()

    best = None
    for cost, n_sheets, counts in combos:
        if best is not None and cost > best[0] * (1 + COST_TIE):
            break
        remaining = list(pieces)
        for n, sheet in zip(counts, sheets):
            if n:
                _, remaining = pack(remaining, sheet, n, params)
        if remaining:
            continue
        if best is None or n_sheets < best[1]:
            best = (cost, n_sheets, counts)
    if best is None:
        return None
    return {s.id: n for n, s in zip(best[2], sheets) if n}


def collect(proj: Project, cabinets: list[Cabinet]) -> tuple[list[Piece], list[tuple[str, str, str]]]:
    """Every orderable piece, plus the (cab, pid, alternative-board) entries free to change decor."""
    pieces: list[Piece] = []
    optional: list[tuple[str, str, str]] = []
    for cab in cabinets:
        if cab.kind != "custom":
            continue
        for panel, qty in proj.expanded_panels(cab):
            if panel.element_type != "panel":
                continue
            board = panel.material or cab.defaults.get("material") or "unknown"
            if panel.decor_optional and panel.decor_optional != board:
                optional.append((cab.id, panel.id, panel.decor_optional))
            for _ in range(qty):
                pieces.append(Piece(cab=cab.id, pid=panel.id, name=panel.name,
                                    w=float(panel.width), h=float(panel.height),
                                    grain=str(panel.grain), board=board))
    return pieces, optional


def _mixes_for(pieces: list[Piece], sheets: list[Sheet],
               params: PackParams) -> Optional[dict[str, dict[str, int]]]:
    by_board: dict[str, list[Piece]] = {}
    for p in pieces:
        by_board.setdefault(p.board, []).append(p)
    out = {}
    for board, group in by_board.items():
        mix = _cheapest_mix(group, sheets, params)
        if mix is None:
            return None
        out[board] = mix
    return out


def _mix_cost(mixes: dict[str, dict[str, int]], sheets: list[Sheet]) -> float:
    by_id = {s.id: s for s in sheets}
    return sum(n * by_id[sid].cost for mix in mixes.values() for sid, n in mix.items())


def balance(proj: Project, pieces: list[Piece], optional: list[tuple[str, str, str]],
            sheets: list[Sheet]) -> tuple[list[Piece], list[tuple[str, str, str]]]:
    """Try every on/off combination of the decor-optional panels; keep the cheapest.

    This is the decision docs/ordering-split.md is really about: a hidden panel's decor is free, and
    moving it changes how each decor rounds up to whole sheets. Returns (pieces, moves-applied).
    """
    params = proj.packing
    base = _mixes_for(pieces, sheets, params)
    best = (_mix_cost(base, sheets) if base else float("inf"), list(pieces), [])

    for r in range(1, len(optional) + 1):
        for combo in combinations(optional, r):
            moved = {(cab, pid): alt for cab, pid, alt in combo}
            trial = [Piece(**{**p.__dict__, "board": moved[(p.cab, p.pid)]})
                     if (p.cab, p.pid) in moved else p for p in pieces]
            mixes = _mixes_for(trial, sheets, params)
            if mixes is None:
                continue
            cost = _mix_cost(mixes, sheets)
            if cost < best[0] * (1 - COST_TIE):
                best = (cost, trial, list(combo))
    return best[1], best[2]


def plan(proj: Project, cabinets: list[Cabinet], sheet_ids: Optional[list[str]] = None,
         rebalance: bool = False) -> tuple[list[Order], list[tuple[str, str, str]]]:
    """Recommend the order split: which decors on which sheet formats, how many of each."""
    sheets = [proj.sheets[i] for i in (sheet_ids or list(proj.sheets))]
    if not sheets:
        raise ValueError("no sheet formats defined — add `sheets:` to library/materials.yaml")
    params = proj.packing

    pieces, optional = collect(proj, cabinets)
    moves: list[tuple[str, str, str]] = []
    if rebalance and optional:
        pieces, moves = balance(proj, pieces, optional, sheets)

    by_board: dict[str, list[Piece]] = {}
    for p in pieces:
        by_board.setdefault(p.board, []).append(p)

    orders: list[Order] = []
    n = 0
    for board in sorted(by_board):
        group = by_board[board]
        mix = _cheapest_mix(group, sheets, params)
        if mix is None:
            raise ValueError(f"cannot fit {board} on any combination of "
                             f"{', '.join(s.id for s in sheets)} (up to 8 each)")
        # Largest format first, so the odd offcuts land on the smaller sheet.
        remaining = list(group)
        for sheet in sorted(sheets, key=lambda s: -s.area):
            count = mix.get(sheet.id, 0)
            if not count:
                continue
            packed, remaining = pack(remaining, sheet, count, params)
            n += 1
            b = proj.board(board)
            orders.append(Order(number=n, board=board, sheet=sheet, packed=packed,
                                pieces=[p for s in packed for p in s.pieces],
                                decor=(b.decor_code if b else "")))
    return orders, moves


# --------------------------------------------------------------------------- marker stamping

_ID_RE = re.compile(r"^- id: (\S+)\s*$")
_NAME_RE = re.compile(r'^(\s*name:\s*)"([^"]*)"(.*)$')
_MARKER_RE = re.compile(r"\s*\[order .*?\]\s*$")


def stamp_markers(proj: Project, orders: list[Order]) -> list[tuple[str, str, str, str]]:
    """Write each panel's `[order N · …]` marker into its `name:` in the cabinet YAML.

    The marker rides in the free-text name so it reaches the CSV's `Nazwa` column and the PDF sheets
    without affecting nesting. Edits the YAML as text — the files are heavily commented and a
    round-trip through a YAML dumper would not preserve them.
    """
    marker_for = {(p.cab, p.pid): o.marker for o in orders for p in o.pieces}
    changed: list[tuple[str, str, str, str]] = []

    for cab_id in sorted({cab for cab, _ in marker_for}):
        cab = proj.cabinet(cab_id)
        if not cab or not cab.source_path:
            continue
        lines = cab.source_path.read_text(encoding="utf-8").splitlines(keepends=True)
        out, cur = [], None
        for line in lines:
            m = _ID_RE.match(line)
            if m:
                cur, _ = m.group(1), out.append(line)
                continue
            nm = _NAME_RE.match(line)
            if nm and cur is not None:
                marker = marker_for.get((cab_id, cur))
                if marker:
                    base = _MARKER_RE.sub("", nm.group(2)).rstrip()
                    new_line = f'{nm.group(1)}"{base}  {marker}"{nm.group(3)}\n'
                    if new_line != line:
                        changed.append((cab_id, cur, nm.group(2), f"{base}  {marker}"))
                    line = new_line
                cur = None
            out.append(line)
        cab.source_path.write_text("".join(out), encoding="utf-8")
    return changed

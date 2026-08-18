"""Bill of materials — what to BUY, from the fittings the designs declare.

This is a projection over `assembly.fittings`, the same way the CSV is a projection over the panels.
It counts declared fittings and nothing else; it never infers hardware from drill holes.

WHY NOT FROM THE HOLES. It is tempting, and it is wrong twice over:

  * A hole does not know what it is for. There are 50 Ø5 blind holes in this project, and most are
    hinge-plate and minifix-bolt holes rather than shelf pins. Counting them yields 50 pins when the
    answer is 20.
  * The count is not the quantity. A shelf-pin fitting's `at` is a list of shelf HEIGHTS, and each
    shelf takes 4 pins. A slide has no holes at all — it is mounted on site — yet still has to be
    bought. Hence `quantity:`.

And the distinction that motivated this module: **two fittings can share one `hardware:` id and still
be different things to buy.** wc-column's two doors both use `hinge-clip-110`, but door-l lands on a
side panel (full overlay) and door-r on the shared centre gable (half overlay). The cup and the plate
line are identical, so no amount of looking at holes can tell them apart — only `variant:` can. Buying
10 full-overlay hinges leaves door-r unhangeable, which is exactly the mistake this prevents.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .model import Cabinet, Project

#: `at` is a list of positions, so its length is the count — true for confirmat, minifix and hinge
#: fittings. Anything whose purchase quantity differs from its position count says so with `quantity:`.
DRILLING_MODES = ("stamped", "manual", "none")


@dataclass
class Line:
    """One thing you buy: a (hardware, variant) pair with a total."""
    hardware: str
    variant: str | None = None
    name: str = ""
    variant_name: str = ""
    sold_as: str = "piece"
    quantity: int = 0
    per_cabinet: dict = field(default_factory=dict)
    fittings: list = field(default_factory=list)

    @property
    def key(self) -> tuple:
        return (self.hardware, self.variant or "")

    @property
    def label(self) -> str:
        """Short form for a table column. The Polish shop name lives in `variant_name`."""
        if not self.variant:
            return self.name
        return f"{self.name} — {self.variant} overlay"


def fitting_quantity(f: dict) -> int:
    """How many units of hardware this fitting needs.

    `quantity:` wins when given; otherwise the number of `at` positions. A fitting with neither is a
    validation error rather than a silent zero — see validate.py.
    """
    if f.get("quantity") is not None:
        return int(f["quantity"])
    return len(f.get("at") or [])


def collared_pins(proj: Project, cabinets: list[Cabinet]) -> int:
    """Shelf pins that land in a `depth: through` bore, and so MUST have a collar.

    A gable with shelves on both sides gets ONE through column pair rather than two opposing blind
    ones (CLAUDE.md), so each through bore is shared by a shelf on each side — two pins meeting
    mid-panel at ~9 mm each. That is plenty of engagement, but only if each pin has a collar to stop
    against; a plain peg has nothing. Counted from the holes on purpose: it is a property of how the
    panel is drilled, not of the fitting.
    """
    n = 0
    for cab in cabinets:
        if cab.kind != "custom":
            continue
        pin_fittings = {f.get("id") for f in cab.fittings
                        if (proj.hw(f.get("hardware")) or None)
                        and proj.hw(f["hardware"]).raw.get("type") == "shelf-pin"}
        for panel, qty in proj.expanded_panels(cab):
            for h in panel.holes:
                if h.is_surface and h.dia == 5 and h.depth == "through" and h.src in pin_fittings:
                    n += len(h.surface_positions()) * qty * 2   # one pin from each side
    return n


def bill_of_materials(proj: Project, cabinets: list[Cabinet]) -> list[Line]:
    """Grouped by (hardware, variant), sorted by hardware id then variant. Pure."""
    lines: dict[tuple, Line] = {}
    for cab in cabinets:
        if cab.kind != "custom":
            continue
        for f in cab.fittings:
            hw_id = f.get("hardware")
            hw = proj.hw(hw_id)
            if hw is None:
                continue                      # validate.py reports the broken ref
            variant = f.get("variant")
            variants = hw.raw.get("variants") or {}
            key = (hw_id, variant or "")
            line = lines.get(key)
            if line is None:
                line = lines[key] = Line(
                    hardware=hw_id, variant=variant, name=hw.raw.get("name", hw_id),
                    variant_name=(variants.get(variant) or {}).get("name", "") if variant else "",
                    sold_as=hw.raw.get("sold_as", "piece"))
            n = fitting_quantity(f)
            line.quantity += n
            line.per_cabinet[cab.id] = line.per_cabinet.get(cab.id, 0) + n
            line.fittings.append(f"{cab.id}/{f.get('id')}")
    return sorted(lines.values(), key=lambda l: l.key)


# ---------------------------------------------------------------------------- sourcing

#: A price older than this is shown with a warning. Long enough not to nag, short enough that nobody
#: budgets off a year-old snapshot.
PRICE_STALE_DAYS = 120


@dataclass
class Buy:
    """One thing you put in a basket: an offering, the components it covers, and how many."""
    component: str
    component_name: str = ""
    quantity: int = 0
    vendor: str = ""
    sku: str = ""
    name: str = ""
    price: float | None = None
    checked: str = ""
    note: str = ""
    bundled_with: tuple = ()

    @property
    def total(self) -> float | None:
        return None if self.price is None else round(self.price * self.quantity, 2)


def _offerings(hw, vendor: str | None) -> list[dict]:
    out = []
    for s in (hw.raw.get("sourcing") or []):
        if vendor is None or s.get("vendor") == vendor:
            out.append(s)
    return out


def components_of(hw) -> list[dict]:
    """The logical parts of one fitting. Hardware with none declared is a single part."""
    return list(hw.raw.get("components") or [{"id": "item", "name": hw.raw.get("name", "")}])


def resolve_sourcing(proj: Project, line: Line, vendor: str | None = None,
                     prefer: dict | None = None) -> tuple[list[Buy], list[str]]:
    """-> (things to buy, components nothing covers).

    A vendor offering says which components it `covers:`, so one SKU may satisfy several parts (a
    "hinge with plate" set) or exactly one (Blum, which sells them apart). Whether a fitting arrives
    as one item or three is therefore looked up, never assumed — which is the only way the same
    design can be ordered from two shops that package differently.

    The second return value is what makes this worth having: a component with no offering is a part
    of the joint that nobody is going to buy.
    """
    hw = proj.hw(line.hardware)
    if hw is None:
        return [], []
    prefer = prefer or {}
    comps = components_of(hw)
    offers = _offerings(hw, vendor)

    buys, claimed = [], set()
    for comp in comps:
        if comp["id"] in claimed:
            continue
        # an offering fits if it covers this component and either ignores variants or matches ours
        cands = [o for o in offers
                 if comp["id"] in (o.get("covers") or ["item"])
                 and (o.get("variant") in (None, line.variant))]
        if not cands:
            continue
        pick = next((o for o in cands if o.get("sku") == prefer.get(comp["id"])), cands[0])
        covers = list(pick.get("covers") or ["item"])
        claimed.update(covers)
        buys.append(Buy(
            component=comp["id"], component_name=comp.get("name", comp["id"]),
            quantity=line.quantity, vendor=pick.get("vendor", ""), sku=pick.get("sku", ""),
            name=pick.get("name", ""), price=pick.get("price"), checked=str(pick.get("checked", "")),
            note=pick.get("note", ""),
            bundled_with=tuple(c for c in covers if c != comp["id"])))
    missing = [c.get("name", c["id"]) for c in comps if c["id"] not in claimed]
    return buys, missing


def alternatives(proj: Project, line: Line, vendor: str | None = None) -> list[dict]:
    """Other offerings for the same components — the ones worth knowing you could have chosen."""
    hw = proj.hw(line.hardware)
    if hw is None:
        return []
    chosen = {b.sku for b in resolve_sourcing(proj, line, vendor)[0]}
    return [o for o in _offerings(hw, vendor)
            if o.get("sku") not in chosen and o.get("variant") in (None, line.variant)]


def price_checked_dates(proj: Project, lines: list[Line], vendor: str | None = None) -> list[str]:
    """Every distinct `checked:` date behind the prices on a list, so the sheet can date itself."""
    seen = set()
    for line in lines:
        for b in resolve_sourcing(proj, line, vendor)[0]:
            if b.price is not None and b.checked:
                seen.add(b.checked)
    return sorted(seen)

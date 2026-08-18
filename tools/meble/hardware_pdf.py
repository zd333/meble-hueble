"""The shopping list as a PDF you can take to the counter, or paste into a basket.

Renders what `hardware.bill_of_materials` counted and what `hardware.resolve_sourcing` matched it to;
no counting or lookup happens here.

The sheet is deliberately blunt about provenance, because the ways this list can be wrong all look
perfectly plausible on paper:

  * a hinge variant collapsed into one line — 10 hinges of which 3 will not let the door shut;
  * a component nobody sells you — 10 hinges and no mounting plates hangs zero doors;
  * a stale price read as a quote. Every price carries the date someone last looked and is flagged
    once it is older than `PRICE_STALE_DAYS`. `meble pack` was deleted from this project because a
    local number that looked authoritative invited confident decisions that turned out wrong; a
    hard-coded price is the same trap, so the sheet never lets one pass as current.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .hardware import (PRICE_STALE_DAYS, Line, alternatives, components_of, price_checked_dates,
                       resolve_sourcing)
from .model import Project
from .pdf_export import MARGIN, MM, PH, PW, _register_fonts

C_HEAD = colors.HexColor("#00695C")
C_GREY = colors.HexColor("#757575")
C_WARN = colors.HexColor("#B71C1C")
C_RULE = colors.HexColor("#E0E0E0")
C_SKU = colors.HexColor("#1565C0")

#: Buy a few spare of the small, losable, cheap things. A second trip costs more than the spares.
SPARES = {"confirmat": 1.15, "shelf-pin": 1.5, "rafix": 1.2, "hinge": 1.2}


def _round_up(n: int, to: int) -> int:
    return ((n + to - 1) // to) * to


def buy_quantity(quantity: int, hw_type: str) -> int:
    factor = SPARES.get(hw_type, 1.0)
    if factor == 1.0:
        return quantity
    want = int(quantity * factor + 0.5)
    return _round_up(want, 5 if want >= 20 else 2)


def _fit(c, text: str, font: str, size: float, width: float) -> str:
    """Trim to `width` points with an ellipsis. Character counts guess wrong, and a column that runs
    off the paper is how a shopping list loses its last line."""
    if c.stringWidth(text, font, size) <= width:
        return text
    while text and c.stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text + "…"


def is_stale(checked: str, today: _dt.date) -> bool:
    try:
        return (today - _dt.date.fromisoformat(checked)).days > PRICE_STALE_DAYS
    except (ValueError, TypeError):
        return False


def export_hardware_pdf(proj: Project, lines: list[Line], collared: int, out_path: Path,
                        title: str = "Hardware", vendor: str | None = None,
                        today: _dt.date | None = None) -> Path:
    _register_fonts()
    from .pdf_export import FONT, FONT_BOLD          # after registration, so the TTF wins

    today = today or _dt.date.today()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_path), pagesize=A4)
    y = [PH - MARGIN]                                # boxed so the nested helpers can advance it
    cols = [MARGIN, MARGIN + 74 * MM, MARGIN + 98 * MM, MARGIN + 113 * MM, MARGIN + 132 * MM]

    def header():
        c.setFont(FONT_BOLD, 16)
        c.drawString(MARGIN, y[0] - 5 * MM, "Hardware shopping list")
        c.setFont(FONT, 9); c.setFillColor(C_GREY)
        c.drawRightString(PW - MARGIN, y[0] - 5 * MM,
                          f"{title}{'  ·  ' + vendor if vendor else ''}")
        c.setFillColor(colors.black)
        c.setStrokeColor(C_GREY); c.line(MARGIN, y[0] - 8 * MM, PW - MARGIN, y[0] - 8 * MM)
        y[0] -= 14 * MM
        c.setFont(FONT_BOLD, 8)
        for x, t in zip(cols, ["item", "SKU", "need", "buy", "~ cost"]):
            c.drawString(x, y[0], t)
        y[0] -= 1.5 * MM
        c.setStrokeColor(C_GREY); c.line(MARGIN, y[0], PW - MARGIN, y[0])
        y[0] -= 5.5 * MM

    def room(need: float):
        if y[0] - need < MARGIN + 8 * MM:
            c.showPage(); y[0] = PH - MARGIN; header()

    header()
    unsourced: list[str] = []
    grand = 0.0

    for line in lines:
        hw = proj.hw(line.hardware)
        hw_type = hw.raw.get("type", "") if hw else ""
        buys, missing = resolve_sourcing(proj, line, vendor=vendor)
        alts = alternatives(proj, line, vendor=vendor)
        room(10 * MM + 4.2 * MM * (len(buys) + len(missing) + len(alts)))

        unit = "" if line.sold_as == "piece" else f" {line.sold_as}s"
        c.setFont(FONT_BOLD, 9); c.setFillColor(colors.black)
        c.drawString(cols[0], y[0], _fit(c, line.label, FONT_BOLD, 9, cols[1] - cols[0] - 3 * MM))
        c.setFont(FONT, 9)
        c.drawString(cols[2], y[0], f"{line.quantity}{unit}")
        y[0] -= 4.2 * MM

        multi = len(components_of(hw)) > 1 if hw else False
        for b in buys:
            qty = buy_quantity(b.quantity, hw_type)
            cost = None if b.price is None else round(b.price * qty, 2)
            if cost:
                grand += cost
            label = f"{b.component_name} — {b.name}" if multi else b.name
            if b.bundled_with:
                label += f"  (bundle: also covers {', '.join(b.bundled_with)})"
            c.setFont(FONT, 8); c.setFillColor(C_GREY)
            c.drawString(cols[0] + 4 * MM, y[0],
                         _fit(c, label or "(unnamed)", FONT, 8, cols[1] - cols[0] - 7 * MM))
            c.setFont(FONT_BOLD, 8); c.setFillColor(C_SKU)
            c.drawString(cols[1], y[0], _fit(c, b.sku or "—", FONT_BOLD, 8, 22 * MM))
            c.setFont(FONT, 8); c.setFillColor(C_GREY)
            c.drawString(cols[2], y[0], str(b.quantity))
            c.setFont(FONT_BOLD, 8); c.setFillColor(colors.black)
            c.drawString(cols[3], y[0], str(qty))
            c.setFont(FONT, 8); c.setFillColor(C_GREY)
            c.drawString(cols[4], y[0],
                         f"{cost:.2f} PLN{' (!)' if is_stale(b.checked, today) else ''}"
                         if cost is not None else "— no price —")
            c.setFillColor(colors.black)
            y[0] -= 4 * MM

        for m in missing:
            # single-part hardware would otherwise read "Confirmat 7x50 - Confirmat 7x50"
            part = f" {m}" if multi else ""
            unsourced.append(f"{line.label}{(' — ' + m) if multi else ''}")
            c.setFont(FONT, 8); c.setFillColor(C_WARN)
            c.drawString(cols[0] + 4 * MM, y[0],
                         _fit(c, f"/!\\{part} — no supplier recorded", FONT, 8, 105 * MM))
            c.setFillColor(colors.black)
            y[0] -= 4 * MM

        for a in alts:
            c.setFont(FONT, 7.5); c.setFillColor(C_GREY)
            price = f"{a['price']:.2f} PLN" if a.get("price") is not None else ""
            c.drawString(cols[0] + 4 * MM, y[0],
                         _fit(c, f"or {a.get('sku','')} · {a.get('name','')} · {price}",
                              FONT, 7.5, 150 * MM))
            c.setFillColor(colors.black)
            y[0] -= 3.6 * MM

        c.setStrokeColor(C_RULE); c.line(MARGIN, y[0] + 1.4 * MM, PW - MARGIN, y[0] + 1.4 * MM)
        y[0] -= 3 * MM

    # ---------------------------------------------------------------- money, carefully framed
    dates = price_checked_dates(proj, lines, vendor=vendor)
    room(24 * MM)
    y[0] -= 2 * MM
    c.setFont(FONT_BOLD, 9)
    c.drawString(cols[0], y[0], "Indicative subtotal — priced lines only")
    c.drawString(cols[4], y[0], f"{grand:.2f} PLN")
    y[0] -= 5 * MM
    c.setFont(FONT, 7.5); c.setFillColor(C_WARN)
    c.drawString(cols[0], y[0],
                 f"/!\\ NOT A QUOTE. Prices last checked {', '.join(dates) if dates else 'never'}. "
                 f"Lines marked “no price” are missing from this total entirely.")
    y[0] -= 3.6 * MM
    c.drawString(cols[0], y[0],
                 f"    Confirm every figure in the basket before ordering. (!) marks a price older "
                 f"than {PRICE_STALE_DAYS} days.")
    c.setFillColor(colors.black)
    y[0] -= 9 * MM

    # ---------------------------------------------------------------- what to watch
    room(30 * MM)
    c.setFont(FONT_BOLD, 11); c.setFillColor(C_WARN)
    c.drawString(MARGIN, y[0], "Read before buying"); c.setFillColor(colors.black)
    y[0] -= 6.5 * MM

    notes: list[tuple[str, str]] = []
    if unsourced:
        notes.append(("Look these up before ordering.",
                      "Counted correctly, but no supplier is recorded — so no SKU, no price, and"))
        notes.append(("", "absent from the subtotal above. Add them to `sourcing:` once found:"))
        for u in unsourced:
            notes.append(("", f"    · {u}"))
    variants = [l for l in lines if l.variant]
    if variants:
        notes.append(("The hinges are NOT interchangeable.",
                      "Overlay depends on what the door lands on, and the drilling is identical for"))
        notes.append(("", "all of them — nothing on the panel sheets will tell you which is which:"))
        for l in variants:
            notes.append(("", f"    · {l.quantity} × {l.variant_name}  —  "
                              f"{', '.join(sorted(l.per_cabinet))}"))
        notes.append(("", "A full-overlay hinge on a shared divider will not let the door shut."))
        notes.append(("", "Overlay is fine-tuned by PLATE HEIGHT, not the hinge: if a door rubs, a"))
        notes.append(("", "different h= plate fixes it without buying a different hinge."))
    if collared:
        notes.append((f"Shelf pins: {collared} need a collar.",
                      "Those sit in THROUGH bores shared by the compartments either side of a gable,"))
        notes.append(("", "so two pins meet mid-panel at ~9 mm each. Plenty — but only with a collar"))
        notes.append(("", "to stop against. A plain peg has nothing."))
    notes.append(("Quantities come from the designs.",
                  "Every one is a declared fitting, never a guess from the drill holes: a hole does"))
    notes.append(("", "not know what it is for, and a shelf-pin fitting's positions are shelf"))
    notes.append(("", "HEIGHTS, not pins. `buy` adds spares; `need` is the exact figure."))

    for lead, text in notes:
        room(6 * MM)
        if lead:
            c.setFont(FONT_BOLD, 8); c.drawString(MARGIN, y[0], _fit(c, lead, FONT_BOLD, 8, 56 * MM))
            c.setFont(FONT, 8); c.drawString(MARGIN + 58 * MM, y[0], text)
        else:
            c.setFont(FONT, 8); c.setFillColor(C_GREY)
            c.drawString(MARGIN + 58 * MM, y[0], text); c.setFillColor(colors.black)
        y[0] -= 4.2 * MM

    c.setFont(FONT, 7); c.setFillColor(C_GREY)
    c.drawCentredString(PW / 2, MARGIN - 4 * MM,
                        "meble · hardware list · counted from assembly.fittings; SKUs and prices from "
                        "library/hardware.yaml `sourcing:`")
    c.showPage(); c.save()
    return out_path

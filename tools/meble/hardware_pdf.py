"""The shopping list as a one-page PDF you can take to the counter.

Renders what `hardware.bill_of_materials` computed and nothing else — no counting happens here. The
sheet is deliberately blunt about *how* each number was reached, because the two ways this list can
be wrong (a hinge variant collapsed into one line, a pin count taken from the hole count) both look
perfectly plausible on paper.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .hardware import Line
from .model import Project
from .pdf_export import MARGIN, MM, PH, PW, _register_fonts

C_HEAD = colors.HexColor("#00695C")
C_GREY = colors.HexColor("#757575")
C_WARN = colors.HexColor("#B71C1C")
C_RULE = colors.HexColor("#E0E0E0")

#: Buy a few spare of the small, losable, cheap things. A second trip to the shop costs more than the
#: spares do. Keyed by hardware type; anything absent is ordered exactly.
SPARES = {"confirmat": 1.15, "shelf-pin": 1.5, "minifix": 1.2, "hinge": 1.2}


def _round_up(n: int, to: int) -> int:
    return ((n + to - 1) // to) * to


def _fit(c, text: str, font: str, size: float, width: float) -> str:
    """Trim `text` to `width` points, with an ellipsis. Character counts guess wrong — a column that
    silently runs off the page is how a shopping list loses its last cabinet."""
    if c.stringWidth(text, font, size) <= width:
        return text
    while text and c.stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text + "…"


def buy_quantity(line: Line, hw_type: str) -> int:
    """What to actually put in the basket: the need plus a sensible margin, rounded to a tidy number."""
    factor = SPARES.get(hw_type, 1.0)
    if factor == 1.0:
        return line.quantity
    want = int(line.quantity * factor + 0.5)
    return _round_up(want, 5 if want >= 20 else 2)


def export_hardware_pdf(proj: Project, lines: list[Line], collared: int, out_path: Path,
                        title: str = "Hardware") -> Path:
    _register_fonts()
    from .pdf_export import FONT, FONT_BOLD          # after registration, so the TTF wins

    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_path), pagesize=A4)

    y = PH - MARGIN
    c.setFont(FONT_BOLD, 16); c.drawString(MARGIN, y - 5 * MM, "Hardware shopping list")
    c.setFont(FONT, 9); c.setFillColor(C_GREY)
    c.drawRightString(PW - MARGIN, y - 5 * MM, title)
    c.setFillColor(colors.black)
    c.setStrokeColor(C_GREY); c.line(MARGIN, y - 8 * MM, PW - MARGIN, y - 8 * MM)

    # ---------------------------------------------------------------- the list
    y -= 16 * MM
    cols = [MARGIN, MARGIN + 78 * MM, MARGIN + 96 * MM, MARGIN + 114 * MM]
    c.setFont(FONT_BOLD, 8)
    for x, t in zip(cols, ["item", "needed", "buy", "where"]):
        c.drawString(x, y, t)
    y -= 1.5 * MM
    c.setStrokeColor(C_GREY); c.line(MARGIN, y, PW - MARGIN, y); y -= 5.5 * MM

    for line in lines:
        hw = proj.hw(line.hardware)
        hw_type = hw.raw.get("type", "") if hw else ""
        unit = "" if line.sold_as == "piece" else f" {line.sold_as}s"
        c.setFont(FONT_BOLD, 9)
        c.drawString(cols[0], y, _fit(c, line.label, FONT_BOLD, 9, cols[1] - cols[0] - 3 * MM))
        c.setFont(FONT, 9)
        c.drawString(cols[1], y, f"{line.quantity}{unit}")
        c.setFont(FONT_BOLD, 9)
        c.drawString(cols[2], y, f"{buy_quantity(line, hw_type)}{unit}")
        c.setFont(FONT, 7.5); c.setFillColor(C_GREY)
        where = ", ".join(f"{k} {v}" for k, v in sorted(line.per_cabinet.items()))
        c.drawString(cols[3], y, _fit(c, where, FONT, 7.5, PW - MARGIN - cols[3]))
        c.setFillColor(colors.black)
        y -= 4 * MM
        c.setStrokeColor(C_RULE); c.line(MARGIN, y, PW - MARGIN, y); y -= 4 * MM

    # ---------------------------------------------------------------- what to watch
    y -= 6 * MM
    c.setFont(FONT_BOLD, 11); c.setFillColor(C_WARN)
    c.drawString(MARGIN, y, "Read before buying"); c.setFillColor(colors.black)
    y -= 6.5 * MM

    notes: list[tuple[str, str]] = []
    variants = [l for l in lines if l.variant]
    if variants:
        notes.append(("The hinges are NOT interchangeable.",
                      "The overlay depends on what the door lands on, and the drilling is identical for"))
        notes.append(("", "all of them — so nothing on the panel sheet will tell you which is which:"))
        for l in variants:
            where = ", ".join(f"{k}" for k in sorted(l.per_cabinet))
            notes.append(("", f"    {l.quantity} × {l.variant_name}  —  {where}"))
        notes.append(("", "A full-overlay hinge on a shared divider will not let the door shut."))
    if collared:
        notes.append(("Shelf pins: %d need a collar." % collared,
                      "Those go into THROUGH bores shared by the compartments on both sides of a gable,"))
        notes.append(("", "so two pins meet mid-panel at ~9 mm each. That is plenty of engagement, but"))
        notes.append(("", "only if each has a collar to stop against — a plain peg has nothing."))
    notes.append(("Quantities come from the designs.",
                  "Every one is a declared fitting, not a guess from the drill holes: a hole does not"))
    notes.append(("", "know what it is for, and a shelf-pin fitting's positions are shelf HEIGHTS, not"))
    notes.append(("", "pins. The `buy` column adds spares for the small cheap things."))
    notes.append(("Slides are mounted on site.",
                  "No holes are drilled for them anywhere, by design — screw them on with chipboard"))
    notes.append(("", "screws, keeping the drawer member's screws out of the 18 mm end grain."))

    for lead, text in notes:
        if lead:
            c.setFont(FONT_BOLD, 8); c.drawString(MARGIN, y, lead)
            c.setFont(FONT, 8); c.drawString(MARGIN + 58 * MM, y, text)
        else:
            c.setFont(FONT, 8); c.setFillColor(C_GREY)
            c.drawString(MARGIN + 58 * MM, y, text); c.setFillColor(colors.black)
        y -= 4.2 * MM

    c.setFont(FONT, 7); c.setFillColor(C_GREY)
    c.drawCentredString(PW / 2, MARGIN - 4 * MM,
                        "meble · hardware list · counted from assembly.fittings, never from drill holes")
    c.showPage(); c.save()
    return out_path

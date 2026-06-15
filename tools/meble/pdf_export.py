"""Per-panel PDF spec sheet for manual entry into the centrum.meble.pl editor.

Layout mirrors the editor's field order so you can read a page top-to-bottom and type. Each panel page
has two to-scale diagrams (front + back face) with edge numbers (1=top 2=right 3=bottom 4=left) and
plotted holes, then tables for size, edge banding, and drilling, each with a check column. A linked
index lists every panel. Reads ONLY the panels (the source of truth).
"""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .model import Cabinet, Panel, Project

MM = 72.0 / 25.4
PW, PH = A4
MARGIN = 15 * MM
EDGE_NAMES = {1: "1 góra", 2: "2 prawo", 3: "3 dół", 4: "4 lewo"}

# Polish needs a Unicode TTF — the base-14 Helvetica renders ł/ś/ż/ć/ę/ą as boxes.
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
_FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]


def _register_fonts() -> bool:
    """Register a Polish-capable TTF as Body/Body-Bold. Returns False if none found (falls back to
    Helvetica, which cannot render all Polish diacritics)."""
    global FONT, FONT_BOLD
    for reg, bold in _FONT_CANDIDATES:
        if not os.path.exists(reg):
            continue
        try:
            pdfmetrics.registerFont(TTFont("Body", reg))
            FONT = "Body"
            if os.path.exists(bold):
                pdfmetrics.registerFont(TTFont("Body-Bold", bold))
                FONT_BOLD = "Body-Bold"
            else:
                FONT_BOLD = "Body"
            return True
        except Exception:
            continue
    return False


def _depth_str(d) -> str:
    return "na wylot" if d == "through" else f"{d} mm"


def _checkbox(c: canvas.Canvas, x: float, y: float, s: float = 3 * MM) -> None:
    c.saveState()
    c.setLineWidth(0.6)
    c.rect(x, y, s, s, stroke=1, fill=0)
    c.restoreState()


def _diagram(c: canvas.Canvas, panel: Panel, surface: str, scale: float,
             ox: float, oy: float, label: str) -> None:
    """Draw one face of the panel: rectangle, edge numbers, edge holes, this surface's holes."""
    rw, rh = panel.width * scale, panel.height * scale
    c.saveState()
    c.setLineWidth(1)
    c.setStrokeColor(colors.black)
    c.rect(ox, oy, rw, rh, stroke=1, fill=0)

    c.setFont(FONT, 7)
    c.drawCentredString(ox + rw / 2, oy + rh + 2 * MM, label)
    # edge numbers
    c.setFont(FONT, 6)
    c.setFillColor(colors.HexColor("#1565C0"))
    c.drawCentredString(ox + rw / 2, oy + rh - 3.2 * MM, "1")
    c.drawCentredString(ox + rw / 2, oy + 1.6 * MM, "3")
    c.drawRightString(ox + rw - 1 * MM, oy + rh / 2, "2")
    c.drawString(ox + 1 * MM, oy + rh / 2, "4")
    c.setFillColor(colors.black)

    # dimension labels
    c.setFont(FONT, 6.5)
    c.drawCentredString(ox + rw / 2, oy - 4 * MM, f"szer. {int(panel.width)}")
    c.saveState()
    c.translate(ox - 3.5 * MM, oy + rh / 2)
    c.rotate(90)
    c.drawCentredString(0, 0, f"wys. {int(panel.height)}")
    c.restoreState()

    # edge holes (on the perimeter — shared across both faces)
    c.setFillColor(colors.HexColor("#C62828"))
    for h in panel.holes:
        if not h.is_edge:
            continue
        f = h.frm or 0
        e = h.edge_no
        if e == 1:
            px, py = ox + f * scale, oy + rh
        elif e == 3:
            px, py = ox + f * scale, oy
        elif e == 2:
            px, py = ox + rw, oy + f * scale
        else:
            px, py = ox, oy + f * scale
        c.circle(px, py, 1.2 * MM, stroke=0, fill=1)
    c.setFillColor(colors.black)

    # surface holes for THIS face
    c.setStrokeColor(colors.HexColor("#2E7D32"))
    c.setFillColor(colors.HexColor("#2E7D32"))
    for h in panel.holes:
        if h.face != surface:
            continue
        px, py = ox + (h.x or 0) * scale, oy + (h.y or 0) * scale
        r = max(1.0 * MM, (h.dia or 5) * scale / 2)
        through = h.depth == "through"
        c.circle(px, py, r, stroke=1, fill=0 if through else 1)
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.black)
    c.restoreState()


def _draw_panel_page(c: canvas.Canvas, proj: Project, cab: Cabinet, panel: Panel,
                     qty: int, idx: int, dest: str) -> None:
    c.bookmarkPage(dest)
    board = proj.board(panel.material) if panel.material else None
    thickness = proj.panel_thickness(panel)

    # header
    y = PH - MARGIN
    c.setFont(FONT_BOLD, 14)
    c.drawString(MARGIN, y - 4 * MM, f"P{idx}.  {panel.name}")
    c.setFont(FONT, 9)
    c.drawRightString(PW - MARGIN, y - 4 * MM, f"{cab.name}  ·  {cab.id}/{panel.id}")
    c.setStrokeColor(colors.grey)
    c.line(MARGIN, y - 6 * MM, PW - MARGIN, y - 6 * MM)
    c.setStrokeColor(colors.black)

    # diagrams: front (left) + back (right), shared scale
    area_top = y - 12 * MM
    area_h = 75 * MM
    half = (PW - 2 * MARGIN - 10 * MM) / 2
    scale = min((half - 12 * MM) / max(panel.width, 1), (area_h - 14 * MM) / max(panel.height, 1))
    rw, rh = panel.width * scale, panel.height * scale
    base_y = area_top - rh - 6 * MM
    fx = MARGIN + (half - rw) / 2 + 4 * MM
    bx = MARGIN + half + 10 * MM + (half - rw) / 2 + 4 * MM
    _diagram(c, panel, "front", scale, fx, base_y, "PRZÓD (front)")
    _diagram(c, panel, "back", scale, bx, base_y, "TYŁ (back)")

    # tables
    ty = base_y - 12 * MM
    ty = _table_size(c, panel, qty, board, thickness, ty)
    ty = _table_banding(c, proj, panel, ty)
    ty = _table_drilling(c, panel, ty)

    c.setFont(FONT, 7)
    c.setFillColor(colors.grey)
    c.drawCentredString(PW / 2, MARGIN - 4 * MM, f"meble · {cab.id} · strona panelu P{idx}")
    c.setFillColor(colors.black)
    c.showPage()


def _row(c, x, y, cells, widths, bold=False, check=False):
    if check:
        _checkbox(c, x - 6 * MM, y - 0.5 * MM)
    c.setFont(FONT_BOLD if bold else FONT, 8)
    cx = x
    for cell, w in zip(cells, widths):
        c.drawString(cx, y, str(cell))
        cx += w
    return y - 5.2 * MM


def _heading(c, x, y, text):
    c.setFont(FONT_BOLD, 9.5)
    c.setFillColor(colors.HexColor("#37474F"))
    c.drawString(x, y, text)
    c.setFillColor(colors.black)
    return y - 5.5 * MM


def _table_size(c, panel: Panel, qty, board, thickness, y):
    x = MARGIN + 6 * MM
    y = _heading(c, MARGIN, y, "Wymiar i materiał")
    y = _row(c, x, y, ["szerokość", "wysokość", "grubość", "ilość", "słoje"],
             [30 * MM, 30 * MM, 28 * MM, 22 * MM, 30 * MM], bold=True)
    grain = {"any": "0 bez zn.", "height": "1 wys.", "width": "2 szer."}.get(panel.grain, "2 szer.")
    y = _row(c, x, y, [f"{int(panel.width)} mm", f"{int(panel.height)} mm",
                       f"{thickness:g} mm", qty, grain],
             [30 * MM, 30 * MM, 28 * MM, 22 * MM, 30 * MM], check=True)
    c.setFont(FONT, 7.5)
    c.drawString(x, y, f"płyta: {board.name if board else panel.material}")
    return y - 7 * MM


def _table_banding(c, proj: Project, panel: Panel, y):
    x = MARGIN + 6 * MM
    eb = panel.edge_banding
    y = _heading(c, MARGIN, y, f"Oklejanie  ·  klejenie: {eb.glue_type} (kryjące {'długie' if eb.glue_type=='long' else 'krótkie'})")
    y = _row(c, x, y, ["krawędź", "okleina", "model", "grubość"],
             [26 * MM, 22 * MM, 55 * MM, 24 * MM], bold=True)
    for e in (1, 2, 3, 4):
        band_id = eb.band_for(e)
        if band_id:
            band = proj.edgeband(band_id)
            model = band.name if band else band_id
            th = f"{band.thickness:g} mm" if band else ""
            y = _row(c, x, y, [EDGE_NAMES[e], "TAK", model, th],
                     [26 * MM, 22 * MM, 55 * MM, 24 * MM], check=True)
        else:
            y = _row(c, x, y, [EDGE_NAMES[e], "—", "", ""],
                     [26 * MM, 22 * MM, 55 * MM, 24 * MM], check=True)
    return y - 4 * MM


def _table_drilling(c, panel: Panel, y):
    x = MARGIN + 6 * MM
    edge_holes = [h for h in panel.holes if h.is_edge]
    surf_holes = [h for h in panel.holes if h.is_surface]

    y = _heading(c, MARGIN, y, "Wiercenia — krawędziowe")
    if edge_holes:
        y = _row(c, x, y, ["krawędź", "od 0", "Ø", "głęb.", "typ"],
                 [26 * MM, 24 * MM, 18 * MM, 24 * MM, 40 * MM], bold=True)
        for h in edge_holes:
            typ = h.type if h.type != "multi" else f"multi ×{h.count} co {h.spacing}"
            tag = "  (auto)" if h.src else ""
            y = _row(c, x, y, [EDGE_NAMES[h.edge_no], f"{h.frm} mm", f"{h.dia}", _depth_str(h.depth), typ + tag],
                     [26 * MM, 24 * MM, 18 * MM, 24 * MM, 40 * MM], check=True)
    else:
        c.setFont(FONT, 8); c.drawString(x, y, "— brak —"); y -= 5.2 * MM

    y -= 2 * MM
    y = _heading(c, MARGIN, y, "Wiercenia — powierzchniowe")
    if surf_holes:
        y = _row(c, x, y, ["str.", "x", "y", "Ø", "głęb.", "typ"],
                 [20 * MM, 22 * MM, 22 * MM, 16 * MM, 24 * MM, 40 * MM], bold=True)
        for h in surf_holes:
            typ = h.type if h.type != "multi" else f"multi ×{h.count} co {h.spacing} ({h.direction})"
            tag = "  (auto)" if h.src else ""
            face = "tył" if h.face == "back" else "przód"
            y = _row(c, x, y, [face, f"{h.x}", f"{h.y}", f"{h.dia}", _depth_str(h.depth), typ + tag],
                     [20 * MM, 22 * MM, 22 * MM, 16 * MM, 24 * MM, 40 * MM], check=True)
    else:
        c.setFont(FONT, 8); c.drawString(x, y, "— brak —"); y -= 5.2 * MM
    return y


def _draw_index(c: canvas.Canvas, title: str, entries: list[tuple]) -> None:
    """entries: list of (idx, dest, cab, panel, qty)."""
    def header():
        c.setFont(FONT_BOLD, 16)
        c.drawString(MARGIN, PH - MARGIN - 4 * MM, title)
        c.setFont(FONT, 9)
        c.setFillColor(colors.grey)
        c.drawString(MARGIN, PH - MARGIN - 10 * MM,
                     "Lista paneli — kliknij pozycję, aby przejść do karty panelu.")
        c.setFillColor(colors.black)

    header()
    y = PH - MARGIN - 18 * MM
    c.setFont(FONT, 9)
    for idx, dest, cab, panel, qty in entries:
        if y < MARGIN + 10 * MM:
            c.showPage()
            header()
            y = PH - MARGIN - 18 * MM
            c.setFont(FONT, 9)
        text = (f"P{idx}.  {cab.id} / {panel.name}   "
                f"{int(panel.width)}×{int(panel.height)} mm   ×{qty}")
        c.drawString(MARGIN, y, text)
        c.linkAbsolute("", dest, (MARGIN - 1 * MM, y - 1.5 * MM, PW - MARGIN, y + 4 * MM))
        c.setFillColor(colors.HexColor("#1565C0"))
        c.drawRightString(PW - MARGIN, y, "→")
        c.setFillColor(colors.black)
        y -= 6 * MM
    c.showPage()


def export_pdf(proj: Project, cabinets: list[Cabinet], out_path: Path, title: str = "Panele") -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not _register_fonts():
        print("  warn: no Unicode TTF found — Polish characters may not render (install Arial/DejaVu).")
    c = canvas.Canvas(str(out_path), pagesize=A4)
    c.setTitle(title)

    entries: list[tuple] = []
    idx = 0
    for cab in cabinets:
        if cab.kind != "custom":
            continue
        for panel, qty in proj.expanded_panels(cab):
            if panel.element_type != "panel":
                continue
            idx += 1
            entries.append((idx, f"p{idx}", cab, panel, qty))

    _draw_index(c, title, entries)
    for idx, dest, cab, panel, qty in entries:
        _draw_panel_page(c, proj, cab, panel, qty, idx, dest)

    c.save()
    return out_path

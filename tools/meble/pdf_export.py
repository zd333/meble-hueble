"""Per-panel PDF spec sheet for manual entry into the centrum.meble.pl editor.

Layout mirrors the editor's field order so you can read a page top-to-bottom and type. Each panel page
has two to-scale diagrams (outer + inner face) and tables for size, edge banding, and drilling — each row
with a check box. Colour coding (consistent across all pages):
  · plate fill   = a light tint per board material
  · edge colour  = per edge-band (bright, arbitrary; the swatch in the banding table matches)
  · hole colour  = per bore diameter (static palette; the swatch in the drilling table matches)
Edge holes are drawn as inward lines whose length shows drilling depth. Reads ONLY the panels.
"""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .model import (BAND_COLOR_DEFAULT, Cabinet, DIA_COLORS, DIA_COLOR_DEFAULT, Panel, Project,
                    band_color_map)

MM = 72.0 / 25.4
PW, PH = A4
MARGIN = 15 * MM
EDGE_NAMES = {1: "1 top", 2: "2 right", 3: "3 bottom", 4: "4 left"}
# which local edge faces the cabinet front, per role (for orientation labels)
_FRONT_EDGE_DESC = {"side-left": "right edge (2)", "side-right": "left edge (4)",
                    "bottom": "top edge (1)", "top": "top edge (1)", "shelf": "top edge (1)"}


def _front_desc(role: str):
    return _FRONT_EDGE_DESC.get(role)

# ---- fonts (Polish-capable TTF; base-14 Helvetica can't render ł/ś/ż) ----
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
_FONT_CANDIDATES = [
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
]


def _register_fonts() -> bool:
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


# ---- colours ----
C_DIM = colors.HexColor("#00695C")     # size & material section
C_BAND = colors.HexColor("#6A1B9A")    # edge-banding section
C_DRILL = colors.HexColor("#BF360C")   # drilling sections
C_GREY = colors.HexColor("#9E9E9E")

# bore-diameter palette lives in model.py — shared with the 3D viewer (same colour on paper and screen)
_DIA_DEFAULT = DIA_COLOR_DEFAULT

# per-edge-band palette lives in model.py — shared with the 3D viewer
BAND_COLORS: dict[str, str] = {}       # band id -> hex, populated in export_pdf

# bright palette assigned per board (faded to a pastel for the plate fill); arbitrary, not the real decor
_MATERIAL_PALETTE = ["#42A5F5", "#66BB6A", "#FFA726", "#AB47BC", "#EF5350",
                     "#26A69A", "#FFCA28", "#8D6E63", "#5C6BC0", "#26C6DA"]
MATERIAL_COLORS: dict[str, str] = {}   # board id -> hex, populated in export_pdf


def _dia_color(dia) -> colors.Color:
    return colors.HexColor(DIA_COLORS.get(int(dia) if dia else 0, _DIA_DEFAULT))


def _band_color(band_id) -> colors.Color:
    return colors.HexColor(BAND_COLORS.get(band_id, BAND_COLOR_DEFAULT))


def _lighten(hex_color: str, amt: float) -> colors.Color:
    """Mix a colour toward white by `amt` (0..1)."""
    if not (hex_color and hex_color.startswith("#") and len(hex_color) == 7):
        hex_color = "#CFCFCF"
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return colors.Color((r + (255 - r) * amt) / 255, (g + (255 - g) * amt) / 255, (b + (255 - b) * amt) / 255)


def _material_fill(panel: Panel) -> colors.Color:
    """Faded bright pastel, consistent per material (arbitrary — does not match the real decor)."""
    base = MATERIAL_COLORS.get(panel.material, "#BDBDBD")
    return _lighten(base, 0.62)


def _depth_str(d) -> str:
    return "through" if d == "through" else f"{d} mm"


# ---- hole instance enumeration (expand multi for the diagram) — shared with the 3D viewer ----
def _edge_positions(h) -> list:
    return h.edge_positions()


def _surface_positions(h) -> list:
    return h.surface_positions()


# ---- small primitives ----
def _checkbox(c, x, y, s=3 * MM):
    c.saveState(); c.setLineWidth(0.6); c.rect(x, y, s, s, stroke=1, fill=0); c.restoreState()


def _swatch(c, x, y, color, s=3 * MM):
    c.saveState(); c.setFillColor(color); c.setStrokeColor(C_GREY); c.setLineWidth(0.4)
    c.rect(x, y, s, s, stroke=1, fill=1); c.restoreState()


def _diagram(c, panel: Panel, surface: str, scale: float, ox: float, oy: float, label: str):
    rw, rh = panel.width * scale, panel.height * scale
    c.saveState()

    # plate fill (light material tint) + outline
    c.setFillColor(_material_fill(panel))
    c.setStrokeColor(colors.HexColor("#616161"))
    c.setLineWidth(0.8)
    c.rect(ox, oy, rw, rh, stroke=1, fill=1)

    # banded edges in their band colour
    eb = panel.edge_banding
    edge_lines = {1: (ox, oy + rh, ox + rw, oy + rh), 3: (ox, oy, ox + rw, oy),
                  2: (ox + rw, oy, ox + rw, oy + rh), 4: (ox, oy, ox, oy + rh)}
    c.setLineWidth(3)
    for e, (x1, y1, x2, y2) in edge_lines.items():
        band_id = eb.band_for(e)
        if band_id:
            c.setStrokeColor(_band_color(band_id))
            c.line(x1, y1, x2, y2)

    # labels
    c.setFillColor(colors.black)
    c.setFont(FONT, 7)
    c.drawCentredString(ox + rw / 2, oy + rh + 2 * MM, label)
    c.setFont(FONT, 6)
    c.setFillColor(C_GREY)
    c.drawCentredString(ox + rw / 2, oy + rh - 3.4 * MM, "1")
    c.drawCentredString(ox + rw / 2, oy + 1.8 * MM, "3")
    c.drawRightString(ox + rw - 1 * MM, oy + rh / 2, "2")
    c.drawString(ox + 1 * MM, oy + rh / 2, "4")
    c.drawCentredString(ox + rw / 2, oy - 4 * MM, f"w {int(panel.width)}")
    c.saveState(); c.translate(ox - 3.5 * MM, oy + rh / 2); c.rotate(90)
    c.drawCentredString(0, 0, f"h {int(panel.height)}"); c.restoreState()
    c.setFillColor(colors.black)

    cap = min(rw, rh) * 0.45

    # edge holes: inward line whose length ~ drilling depth, coloured by diameter
    for h in panel.holes:
        if not h.is_edge:
            continue
        e = h.edge_no
        depth = h.depth if isinstance(h.depth, (int, float)) else 20
        L = max(2.0 * MM, min(depth * scale, cap))
        c.setStrokeColor(_dia_color(h.dia))
        c.setLineWidth(1.6)
        for p in _edge_positions(h):
            if e == 1:
                x = ox + p * scale; c.line(x, oy + rh, x, oy + rh - L)
            elif e == 3:
                x = ox + p * scale; c.line(x, oy, x, oy + L)
            elif e == 2:
                y = oy + p * scale; c.line(ox + rw, y, ox + rw - L, y)
            else:
                y = oy + p * scale; c.line(ox, y, ox + L, y)

    # surface holes for THIS face: circles coloured by diameter (hollow = through)
    for h in panel.holes:
        if h.face != surface:
            continue
        col = _dia_color(h.dia)
        c.setStrokeColor(col); c.setFillColor(col)
        through = h.depth == "through"
        r = max(1.0 * MM, (h.dia or 5) * scale / 2)
        for (hx, hy) in _surface_positions(h):
            c.circle(ox + hx * scale, oy + hy * scale, r, stroke=1, fill=0 if through else 1)

    c.setStrokeColor(colors.black); c.setFillColor(colors.black)
    c.restoreState()


def _row(c, x, y, cells, widths, bold=False, check=False, swatch=None, color=colors.black):
    if check:
        _checkbox(c, x - 6 * MM, y - 0.5 * MM)
    if swatch is not None:
        _swatch(c, x - 11 * MM, y - 0.5 * MM, swatch)
    c.setFont(FONT_BOLD if bold else FONT, 8)
    c.setFillColor(color)
    cx = x
    for cell, w in zip(cells, widths):
        c.drawString(cx, y, str(cell)); cx += w
    c.setFillColor(colors.black)
    return y - 5.2 * MM


def _heading(c, x, y, text, color):
    c.setFont(FONT_BOLD, 9.5); c.setFillColor(color)
    c.drawString(x, y, text); c.setFillColor(colors.black)
    return y - 5.5 * MM


def _table_size(c, panel: Panel, qty, board, thickness, y):
    x = MARGIN + 6 * MM
    y = _heading(c, MARGIN, y, "Size & material", C_DIM)
    y = _row(c, x, y, ["width", "height", "thickness", "qty", "grain"],
             [30 * MM, 30 * MM, 28 * MM, 22 * MM, 38 * MM], bold=True, color=C_DIM)
    grain = {"any": "0 — any", "height": "1 — along height", "width": "2 — along width"}.get(
        panel.grain, "2 — along width")
    y = _row(c, x, y, [f"{int(panel.width)} mm", f"{int(panel.height)} mm",
                       f"{thickness:g} mm", qty, grain],
             [30 * MM, 30 * MM, 28 * MM, 22 * MM, 38 * MM], check=True, color=C_DIM)
    c.setFont(FONT, 7.5); c.setFillColor(C_DIM)
    c.drawString(x, y, f"board: {board.name if board else panel.material}")
    c.setFillColor(colors.black)
    return y - 7 * MM


def _table_banding(c, proj: Project, panel: Panel, y):
    x = MARGIN + 6 * MM
    eb = panel.edge_banding
    glue = ("long edges (editor: kryjące długie)" if eb.glue_type == "long"
            else "short edges (editor: kryjące krótkie)")
    y = _heading(c, MARGIN, y, f"Edge banding   ·   covering: {glue}", C_BAND)
    y = _row(c, x, y, ["edge", "banded", "band model", "thick."],
             [26 * MM, 20 * MM, 60 * MM, 22 * MM], bold=True, color=C_BAND)
    for e in (1, 2, 3, 4):
        band_id = eb.band_for(e)
        if band_id:
            band = proj.edgeband(band_id)
            model = band.name if band else band_id
            th = f"{band.thickness:g} mm" if band else ""
            y = _row(c, x, y, [EDGE_NAMES[e], "yes", model, th],
                     [26 * MM, 20 * MM, 60 * MM, 22 * MM], check=True, swatch=_band_color(band_id),
                     color=C_BAND)
        else:
            y = _row(c, x, y, [EDGE_NAMES[e], "—", "", ""],
                     [26 * MM, 20 * MM, 60 * MM, 22 * MM], check=True, color=C_BAND)
    return y - 4 * MM


def _multi_str(h) -> str:
    if h.type != "multi":
        return "single"
    d = f" {h.direction}" if h.direction else ""
    return f"multi ×{h.count} @ {h.spacing}mm{d}"


def _table_drilling(c, panel: Panel, y):
    x = MARGIN + 6 * MM
    edge_holes = [h for h in panel.holes if h.is_edge]
    surf_holes = [h for h in panel.holes if h.is_surface]

    y = _heading(c, MARGIN, y, "Drilling — edge", C_DRILL)
    if edge_holes:
        y = _row(c, x, y, ["edge", "from", "Ø", "depth", "type"],
                 [26 * MM, 22 * MM, 16 * MM, 24 * MM, 50 * MM], bold=True, color=C_DRILL)
        for h in edge_holes:
            tag = "  (auto)" if h.src else ""
            y = _row(c, x, y, [EDGE_NAMES[h.edge_no], f"{h.frm} mm", f"{h.dia}",
                               _depth_str(h.depth), _multi_str(h) + tag],
                     [26 * MM, 22 * MM, 16 * MM, 24 * MM, 50 * MM], check=True,
                     swatch=_dia_color(h.dia), color=C_DRILL)
    else:
        c.setFont(FONT, 8); c.setFillColor(C_DRILL); c.drawString(x, y, "— none —")
        c.setFillColor(colors.black); y -= 5.2 * MM

    y -= 2 * MM
    y = _heading(c, MARGIN, y, "Drilling — surface", C_DRILL)
    if surf_holes:
        y = _row(c, x, y, ["face", "x", "y", "Ø", "depth", "type"],
                 [20 * MM, 22 * MM, 22 * MM, 16 * MM, 24 * MM, 50 * MM], bold=True, color=C_DRILL)
        for h in surf_holes:
            tag = "  (auto)" if h.src else ""
            y = _row(c, x, y, [h.face, f"{h.x}", f"{h.y}", f"{h.dia}",
                               _depth_str(h.depth), _multi_str(h) + tag],
                     [20 * MM, 22 * MM, 22 * MM, 16 * MM, 24 * MM, 50 * MM],
                     check=True, swatch=_dia_color(h.dia), color=C_DRILL)
    else:
        c.setFont(FONT, 8); c.setFillColor(C_DRILL); c.drawString(x, y, "— none —")
        c.setFillColor(colors.black); y -= 5.2 * MM
    return y


def _draw_panel_page(c, proj: Project, cab: Cabinet, panel: Panel, qty: int, idx: int, dest: str):
    c.bookmarkPage(dest)
    board = proj.board(panel.material) if panel.material else None
    thickness = proj.panel_thickness(panel)

    y = PH - MARGIN
    c.setFont(FONT_BOLD, 14)
    c.drawString(MARGIN, y - 4 * MM, f"P{idx}.  {panel.name}")
    c.setFont(FONT, 9)
    c.drawRightString(PW - MARGIN, y - 4 * MM, f"{cab.name}  ·  {cab.id}/{panel.id}")
    c.setStrokeColor(C_GREY); c.line(MARGIN, y - 6 * MM, PW - MARGIN, y - 6 * MM)
    c.setStrokeColor(colors.black)

    area_top = y - 12 * MM
    area_h = 75 * MM
    half = (PW - 2 * MARGIN - 10 * MM) / 2
    scale = min((half - 12 * MM) / max(panel.width, 1), (area_h - 14 * MM) / max(panel.height, 1))
    rw, rh = panel.width * scale, panel.height * scale
    base_y = area_top - rh - 6 * MM
    fx = MARGIN + (half - rw) / 2 + 4 * MM
    bx = MARGIN + half + 10 * MM + (half - rw) / 2 + 4 * MM
    _diagram(c, panel, "outer", scale, fx, base_y, "OUTER  ·  editor: przód (front)")
    _diagram(c, panel, "inner", scale, bx, base_y, "INNER  ·  editor: tył (back)")

    # orientation note (single panel frame; outer/inner = which face the drill enters)
    fd = _front_desc(panel.role)
    note = "Faces: outer = visible outside · inner = toward cavity (same x,y frame; face = drill side)."
    if fd:
        note = f"Cabinet FRONT edge = {fd}.   " + note
    c.setFont(FONT, 7.5); c.setFillColor(C_GREY)
    c.drawCentredString(PW / 2, base_y - 8 * MM, note)
    c.setFillColor(colors.black)

    ty = base_y - 14 * MM
    ty = _table_size(c, panel, qty, board, thickness, ty)
    ty = _table_banding(c, proj, panel, ty)
    ty = _table_drilling(c, panel, ty)

    c.setFont(FONT, 7); c.setFillColor(C_GREY)
    c.drawCentredString(PW / 2, MARGIN - 4 * MM, f"meble · {cab.id} · panel sheet P{idx}")
    c.setFillColor(colors.black)
    c.showPage()


def _draw_index(c, title: str, entries: list):
    def header():
        c.setFont(FONT_BOLD, 16); c.drawString(MARGIN, PH - MARGIN - 4 * MM, title)
        c.setFont(FONT, 9); c.setFillColor(C_GREY)
        c.drawString(MARGIN, PH - MARGIN - 10 * MM, "Click a row to jump to its panel sheet.")
        c.setFillColor(colors.black)

    header()
    y = PH - MARGIN - 18 * MM
    c.setFont(FONT, 9)
    for idx, dest, cab, panel, qty in entries:
        if y < MARGIN + 10 * MM:
            c.showPage(); header(); y = PH - MARGIN - 18 * MM; c.setFont(FONT, 9)
        c.drawString(MARGIN, y, f"P{idx}.  {cab.id} / {panel.name}   "
                                f"{int(panel.width)}×{int(panel.height)} mm   ×{qty}")
        c.linkAbsolute("", dest, (MARGIN - 1 * MM, y - 1.5 * MM, PW - MARGIN, y + 4 * MM))
        c.setFillColor(colors.HexColor("#1565C0")); c.drawRightString(PW - MARGIN, y, "→")
        c.setFillColor(colors.black)
        y -= 6 * MM
    c.showPage()


def export_pdf(proj: Project, cabinets: list[Cabinet], out_path: Path, title: str = "Panels") -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not _register_fonts():
        print("  warn: no Unicode TTF found — Polish characters may not render (install Arial/DejaVu).")
    # deterministic colours across all panels (sorted ids -> palette)
    BAND_COLORS.update(band_color_map(proj.edgebands.keys()))
    for i, bid in enumerate(sorted(proj.boards)):
        MATERIAL_COLORS[bid] = _MATERIAL_PALETTE[i % len(_MATERIAL_PALETTE)]

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

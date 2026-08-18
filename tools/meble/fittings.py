"""Fitting -> hole stamping.

A fitting references the panels it joins. Applying it computes the drill holes from the hardware's
drill pattern and writes them onto those panels, tagged with `src: <fitting id>`. Re-applying is safe:
only holes whose `src` matches a (re)applied fitting are replaced; manual holes (no `src`) are untouched.

A fitting may opt out entirely with `drilling: manual` (its holes are hand-derived and tagged with its
id) or `drilling: none` (it has no holes by design — a drawer slide mounted on site). Both are skipped
silently; only `drilling: stamped`, the default, is expected to produce holes here.

v1 implements butt-joint hardware that has both a `face` and an `edge` drill pattern (confirmat, dowel),
and only where the seam runs along one of the through panel's own edges (`seam.through_edge`). A mid-face
T-joint — an internal gable landing on a top/bottom panel, say — is recognised but skipped (warn), as is
cam/cup/slide hardware (minifix, hinge, slide); those holes are hand-written for now.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

_rt = YAML()                 # round-trip: preserves comments/formatting when we write back
_rt.preserve_quotes = True
_rt.width = 4096


def _thickness(panel: dict, boards: dict) -> float:
    if panel.get("thickness") is not None:
        return panel["thickness"]
    b = boards.get(panel.get("material"))
    return (b.get("thickness") if b else None) or 18


def _series(positions: list):
    """If positions are an evenly-spaced run (>=2, equal gaps), return (start, count, spacing) so we can
    emit ONE multi (bulk) hole instead of many singles. Else None."""
    if len(positions) >= 2:
        gap = positions[1] - positions[0]
        if gap > 0 and all(positions[i + 1] - positions[i] == gap for i in range(len(positions) - 1)):
            return positions[0], len(positions), gap
    return None


def _stamp_butt_joint(fitting: dict, panels_by_id: dict, hw: dict, boards: dict) -> dict:
    """Butt joint: screw/dowel passes through `through` panel's face toward `into` panel's edge.

    Stamps a face/surface hole on the through panel (if the hardware has a `face` pattern) and an edge
    hole on the into panel (if it has an `edge` pattern). Confirmat = Ø8 face + Ø4 edge. Dowel = Ø8 + Ø8.
    Evenly-spaced runs are emitted as a single MULTI hole (bulk) to minimise manual entry in the editor.
    """
    fid = fitting["id"]
    through = panels_by_id[fitting["through"]]
    into = panels_by_id[fitting["into"]]
    seam = fitting.get("seam", {})
    te = int(seam["through_edge"])
    ie = int(seam["into_edge"])
    positions = list(fitting.get("at", []))
    drill = hw.get("drill", {})
    series = _series(positions)

    t_into = _thickness(into, boards)
    W = through.get("width", 0)
    H = through.get("height", 0)
    face = fitting.get("through_face", "outer")   # confirmat head sits on the OUTER (visible) face

    out: dict[str, list] = {}

    if "face" in drill:
        fd = drill["face"].get("dia")
        fdepth = drill["face"].get("depth", "through")   # confirmat clearance = through-hole
        # the screw row runs along the seam: along X for a horizontal seam, along Y for a vertical one
        def face_xy(a):
            if te in (1, 3):
                return a, (t_into / 2 if te == 3 else H - t_into / 2)
            return (t_into / 2 if te == 4 else W - t_into / 2), a
        direction = "x" if te in (1, 3) else "y"
        holes = []
        if series:
            start, count, gap = series
            x, y = face_xy(start)
            holes.append({"face": face, "x": round(x, 1), "y": round(y, 1), "dia": fd, "depth": fdepth,
                          "type": "multi", "count": count, "spacing": gap, "direction": direction, "src": fid})
        else:
            for a in positions:
                x, y = face_xy(a)
                holes.append({"face": face, "x": round(x, 1), "y": round(y, 1),
                              "dia": fd, "depth": fdepth, "type": "single", "src": fid})
        out.setdefault(fitting["through"], []).extend(holes)

    if "edge" in drill:
        ed = drill["edge"].get("dia")
        edepth = drill["edge"].get("depth")
        if series:
            start, count, gap = series
            holes = [{"face": f"edge{ie}", "from": start, "dia": ed, "depth": edepth,
                      "type": "multi", "count": count, "spacing": gap, "src": fid}]
        else:
            holes = [{"face": f"edge{ie}", "from": a, "dia": ed, "depth": edepth,
                      "type": "single", "src": fid} for a in positions]
        out.setdefault(fitting["into"], []).extend(holes)

    return out


def apply_fittings(cabinet: dict, hardware_by_id: dict, boards_by_id: dict,
                   only: Optional[set] = None) -> tuple[set, list[str], int]:
    """Mutate `cabinet` (a dict) in place: stamp holes from its fittings onto its panels.

    Returns (applied_fitting_ids, warnings, holes_added).
    """
    panels = cabinet.get("panels", []) or []
    panels_by_id = {p["id"]: p for p in panels}
    fittings = (cabinet.get("assembly") or {}).get("fittings", []) or []

    applied: set = set()
    warnings: list[str] = []
    stamped: dict[str, list] = {}

    for f in fittings:
        fid = f.get("id")
        if only is not None and fid not in only:
            continue
        hw = hardware_by_id.get(f.get("hardware"))
        if hw is None:
            warnings.append(f"fitting '{fid}': unknown hardware '{f.get('hardware')}' (skipped)")
            continue
        # DELIBERATELY not stamped, and therefore NOT a warning:
        #   manual — the holes exist on the panels, hand-derived and tagged `src: <this id>` (hinge
        #            cups and plates, shelf pins — none of them butt joints, so the perimeter maths
        #            below cannot produce them). The merge step keeps them, because a fitting that is
        #            never `applied` never has its holes dropped.
        #   none   — there are no holes at all and there should not be (drawer slides, mounted on
        #            site). The fitting exists only so the hardware still reaches the buy list.
        # Before this, every one of these printed "not implemented (skipped)" on every single run —
        # which is how a warning stops being read.
        if f.get("drilling", "stamped") in ("manual", "none"):
            continue
        for ref in ("through", "into"):
            if f.get(ref) and f[ref] not in panels_by_id:
                warnings.append(f"fitting '{fid}': panel '{f[ref]}' not found (skipped)")
                break
        else:
            drill = hw.get("drill", {})
            seam = f.get("seam") or {}
            is_butt = ("face" in drill or "edge" in drill) and f.get("through") and f.get("into")
            if is_butt and seam.get("through_edge") is not None:
                res = _stamp_butt_joint(f, panels_by_id, hw, boards_by_id)
                for pid, holes in res.items():
                    stamped.setdefault(pid, []).extend(holes)
                applied.add(fid)
            elif is_butt:
                # No `through_edge` -> the seam is not along one of the through panel's own edges, so the
                # screw meets it mid-face (a T-joint, e.g. an internal gable landing on a shelf/top). The
                # perimeter maths below does not apply; those holes are hand-written.
                warnings.append(
                    f"fitting '{fid}': seam has no `through_edge`, so this is a mid-face (T) joint — "
                    f"stamping it is not implemented; its holes must be hand-written (skipped)")
            else:
                warnings.append(
                    f"fitting '{fid}': stamping for hardware type '{hw.get('type')}' not implemented "
                    f"yet (skipped — comes with drawers/fronts)")

    # merge: drop previously-stamped holes from these fittings, keep manual holes, add fresh stamps
    added = 0
    for p in panels:
        original = list(p.get("holes") or [])
        holes = [h for h in original if h.get("src") not in applied]
        new = stamped.get(p["id"], [])
        holes.extend(new)
        added += len(new)
        # /!\ ONLY WRITE BACK WHEN SOMETHING ACTUALLY CHANGED. Assigning `p["holes"]` replaces the
        #     ruamel sequence, and every comment attached to an item inside it is lost with it — so
        #     an unconditional assignment quietly ate a line of design reasoning from EVERY panel on
        #     EVERY run, including cabinets where `fit` stamped nothing at all. The comments in these
        #     files are the reasoning behind the cuts; losing them silently is worse than any hole
        #     this function stamps.
        if new or len(holes) != len(original):
            p["holes"] = holes

    return applied, warnings, added


def fit_cabinet_file(cabinet_path: Path, root: Path, only: Optional[set] = None) -> dict:
    """Round-trip-load a cabinet YAML, stamp holes, write it back. Returns a summary dict."""
    hardware_by_id, boards_by_id = _load_library_min(root)
    with open(cabinet_path, "r", encoding="utf-8") as f:
        cab = _rt.load(f)

    applied, warnings, added = apply_fittings(cab, hardware_by_id, boards_by_id, only=only)

    with open(cabinet_path, "w", encoding="utf-8") as f:
        _rt.dump(cab, f)

    return {"applied": sorted(applied), "warnings": warnings, "holes_added": added,
            "path": str(cabinet_path)}


def _load_library_min(root: Path) -> tuple[dict, dict]:
    """Load just hardware + boards as plain dicts (id -> dict)."""
    safe = YAML(typ="safe")
    with open(root / "library" / "hardware.yaml", "r", encoding="utf-8") as f:
        hardware = {h["id"]: h for h in (safe.load(f) or {}).get("hardware", [])}
    with open(root / "library" / "materials.yaml", "r", encoding="utf-8") as f:
        boards = {b["id"]: b for b in (safe.load(f) or {}).get("boards", [])}
    return hardware, boards

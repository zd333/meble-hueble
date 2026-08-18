"""`meble fit` stamps holes onto panels. The safety properties matter more than the geometry.

The contract in CLAUDE.md is that `fit` is idempotent and safe: it replaces only holes whose `src`
matches a fitting it applied, and **manual holes are never touched**. If that ever stops being true,
re-running `fit` silently deletes hand-derived drilling.
"""
from __future__ import annotations

import copy

from meble.fittings import _series, apply_fittings

CONFIRMAT = {"id": "confirmat-45", "type": "confirmat",
             "drill": {"face": {"dia": 8, "depth": "through"}, "edge": {"dia": 4, "depth": 35}}}
HINGE = {"id": "hinge-euro", "type": "hinge", "drill": {"cup": {"dia": 35, "depth": 12}}}
SLIDE = {"id": "slide-bb-350", "type": "slide", "sold_as": "pair"}
BOARDS = {"u604-18": {"id": "u604-18", "thickness": 18}}


def cabinet(fittings, *, holes_a=(), holes_b=()):
    return {
        "id": "c",
        "panels": [
            {"id": "a", "material": "u604-18", "width": 600, "height": 400, "holes": list(holes_a)},
            {"id": "b", "material": "u604-18", "width": 600, "height": 400, "holes": list(holes_b)},
        ],
        "assembly": {"fittings": list(fittings)},
    }


def butt(at, fid="cf1", **kw):
    f = {"id": fid, "hardware": "confirmat-45", "through": "a", "into": "b",
         "seam": {"through_edge": 3, "into_edge": 1}, "at": list(at)}
    f.update(kw)
    return f


def apply(cab, only=None):
    return apply_fittings(cab, {"confirmat-45": CONFIRMAT, "hinge-euro": HINGE,
                                "slide-bb-350": SLIDE}, BOARDS, only=only)


def holes(cab, pid):
    return next(p for p in cab["panels"] if p["id"] == pid)["holes"]


# ------------------------------------------------------------------ the safety contract

def test_manual_holes_are_never_touched():
    manual = {"face": "inner", "x": 37, "y": 100, "dia": 5, "depth": 13, "type": "single"}
    cab = cabinet([butt([50, 200, 350])], holes_a=[manual])
    apply(cab)
    assert manual in holes(cab, "a")


def test_reapplying_is_idempotent():
    cab = cabinet([butt([50, 200, 350])])
    apply(cab)
    first = copy.deepcopy(cab["panels"])
    apply(cab)
    assert cab["panels"] == first


def test_reapplying_replaces_only_its_own_stamps():
    cab = cabinet([butt([50, 200, 350], fid="cf1")])
    apply(cab)
    other = {"face": "outer", "x": 1, "y": 1, "dia": 8, "depth": "through",
             "type": "single", "src": "cf-other"}
    holes(cab, "a").append(other)
    apply(cab, only={"cf1"})
    assert other in holes(cab, "a")
    assert sum(1 for h in holes(cab, "a") if h.get("src") == "cf1") == 1


def test_only_restricts_which_fittings_are_applied():
    cab = cabinet([butt([50, 200], fid="cf1"), butt([100, 300], fid="cf2")])
    applied, _, _ = apply(cab, only={"cf1"})
    assert applied == {"cf1"}
    assert {h.get("src") for h in holes(cab, "a")} == {"cf1"}


# ------------------------------------------------------------------ what it refuses to stamp

def test_mid_face_t_joint_warns_and_stamps_nothing():
    """No `through_edge` means the seam is not on the through panel's own edge; the perimeter maths
    does not apply, so it must skip rather than compute a plausible wrong hole."""
    f = butt([50, 200])
    f["seam"] = {"into_edge": 1}
    cab = cabinet([f])
    applied, warnings, added = apply(cab)
    assert applied == set() and added == 0
    assert any("mid-face (T) joint" in w for w in warnings)


def test_unimplemented_hardware_warns_and_stamps_nothing():
    cab = cabinet([{"id": "hg1", "hardware": "hinge-euro", "through": "a", "into": "b",
                    "seam": {"through_edge": 3, "into_edge": 1}, "at": [100]}])
    applied, warnings, added = apply(cab)
    assert applied == set() and added == 0
    assert any("not implemented" in w for w in warnings)


def test_unknown_hardware_warns_and_stamps_nothing():
    cab = cabinet([butt([50], hardware="no-such")])
    applied, warnings, added = apply(cab)
    assert applied == set() and added == 0
    assert any("unknown hardware" in w for w in warnings)


def test_missing_panel_warns_and_stamps_nothing():
    cab = cabinet([butt([50], into="ghost")])
    applied, warnings, added = apply(cab)
    assert applied == set() and added == 0
    assert any("not found" in w for w in warnings)


# ------------------------------------------------------------------ bulk drilling

def test_evenly_spaced_screws_collapse_into_one_multi_hole():
    """One editor entry instead of N — CLAUDE.md's 'prefer bulk drilling' rule, enforced."""
    cab = cabinet([butt([50, 200, 350])])
    apply(cab)
    (face,) = holes(cab, "a")
    assert face["type"] == "multi" and face["count"] == 3 and face["spacing"] == 150
    (edge,) = holes(cab, "b")
    assert edge["type"] == "multi" and edge["count"] == 3 and edge["spacing"] == 150


def test_irregular_positions_stay_single():
    cab = cabinet([butt([50, 200, 500])])
    apply(cab)
    assert [h["type"] for h in holes(cab, "a")] == ["single"] * 3


def test_series_detection():
    assert _series([50, 82, 114]) == (50, 3, 32)
    assert _series([50, 200]) == (50, 2, 150)
    assert _series([50, 200, 500]) is None
    assert _series([100]) is None
    assert _series([50, 50, 50]) is None          # zero gap is not a run


# ------------------------------------------------------------------ geometry

def test_confirmat_puts_the_head_on_the_face_and_the_pilot_in_the_edge():
    """Ø8 clearance through the through-panel's face, Ø4 into the other panel's edge."""
    cab = cabinet([butt([50, 200, 350])])
    apply(cab)
    (face,) = holes(cab, "a")
    (edge,) = holes(cab, "b")
    assert (face["dia"], face["depth"], face["face"]) == (8, "through", "outer")
    assert (edge["dia"], edge["depth"], edge["face"]) == (4, 35, "edge1")


def test_the_face_row_is_offset_half_the_mating_panel_thickness():
    """The screw must land in the middle of the 18 mm edge it enters, so 9 mm in from the seam."""
    cab = cabinet([butt([50, 200, 350])])          # through_edge 3 = bottom
    apply(cab)
    (face,) = holes(cab, "a")
    assert face["y"] == 9.0 and face["x"] == 50
    assert face["direction"] == "x"


def test_a_vertical_seam_runs_the_row_down_the_y_axis():
    cab = cabinet([butt([50, 200, 350], seam={"through_edge": 4, "into_edge": 1})])
    apply(cab)
    (face,) = holes(cab, "a")
    assert face["x"] == 9.0 and face["y"] == 50
    assert face["direction"] == "y"


# ------------------------------------------------------------------ fittings that opt out of stamping

def test_drilling_manual_stamps_nothing_and_says_nothing():
    """Hinge and pin holes are hand-derived on purpose. Warning about them on every run is how a
    warning stops being read — that noise is what `drilling:` removes."""
    f = butt([50, 200], fid="hg1")
    f["drilling"] = "manual"
    cab = cabinet([f])
    applied, warnings, added = apply(cab)
    assert applied == set() and added == 0
    assert warnings == []


def test_drilling_none_stamps_nothing_and_says_nothing():
    """A drawer slide is mounted on site: no holes anywhere, by design."""
    cab = cabinet([{"id": "sl1", "hardware": "slide-bb-350", "drilling": "none", "quantity": 1}])
    applied, warnings, added = apply(cab)
    assert applied == set() and added == 0
    assert warnings == []


def test_a_manual_fittings_hand_written_holes_survive():
    """The holes carry `src: hg1`, but the fitting is never `applied`, so the merge must keep them."""
    hand = {"face": "inner", "x": 37, "y": 100, "dia": 5, "depth": 13, "src": "hg1"}
    f = butt([50], fid="hg1"); f["drilling"] = "manual"
    cab = cabinet([f], holes_a=[hand])
    apply(cab)
    assert hand in holes(cab, "a")


def test_default_is_still_stamped():
    cab = cabinet([butt([50, 200, 350])])
    applied, _, added = apply(cab)
    assert applied == {"cf1"} and added == 2


# ------------------------------------------------------------------ comment preservation

def test_untouched_panels_are_not_rewritten():
    """Assigning `p["holes"]` replaces the ruamel sequence and every comment inside it goes with it.
    A panel `fit` did not touch must therefore not be written back at all — otherwise a run that
    stamps nothing still eats a line of design reasoning from every cabinet."""
    manual = {"face": "inner", "x": 37, "y": 100, "dia": 5, "depth": 13}
    cab = cabinet([], holes_a=[manual])
    before = holes(cab, "a")
    apply(cab)
    assert holes(cab, "a") is before, "the holes list was replaced despite nothing changing"


def test_panels_that_gain_holes_are_rewritten():
    cab = cabinet([butt([50, 200, 350])])
    before = holes(cab, "a")
    apply(cab)
    assert holes(cab, "a") is not before

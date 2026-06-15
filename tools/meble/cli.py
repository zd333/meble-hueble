"""meble command-line interface.

  python -m meble validate      [--apartment A | --set S | --cabinet C]
  python -m meble scaffold KIND --width W --height H --depth D [--id ID --name N --material M --edgeband E]
  python -m meble fit           --cabinet C [--only f1,f2]
  python -m meble csv           (--set S | --cabinet C | --apartment A) [--out DIR]
  python -m meble pdf           (--set S | --cabinet C | --apartment A) [--out FILE]
  python -m meble compile-scene (--set S | --cabinet C | --apartment A) [--out FILE]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .model import cabinets_for_scope, load_project


def _scope_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--apartment")
    p.add_argument("--set", dest="set_")
    p.add_argument("--cabinet")


def _scope_label(args) -> str:
    return args.cabinet or args.set_ or args.apartment or "all"


def _resolve(proj, args):
    return cabinets_for_scope(proj, apartment=args.apartment, set_=args.set_, cabinet=args.cabinet)


def cmd_validate(args) -> int:
    from .validate import validate
    proj = load_project()
    cabs = _resolve(proj, args)
    errors, warnings = validate(proj, cabs)
    for w in warnings:
        print(f"  warn: {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    n = len(cabs)
    if errors:
        print(f"\n✗ {len(errors)} error(s), {len(warnings)} warning(s) across {n} cabinet(s).")
        return 1
    print(f"✓ {n} cabinet(s) OK ({len(warnings)} warning(s)).")
    return 0


def cmd_list(args) -> int:
    proj = load_project()
    print("Apartments:")
    for apt in proj.apartments.values():
        print(f"  {apt.id} — {apt.name}   rooms: {', '.join(apt.rooms)}")
        for fs in apt.sets.values():
            print(f"    set '{fs.id}' ({fs.name}):")
            for cid in fs.cabinet_ids:
                cab = proj.cabinet(cid)
                if not cab:
                    print(f"      • {cid}  (MISSING)")
                elif cab.kind == "custom":
                    pieces = sum(q for _, q in proj.expanded_panels(cab))
                    print(f"      • {cab.id:16} {cab.name}  [{cab.category}]  "
                          f"{len(cab.panels)} panels / {pieces} pieces")
                else:
                    print(f"      • {cab.id:16} {cab.name}  [readymade {cab.raw.get('system', '')}]")
    print("\nLibrary:")
    print(f"  boards:    {', '.join(proj.boards) or '—'}")
    print(f"  edgebands: {', '.join(proj.edgebands) or '—'}")
    print(f"  hardware:  {', '.join(proj.hardware) or '—'}")
    print(f"  parts:     {', '.join(proj.parts) or '—'}")
    print(f"  units:     {', '.join(proj.units) or '—'}")
    return 0


def cmd_review(args) -> int:
    from .model import Cabinet
    from .review import review
    proj = load_project()
    cabs = _resolve(proj, args)
    if not args.cabinet:                       # also lint reusable library parts (drawer boxes, etc.)
        cabs = list(cabs) + [Cabinet.from_dict(p) for p in proj.parts.values()]
    findings = review(proj, cabs)
    order = {"info": 0, "warn": 1, "error": 2}
    for f in sorted(findings, key=lambda x: order[x.severity]):
        label = {"info": "info ", "warn": "warn ", "error": "ERROR"}[f.severity]
        print(f"  {label} [{f.cabinet}] {f.rule}: {f.message}")
    errs = sum(1 for f in findings if f.severity == "error")
    warns = sum(1 for f in findings if f.severity == "warn")
    infos = sum(1 for f in findings if f.severity == "info")
    mark = "✗" if errs else "✓"
    print(f"\n{mark} review: {errs} error(s), {warns} warning(s), {infos} info across {len(cabs)} cabinet(s).")
    return 1 if errs else 0


def cmd_scaffold(args) -> int:
    from .templates import scaffold, to_yaml
    cab = scaffold(args.kind, args.width, args.height, args.depth,
                   cab_id=args.id, name=args.name, material=args.material, edgeband=args.edgeband)
    print(to_yaml(cab), end="")
    print(f"\n# ^ save under apartments/<a>/sets/<s>/cabinets/{cab['id']}.yaml, "
          f"then run:  python -m meble fit --cabinet {cab['id']}", file=sys.stderr)
    return 0


def cmd_fit(args) -> int:
    from .fittings import fit_cabinet_file
    proj = load_project()
    cab = proj.cabinet(args.cabinet)
    if not cab or not cab.source_path:
        print(f"✗ cabinet '{args.cabinet}' not found", file=sys.stderr)
        return 1
    only = set(args.only.split(",")) if args.only else None
    res = fit_cabinet_file(cab.source_path, proj.root, only=only)
    for w in res["warnings"]:
        print(f"  warn: {w}")
    print(f"✓ stamped {res['holes_added']} hole(s) from {len(res['applied'])} fitting(s) "
          f"{res['applied']} into {Path(res['path']).name}")
    return 0


def cmd_csv(args) -> int:
    from .csv_export import export_csv
    proj = load_project()
    cabs = _resolve(proj, args)
    outdir = Path(args.out) if args.out else proj.root / "out" / "csv"
    written = export_csv(proj, cabs, outdir)
    if not written:
        print("  (no custom panels in scope)")
    for p in written:
        print(f"✓ {p}")
    return 0


def cmd_pdf(args) -> int:
    from .pdf_export import export_pdf
    proj = load_project()
    cabs = _resolve(proj, args)
    label = _scope_label(args)
    out = Path(args.out) if args.out else proj.root / "out" / "pdf" / f"{label}.pdf"
    export_pdf(proj, cabs, out, title=f"Panele — {label}")
    print(f"✓ {out}")
    return 0


def cmd_compile_scene(args) -> int:
    from .scene import write_scene
    proj = load_project()
    cabs = _resolve(proj, args)
    label = _scope_label(args)
    out = Path(args.out) if args.out else proj.root / "out" / "scene.json"
    write_scene(proj, cabs, out, name=label)
    render = proj.root / "render" / "compile.py"
    print(f"✓ {out}")
    print(f"  render:  blender --background --python {render} -- {out} "
          f"{proj.root / 'out' / (label + '.png')}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="meble", description="MFC cabinet design tools.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="list apartments, sets, cabinets and library contents")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("validate", help="static consistency checks"); _scope_args(p)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("review", help="domain linter — well-known cabinetmaking pitfalls"); _scope_args(p)
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("scaffold", help="seed a new cabinet YAML (prints to stdout)")
    p.add_argument("kind", choices=["base", "wall", "tall", "wardrobe"])
    p.add_argument("--width", type=float, required=True)
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--depth", type=float, required=True)
    p.add_argument("--id"); p.add_argument("--name")
    p.add_argument("--material", default="w980-18"); p.add_argument("--edgeband", default="eb-w980-1")
    p.set_defaults(func=cmd_scaffold)

    p = sub.add_parser("fit", help="stamp holes from fittings onto panels (safe/idempotent)")
    p.add_argument("--cabinet", required=True)
    p.add_argument("--only", help="comma-separated fitting ids to (re)apply")
    p.set_defaults(func=cmd_fit)

    p = sub.add_parser("csv", help="export the meble.pl PRO100 CSV (per board)"); _scope_args(p)
    p.add_argument("--out", help="output directory")
    p.set_defaults(func=cmd_csv)

    p = sub.add_parser("pdf", help="export per-panel PDF spec sheets"); _scope_args(p)
    p.add_argument("--out", help="output file")
    p.set_defaults(func=cmd_pdf)

    p = sub.add_parser("compile-scene", help="resolve a scope to scene.json for Blender"); _scope_args(p)
    p.add_argument("--out", help="output file")
    p.set_defaults(func=cmd_compile_scene)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, FileNotFoundError, ValueError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

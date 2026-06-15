# meble-hueble 💪

Workspace for designing flat-pack **MFC cabinet furniture** and ordering the cut panels online at
[centrum.meble.pl](https://centrum.meble.pl).

- Designs are **YAML** under `apartments/` (source of truth).
- Reusable boards/bands/hardware/units live in `library/`.
- Domain knowledge + conventions are in [`CLAUDE.md`](CLAUDE.md) and [`docs/`](docs/).
- Tools (CSV export, PDF spec sheets, interactive 3D viewer, validation) live in `tools/` and are driven by
  the skills in `.claude/skills/`.

**Start here:** read [`CLAUDE.md`](CLAUDE.md). It explains the data model, the workflow, and how the
tools turn a design into a meble.pl order + a 3D preview.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r tools/requirements.txt
export PYTHONPATH=tools

python -m meble validate --apartment bohaterow      # check designs
python -m meble csv  --set kitchen                  # -> out/csv/*.csv  (import into meble.pl)
python -m meble pdf  --set kitchen                  # -> out/pdf/*.pdf  (manual-entry spec sheets)
python -m meble view --set kitchen                  # interactive 3D viewer (opens in your browser)
```

See `.claude/skills/` for the guided workflows (`design-cabinet`, `generate-order-csv`,
`generate-panel-pdf`, `view-3d`, `validate-design`).

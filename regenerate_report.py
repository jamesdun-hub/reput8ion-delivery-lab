r"""
Regenerate the participant report.docx from already-saved session files.

No transcription, no API call, no cost. Reads the metrics.json and
narrative.json that a previous run saved, and re-renders report.docx
using the CURRENT report.py. Use this to see layout changes or to produce
the report for a session that was run in coaching mode (which generates
the dashboard but not the Word document).

Usage (from the project folder):
    python regenerate_report.py "output\Mark Mohan 1-4 June 2026"

If no folder is given it defaults to the most recently modified output folder.
The report is written to report-regenerated.docx in the session folder.
"""

import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR  = PROJECT_DIR / "output"


def _load_config() -> dict:
    import yaml
    cfg_path = PROJECT_DIR / "config.yaml"
    if cfg_path.exists():
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return {}


def _pick_folder() -> Path:
    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
        if not folder.is_absolute():
            folder = PROJECT_DIR / folder
        return folder
    subdirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir()]
    if not subdirs:
        raise SystemExit("No output folders found. Run a session first.")
    return max(subdirs, key=lambda d: d.stat().st_mtime)


def main() -> None:
    folder = _pick_folder()
    print(f"[REGEN] Using {folder}")

    metrics_path   = folder / "metrics.json"
    narrative_path = folder / "narrative.json"

    if not metrics_path.exists():
        raise SystemExit(f"metrics.json not found in {folder}")
    if not narrative_path.exists():
        raise SystemExit(f"narrative.json not found in {folder}")

    metrics   = json.loads(metrics_path.read_text(encoding="utf-8"))
    narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
    config    = _load_config()

    # Parse candidate / session / date from the folder name where possible.
    # Folder names follow the pattern "Candidate Name-D Month YYYY".
    name = folder.name
    parts = name.rsplit("-", 1)
    candidate = parts[0].strip() if len(parts) == 2 else name
    date      = parts[1].strip() if len(parts) == 2 else ""

    context = {
        "candidate": candidate,
        "session":   "Session report",
        "date":      date,
    }

    from src.report import render_report

    out_path = folder / "report-regenerated.docx"
    render_report(
        metrics=metrics,
        narrative=narrative,
        context=context,
        config=config,
        out_path=str(out_path),
    )
    print(f"[REGEN] Written: {out_path}")

    # Open in Word if available
    import os
    try:
        os.startfile(str(out_path))
        print("[REGEN] Opened in default application.")
    except Exception:
        print("[REGEN] Could not auto-open — open manually.")


if __name__ == "__main__":
    main()

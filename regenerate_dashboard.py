r"""
Regenerate a coach dashboard from already-saved session files.

No transcription, no API call, no cost. Reads the metrics.json,
narrative.json and transcript_words.json that a previous run saved, and
re-renders dashboard.html using the CURRENT dashboard.py. Use this to see
layout changes without re-running a whole session.

Usage (from the project folder):
    python regenerate_dashboard.py "output\Damien L v2-3 June 2026"

If no folder is given it defaults to the most recently modified output folder.
The question-handling section will only appear if the saved narrative.json
already contains a 'question_handling' block (older runs predate it).
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from src.dashboard import generate_dashboard

PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / "output"


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
    # default: most recently modified output subfolder
    subdirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir()]
    if not subdirs:
        raise SystemExit("No output folders found. Run a session first.")
    return max(subdirs, key=lambda d: d.stat().st_mtime)


def _reconstruct_transcript(words_json: list) -> SimpleNamespace:
    """Rebuild the minimal transcript object the renderer reads:
    .words (each with .text/.start/.end) and .speaker_summary."""
    words = [
        SimpleNamespace(
            text=w.get("text", ""),
            start=w.get("start", 0.0),
            end=w.get("end", 0.0),
            speaker=w.get("speaker"),
        )
        for w in words_json
    ]
    # Saved interviewee words have no speaker field — single-speaker view is fine
    speaker_summary = {}
    return SimpleNamespace(words=words, speaker_summary=speaker_summary)


def _reconstruct_prosody(metrics: dict) -> SimpleNamespace:
    """Rebuild a minimal prosody stand-in from saved metrics so pitch renders."""
    pitch = metrics.get("pitch", {})
    pitch_windows = pitch.get("windows", []) or []
    measured = pitch.get("status") != "not_measured"
    return SimpleNamespace(pitch_windows=pitch_windows, pitch_measured=measured)


def _maybe_add_question_handling(narrative: dict, folder: Path, metrics: dict, config: dict) -> dict:
    """If the saved narrative has no question_handling but a full two-speaker
    transcript exists, rebuild just that block with a single coach call.
    Requires OPENAI_API_KEY; otherwise leaves narrative unchanged."""
    import os
    if narrative.get("question_handling"):
        return narrative
    full_path = folder / "transcript_full.json"
    if not full_path.exists():
        print("[REGEN] No transcript_full.json — question handling cannot be "
              "rebuilt on regeneration. Run a fresh live session to capture it.")
        return narrative
    if not os.environ.get("OPENAI_API_KEY"):
        print("[REGEN] transcript_full.json present but OPENAI_API_KEY unset — "
              "skipping question-handling rebuild (no cost incurred).")
        return narrative

    from src.pipeline import _build_qa_transcript
    from src.metrics import Word
    from src.coach import generate_coaching_narrative, CoachContext

    full = json.loads(full_path.read_text(encoding="utf-8"))
    words = [Word(text=w["text"], start=w["start"], end=w["end"], speaker=w.get("speaker"))
             for w in full.get("words", [])]
    qa = _build_qa_transcript(words, full.get("interviewee_id"))
    if not qa:
        print("[REGEN] No interviewer turns found in full transcript.")
        return narrative

    print(f"[REGEN] Rebuilding question handling from {qa.count('INTERVIEWER:')} pairs (one coach call)...")
    ctx = CoachContext(candidate_name=folder.name, session_label="Mock interview", session_date="")
    fresh = generate_coaching_narrative(
        metrics, ctx, config, transcript_text=None, qa_transcript_text=qa,
    )
    if fresh.get("question_handling"):
        narrative["question_handling"] = fresh["question_handling"]
        (folder / "narrative.json").write_text(json.dumps(narrative, indent=2), encoding="utf-8")
        print("[REGEN] question_handling added and narrative.json updated.")
    return narrative


def main() -> None:
    folder = _pick_folder()
    print(f"[REGEN] Using {folder}")

    metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
    narrative = json.loads((folder / "narrative.json").read_text(encoding="utf-8"))
    words_json = json.loads((folder / "transcript_words.json").read_text(encoding="utf-8"))

    config = _load_config()
    narrative = _maybe_add_question_handling(narrative, folder, metrics, config)

    transcript_data = _reconstruct_transcript(words_json)
    prosody_data = _reconstruct_prosody(metrics)

    # Parse candidate/session/date from the folder name where possible
    name = folder.name
    context = {"candidate": name, "session": "Mock interview", "date": ""}

    out_path = folder / "dashboard-regenerated.html"
    generate_dashboard(
        metrics=metrics,
        prosody_data=prosody_data,
        transcript_data=transcript_data,
        context=context,
        config=config,
        out_path=str(out_path),
        narrative=narrative,
        auto_open=True,
    )
    print(f"[REGEN] Written and opened: {out_path}")
    if "question_handling" not in narrative:
        print("[REGEN] Note: this saved narrative predates question_handling, "
              "so that section will be absent. Everything else reflects the new layout.")


if __name__ == "__main__":
    main()

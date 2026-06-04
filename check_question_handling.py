"""
Diagnostic: confirm question-handling fired on a session.

Run after a live session (or after regenerate_dashboard.py with an API key)
to check that the narrative carries a populated question_handling block and
that the full two-speaker transcript was captured.

Usage:
    python check_question_handling.py "output\\<folder>"
    (defaults to the most recently modified output folder)
"""

import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / "output"


def pick_folder() -> Path:
    if len(sys.argv) > 1:
        f = Path(sys.argv[1])
        return f if f.is_absolute() else PROJECT_DIR / f
    subdirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir()]
    if not subdirs:
        raise SystemExit("No output folders found.")
    return max(subdirs, key=lambda d: d.stat().st_mtime)


def main() -> None:
    folder = pick_folder()
    print(f"Checking: {folder}\n")

    # 1. Full transcript captured?
    full = folder / "transcript_full.json"
    if full.exists():
        data = json.loads(full.read_text(encoding="utf-8"))
        words = data.get("words", [])
        speakers = sorted({w.get("speaker") for w in words if w.get("speaker")})
        print(f"[OK]   transcript_full.json present — {len(words)} words, "
              f"speakers: {speakers or 'none labelled'}")
        if len(speakers) < 2:
            print("[WARN] Fewer than two labelled speakers — question handling "
                  "needs interviewer turns. Check speaker separation.")
    else:
        print("[MISS] transcript_full.json absent. This session predates the "
              "full-transcript change, or was regenerated from old files. "
              "Question handling cannot be rebuilt without it.")

    # 2. Narrative carries question_handling?
    nar_path = folder / "narrative.json"
    if not nar_path.exists():
        print("[MISS] narrative.json absent.")
        return
    nar = json.loads(nar_path.read_text(encoding="utf-8"))
    qh = nar.get("question_handling")
    if qh and qh.get("pairs"):
        pairs = qh["pairs"]
        answered = sum(1 for p in pairs if (p.get("verdict") or "").lower() in ("answered", "yes"))
        print(f"[OK]   question_handling present — {len(pairs)} pairs, "
              f"{answered} directly answered")
        print(f"       weakest: {qh.get('weakest_exchange','(none flagged)')}")
        print("\nSUCCESS: question handling is working end to end.")
    else:
        print("[MISS] narrative.json has no populated question_handling block.")
        print("       If transcript_full.json is present, run:")
        print("         python regenerate_dashboard.py \"%s\"" % folder)
        print("       (needs OPENAI_API_KEY set) to rebuild it.")


if __name__ == "__main__":
    main()

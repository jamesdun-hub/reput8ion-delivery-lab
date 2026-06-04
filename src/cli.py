"""
Command-line interface for Reput8ion Delivery Lab.

Parses arguments and hands off to src.pipeline.run_session. All pipeline
logic lives there so changes are picked up by both this entry point and
the desktop GUI (launcher.pyw).

Usage:
    python -m src.cli samples/session.mp3 \\
        --candidate "Test Name" \\
        --session "Mock interview" \\
        --date "1 June 2026" \\
        [--previous output/<earlier-run>/metrics.json]
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reput8ion Delivery Lab: analyse session audio and generate feedback report."
    )
    parser.add_argument("audio_file", help="Path to audio file (mp3, wav, etc.)")
    parser.add_argument(
        "--candidate",
        required=True,
        help="Participant name (e.g. 'John Smith')",
    )
    parser.add_argument(
        "--session",
        required=True,
        help="Session label (e.g. 'Mock interview', 'Press briefing')",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Session date (e.g. '1 June 2026')",
    )
    parser.add_argument(
        "--previous",
        default=None,
        help="Path to previous session's metrics.json for comparative context",
    )
    parser.add_argument(
        "--local-transcription",
        action="store_true",
        help="Use local transcription instead of AssemblyAI (not yet implemented)",
    )

    args = parser.parse_args()
    load_dotenv()

    audio_path = args.audio_file
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if args.local_transcription:
        raise NotImplementedError("Local transcription is not yet implemented.")

    prior_metrics = None
    if args.previous:
        with open(args.previous) as f:
            prior_metrics = json.load(f)

    from src.pipeline import run_session
    run_session(
        audio_path=audio_path,
        candidate=args.candidate,
        session_label=args.session,
        date=args.date,
        prior_metrics=prior_metrics,
        auto_open_dashboard=True,
        metrics_callback=_print_summary,
    )


def _print_summary(metrics: dict) -> None:
    """Print a tight terminal summary for review during the session.

    Called via metrics_callback so it fires immediately after metrics are
    computed, before the narrative generation starts — giving James live
    numbers while the API call runs in the background.
    """
    print("\n" + "=" * 70)
    print("SESSION SUMMARY")
    print("=" * 70 + "\n")

    # Pace
    pace = metrics["pace"]
    print(f"PACE: {pace['gross_wpm']} wpm gross, {pace['net_wpm']} wpm net")
    print(f"      Target: {pace['target_band']} | Status: {pace['status']}\n")

    # Fillers
    fillers = metrics["fillers"]
    filler_breakdown = ", ".join(
        f"{count} {token}"
        for token, count in sorted(fillers["by_token"].items(), key=lambda x: -x[1])
    )
    print(f"FILLERS: {fillers['total']} total ({fillers['per_100_words']}/100 words)")
    if filler_breakdown:
        print(f"         Breakdown: {filler_breakdown}")
    print(f"         Status: {fillers['status']}\n")

    # Weak words
    weak = metrics["weak_words"]
    top_offenders = list(weak["top_offenders"].items())[:3]
    top_str = ", ".join(f"{count} {term}" for term, count in top_offenders)
    print(f"WEAK WORDS: {weak['total']} total ({weak['per_100_words']}/100 words)")
    if top_str:
        print(f"            Top: {top_str}")
    print(f"            Status: {weak['status']}\n")

    # Openers
    openers = metrics["sentence_openers"]
    top_opener = next(iter(openers["by_opener"].keys()), "—")
    print(f"OPENERS: {openers['crutch_percentage']}% of {openers['sentence_count']} sentences")
    print(f"         Top offender: '{top_opener}'")
    print(f"         Status: {openers['status']}\n")

    # Sentence shape
    shape = metrics["sentence_shape"]
    print(f"SENTENCE SHAPE: {shape['avg_sentence_length_words']} words avg, ")
    print(f"                {shape['longest_sentence_words']} words longest")
    print(f"                Status: {shape['status']}\n")

    # Pitch
    pitch = metrics["pitch"]
    if pitch["status"] == "not_measured":
        print("PITCH: Not measured this session\n")
    else:
        print(f"PITCH: {pitch['mean_hz']} Hz mean, {pitch['range_hz']} Hz range")
        print(f"       Std dev: {pitch['std_semitones']} semitones")
        if pitch.get("monotone_passages"):
            print(f"       Monotone passages: {len(pitch['monotone_passages'])}")
        print(f"       Status: {pitch['status']}\n")

    # Pauses
    pauses = metrics["pauses"]
    if pauses["status"] == "not_measured":
        print("PAUSES: Not measured this session\n")
    else:
        print(f"PAUSES: {pauses['count']} detected, {pauses['total_silent_seconds']}s total")
        print(f"        {pauses['at_sentence_boundary']} at sentence boundary, {pauses['mid_sentence']} mid-sentence")
        print(f"        Avg: {pauses['avg_seconds']}s, longest: {pauses['longest_seconds']}s\n")

    # Energy
    energy = metrics["energy"]
    if energy["status"] == "not_measured":
        print("ENERGY: Not measured this session\n")
    else:
        print(f"ENERGY: {energy['dynamic_range_db']} dB dynamic range")
        if energy.get("trailing_off_count", 0) > 0:
            print(f"        Trailing-off events: {energy['trailing_off_count']}")
        print(f"        Status: {energy['status']}\n")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

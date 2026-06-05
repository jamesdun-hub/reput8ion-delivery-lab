"""
Core orchestration pipeline for Reput8ion Delivery Lab.

Both entry points — cli.py (terminal) and launcher.pyw (GUI) — call
run_session() so any change to the analysis pipeline is made exactly once.

History: prior to this module, cli.py and launcher.pyw each carried their own
full copy of the pipeline body. They drifted out of sync during Session 6,
causing hours of debugging because a fix applied in cli.py never reached the
desktop app (launcher.pyw). This module eliminates that class of bug permanently.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


@dataclass
class RunResult:
    """Returned by run_session so callers can access key outputs."""
    output_dir: Path
    metrics: dict
    narrative: dict
    report_path: Path | None  # None for coaching mode (HTML dashboard only)


def run_session(
    audio_path: str | Path,
    candidate: str,
    session_label: str,
    date: str,
    *,
    mode: str = "coaching",
    coach_file: str | Path = "",
    prior_metrics: dict | None = None,
    log=print,
    auto_open_dashboard: bool = True,
    metrics_callback=None,
    role: str = "",
    organisation: str = "",
    sector: str = "",
    session_number: int = 1,
    interview_format: str = "broadcast",
    rock_1: str = "",
    rock_2: str = "",
    rock_3: str = "",
    known_context: str = "",
    confidentiality: str = "participant only",
) -> RunResult:
    """Run the full analysis pipeline and return a RunResult.

    Parameters
    ----------
    audio_path          : participant recording (audio or video)
    candidate           : participant name, e.g. 'Damien L'
    session_label       : e.g. 'Mock interview'
    date                : e.g. '3 June 2026'
    mode                : 'coaching' (default) or 'client'
    coach_file          : coach commentary recording or .txt (client mode only)
    prior_metrics       : metrics dict from a previous session for comparison
    log                 : callable(str) — print for CLI, self._log for GUI
    auto_open_dashboard : whether to open dashboard.html in the browser
    metrics_callback    : optional callable(metrics_dict) called immediately
                          after metrics are computed — CLI uses this to print
                          the full terminal summary before narrative generation
    """
    from dotenv import load_dotenv
    from src.config import load_config
    from src.transcribe import transcribe
    from src.prosody import analyse
    from src.metrics import compute_all_metrics, filter_to_speaker
    from src.prosody import detect_acoustic_fillers
    from src.coach import generate_coaching_narrative, CoachContext
    from src.dashboard import generate_dashboard
    # render_report and render_client_report are imported inside the mode
    # branches below to keep the coaching path free of report dependencies.

    load_dotenv()
    config = load_config()

    audio_path = str(audio_path)

    # Key validation — fail fast before any expensive API work
    aai_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not aai_key:
        raise RuntimeError(
            "ASSEMBLYAI_API_KEY not found in .env\n"
            "Set it to use AssemblyAI transcription."
        )
    if not os.environ.get("OPENAI_API_KEY"):
        log("[WARNING] OPENAI_API_KEY not set — narrative will be placeholder text.")

    log(f"[ANALYSIS] {Path(audio_path).name}")
    log(f"   Candidate : {candidate}")
    log(f"   Session   : {session_label}")
    log(f"   Date      : {date}")
    log(f"   Report    : {'Client Report' if mode == 'client' else 'Coaching Report'}")
    log("")

    # Prosody needs audio; extract from video if required
    prosody_path = _ensure_audio(audio_path, log)

    # ── 1. Transcribe ─────────────────────────────────────────────────────────
    log("[TRANSCRIBE] Starting...")
    transcript_data = transcribe(audio_path, aai_key)
    log(f"   {len(transcript_data.words)} words, {transcript_data.duration_seconds:.1f}s duration")

    speaker_info = transcript_data.speaker_summary or {}
    interviewee_id = speaker_info.get("interviewee")
    if interviewee_id and speaker_info.get("speaker_count", 1) > 1:
        counts = speaker_info.get("counts", {})
        total = sum(counts.values()) or 1
        log(f"   Speakers detected: {speaker_info['speaker_count']}")
        for spk, cnt in sorted(counts.items()):
            role = "interviewee" if spk == interviewee_id else "interviewer"
            log(f"   Speaker {spk}: {cnt} words ({cnt/total*100:.0f}%) — {role}")
        analysis_transcript = filter_to_speaker(transcript_data, interviewee_id)
        log(f"   Analysing interviewee (Speaker {interviewee_id}): {len(analysis_transcript.words)} words")
    else:
        analysis_transcript = transcript_data
        log("   Single speaker — analysing full transcript")

    # ── 2. Coach commentary (client mode only) ────────────────────────────────
    # Accepted inputs:
    #   .txt  — plain-text transcript, loaded directly
    #   .docx — Word document (e.g. a pre-existing meeting transcript), text extracted
    #   audio/video — transcribed via AssemblyAI (no disfluency tagging needed here)
    # The result is always saved to coach_notes.txt in the output folder so a
    # failed render never loses an expensive 45-minute transcription.
    coach_notes_text = None
    if mode == "client" and coach_file:
        coach_path = Path(str(coach_file))
        ext = coach_path.suffix.lower()

        if ext == ".txt":
            log("\n[COACH NOTES] Loading text file...")
            coach_notes_text = coach_path.read_text(encoding="utf-8")
            log(f"   {len(coach_notes_text.split())} words loaded")

        elif ext == ".docx":
            log("\n[COACH NOTES] Reading Word document...")
            from docx import Document as _DocxDoc
            _doc = _DocxDoc(str(coach_path))
            coach_notes_text = "\n".join(
                p.text for p in _doc.paragraphs if p.text.strip()
            )
            log(f"   {len(coach_notes_text.split())} words extracted from .docx")

        else:
            import assemblyai as aai_sdk
            log("\n[COACH NOTES] Transcribing commentary recording...")
            coach_audio = _ensure_audio(str(coach_file), log)
            aai_sdk.settings.api_key = aai_key
            cfg = aai_sdk.TranscriptionConfig(disfluencies=False, speaker_labels=False)
            result = aai_sdk.Transcriber(config=cfg).transcribe(coach_audio)
            coach_notes_text = result.text or ""
            log(f"   {len(coach_notes_text.split())} words transcribed")

    # ── 3. Prosody ────────────────────────────────────────────────────────────
    sentence_boundaries = None
    if transcript_data.sentences:
        sentence_boundaries = [s.end for s in transcript_data.sentences]

    log("\n[PROSODY] Analysing...")
    prosody_data = analyse(prosody_path, sentence_boundaries, config["prosody"])
    if prosody_data.pitch_measured:
        log(f"   Pitch: mean {prosody_data.mean_pitch_hz:.0f} Hz, range {prosody_data.pitch_range_hz:.0f} Hz")
    else:
        log("   Pitch: not measured")
    log(f"   Pauses: {len(prosody_data.pauses)} detected")
    log(f"   Speaking time: {prosody_data.speaking_time_seconds:.1f}s")

    # ── 3b. Acoustic filler detection ─────────────────────────────────────────
    # AssemblyAI with disfluencies=True misses most um/uh sounds in practice.
    # This pass scans the audio for voiced speech in inter-word gaps — the same
    # technique acoustic tools like Yoodli use — and passes the count to
    # compute_fillers so it can surface the gap between ASR and acoustic totals.
    log("[FILLERS] Acoustic filler detection...")
    word_timestamps = [{"start": w.start, "end": w.end}
                       for w in analysis_transcript.words]
    acoustic_filler_count = detect_acoustic_fillers(
        prosody_path, word_timestamps, config.get("prosody", {})
    )
    log(f"   Acoustic fillers detected: {acoustic_filler_count}")

    # ── 4. Metrics ────────────────────────────────────────────────────────────
    log("\n[METRICS] Computing...")
    metrics = compute_all_metrics(
        analysis_transcript, prosody_data, config,
        acoustic_filler_count=acoustic_filler_count,
    )

    # Surface a brief summary to the log; if a richer callback was supplied
    # (the CLI passes _print_summary) call it instead.
    if metrics_callback:
        metrics_callback(metrics)
    else:
        pace = metrics["pace"]
        fillers = metrics["fillers"]
        log(f"   Pace    : {pace['net_wpm']} wpm net, target {pace['target_band']}, {pace['status']}")
        log(f"   Fillers : {fillers['total']} total ({fillers['per_100_words']}/100 words)")

    if metrics.get("warnings"):
        log("\n[WARNINGS]")
        for w in metrics["warnings"]:
            log(f"   • {w}")

    # ── 5. Coaching narrative ─────────────────────────────────────────────────
    log("\n[NARRATIVE] Generating...")
    coach_context = CoachContext(
        candidate_name=candidate,
        session_label=session_label,
        session_date=date,
        role=role,
        organisation=organisation,
        sector=sector,
        session_number=session_number,
        interview_format=interview_format,
        rock_1=rock_1,
        rock_2=rock_2,
        rock_3=rock_3,
        known_context=known_context,
        confidentiality=confidentiality,
    )
    timestamped_transcript = _build_timestamped_transcript(analysis_transcript.words)

    # Build interviewer/answer pairs for question-handling assessment.
    # Only possible when AssemblyAI returned two labelled speakers.
    qa_transcript = ""
    if interviewee_id and speaker_info.get("speaker_count", 1) > 1:
        qa_transcript = _build_qa_transcript(transcript_data.words, interviewee_id)
    if qa_transcript:
        n_pairs = qa_transcript.count("INTERVIEWER:")
        log(f"   Question handling: {n_pairs} interviewer/answer pairs built")
    else:
        log("   Question handling: no interviewer turns found — section will be omitted")

    if coach_notes_text:
        log("   Including coach commentary")

    narrative = generate_coaching_narrative(
        metrics, coach_context, config, prior_metrics,
        transcript_text=timestamped_transcript,
        coach_notes_text=coach_notes_text,
        qa_transcript_text=qa_transcript or None,
    )
    log("   Done")

    # ── 6. Output directory ───────────────────────────────────────────────────
    output_dir = Path("output") / f"{candidate}-{date}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 7. Persist all session data (BEFORE rendering) ────────────────────────
    # Saving first means a renderer crash never loses an already-paid-for
    # narrative. The JSON files are also what regenerate_dashboard.py reads.
    with open(output_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    with open(output_dir / "narrative.json", "w") as f:
        json.dump(narrative, f, indent=2)

    # Full two-speaker transcript — source of truth for Q/A regeneration.
    # Saved so question_handling can be rebuilt without re-transcribing.
    full_words_path = output_dir / "transcript_full.json"
    with open(full_words_path, "w") as f:
        json.dump(
            {
                "interviewee_id": interviewee_id,
                "speaker_summary": speaker_info,
                "words": [
                    {"text": w.text, "start": w.start, "end": w.end, "speaker": w.speaker}
                    for w in transcript_data.words
                ],
            },
            f, indent=2,
        )
    log(f"   Full transcript saved to: {full_words_path}")

    # Interviewee-only word timestamps for storyboard regeneration
    with open(output_dir / "transcript_words.json", "w") as f:
        json.dump(
            [{"text": w.text, "start": w.start, "end": w.end}
             for w in analysis_transcript.words],
            f, indent=2,
        )

    # Coach notes — saved regardless of source (audio transcription, .txt, or .docx).
    # A 45-minute transcription is expensive; this means a render crash never
    # loses it, and you can re-render the Word doc from disk without re-transcribing.
    if coach_notes_text:
        coach_notes_path = output_dir / "coach_notes.txt"
        with open(coach_notes_path, "w", encoding="utf-8") as f:
            f.write(coach_notes_text)
        log(f"   Coach notes saved to: {coach_notes_path}")

    # ── 8. Client report (.docx) — client mode only ───────────────────────────
    # The coaching report is the HTML dashboard (below). The client never sees
    # the dashboard; they receive the Word document instead.
    # Two API calls for client mode: coaching narrative (already done, saves
    # narrative.json) + client report narrative (new call, produces the prose
    # that feeds the Word doc).
    ctx = {
        "candidate":    candidate,
        "session":      session_label,
        "date":         date,
        "organisation": getattr(coach_context, "organisation", ""),
    }
    report_path: Path | None = None
    if mode == "client":
        from src.coach import generate_client_report_narrative
        from src.report import render_client_report

        # Full two-speaker interview transcript for the AI (both voices, labelled)
        full_interview_text = _build_full_interview_transcript(
            transcript_data.words, interviewee_id
        )

        log("\n[CLIENT REPORT] Generating report narrative...")
        log("   Primary input: trainer feedback transcript")
        if not coach_notes_text:
            log("   (No trainer commentary — generating from interview transcript only)")
        client_narrative = generate_client_report_narrative(
            metrics=metrics,
            context=coach_context,
            config=config,
            coaching_narrative=narrative,
            interview_transcript_text=full_interview_text,
            coach_notes_text=coach_notes_text,
        )
        log("   Done")

        # Save client narrative alongside the coaching narrative
        with open(output_dir / "client_report.json", "w") as f:
            json.dump(client_narrative, f, indent=2)

        log("\n[REPORT] Rendering client report (.docx)...")
        report_path = output_dir / "report.docx"
        try:
            render_client_report(
                client_narrative=client_narrative,
                context=ctx, config=config, out_path=str(report_path),
                coaching_narrative=narrative,
            )
        except PermissionError:
            ts = datetime.now().strftime("%H%M%S")
            report_path = output_dir / f"report-{ts}.docx"
            log(f"   report.docx is open in Word — saving as {report_path.name}")
            render_client_report(
                client_narrative=client_narrative,
                context=ctx, config=config, out_path=str(report_path),
                coaching_narrative=narrative,
            )
        log(f"   Saved: {report_path}")

        # ── HTML participant report ────────────────────────────────────────────
        log("\n[REPORT] Generating HTML participant report...")
        try:
            from regenerate_report_html import render_report_html, _compute_filler_windows
            import webbrowser as _wb

            filler_set = {
                t.lower() for t in config.get("filler_words", {}).get("tokens", [])
            }
            pace_wins  = metrics.get("pace", {}).get("windows") or []
            word_dicts = [
                {"text": w.text, "start": w.start, "end": w.end}
                for w in analysis_transcript.words
            ]
            filler_wins = _compute_filler_windows(word_dicts, pace_wins, filler_set)
            html_path = output_dir / "report.html"
            render_report_html(
                metrics=metrics,
                narrative=narrative,
                client_report=client_narrative,
                context=ctx,
                out_path=str(html_path),
                filler_windows=filler_wins,
            )
            log(f"   Saved: {html_path}")
            _wb.open(html_path.resolve().as_uri())
            log("   Opened in browser.")
        except Exception as _exc:
            log(f"   [WARN] HTML report skipped: {_exc}")

    # ── 9. Coach dashboard (HTML) — coaching mode only ────────────────────────
    # The client never sees the dashboard. It is James's working instrument:
    # frank, gap-forward, dismissible. It opens automatically in the browser.
    if mode == "coaching":
        log("\n[DASHBOARD] Generating coach dashboard...")
        dashboard_path = output_dir / "dashboard.html"
        generate_dashboard(
            metrics=metrics,
            prosody_data=prosody_data,
            transcript_data=analysis_transcript,
            context=ctx,
            config=config,
            out_path=str(dashboard_path),
            narrative=narrative,
            auto_open=auto_open_dashboard,
        )
        log(f"   Opening in browser: {dashboard_path}")

    if mode == "client":
        log(f"\n[SUCCESS] Client report ready: {report_path}")
    else:
        log(f"\n[SUCCESS] Coach dashboard ready — check your browser")
    return RunResult(
        output_dir=output_dir,
        metrics=metrics,
        narrative=narrative,
        report_path=report_path,
    )


# ── Audio helpers ──────────────────────────────────────────────────────────────

def _ensure_audio(file_path: str, log_fn) -> str:
    """Return a path suitable for librosa/parselmouth.

    If the file is a recognised video format, extract a WAV alongside it and
    return that path. Falls back to the original if extraction fails (librosa
    may still succeed via its own ffmpeg fallback).
    """
    p = Path(file_path)
    if p.suffix.lower() not in VIDEO_EXTENSIONS:
        return file_path  # already audio

    wav_path = p.with_suffix(".extracted.wav")
    if wav_path.exists():
        log_fn(f"   Using cached audio extract: {wav_path.name}")
        return str(wav_path)

    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip  # type: ignore
        log_fn(f"   Extracting audio from video ({p.name})...")
        with VideoFileClip(file_path) as clip:
            clip.audio.write_audiofile(str(wav_path), verbose=False, logger=None)
        log_fn(f"   Audio extracted: {wav_path.name}")
        return str(wav_path)
    except ImportError:
        pass
    except Exception as exc:
        log_fn(f"   moviepy extraction failed ({exc}) — trying original file")

    log_fn("   Passing video directly to librosa (ffmpeg required)")
    return file_path


# ── Transcript helpers ─────────────────────────────────────────────────────────

def _build_timestamped_transcript(words, interval_seconds: float = 30.0) -> str:
    """Transcript text with a [M:SS] marker injected every N seconds.

    Gives the AI anchors to reference specific moments without needing
    word-level timing data in the prompt.
    """
    if not words:
        return ""
    parts: list[str] = []
    last_marker = -interval_seconds
    for word in words:
        t = word.start
        if t >= last_marker + interval_seconds:
            m = int(t // 60)
            s = int(t % 60)
            parts.append(f"\n[{m}:{s:02d}] ")
            last_marker = t
        parts.append(word.text + " ")
    return "".join(parts).strip()


def _build_full_interview_transcript(words, interviewee_id: str) -> str:
    """Readable two-speaker transcript for the client report AI.

    Groups contiguous words by speaker into turns and labels each as
    INTERVIEWER or INTERVIEWEE. The client report prompt uses this as its
    primary evidence base alongside the trainer feedback transcript.
    """
    if not words:
        return ""
    turns: list[dict] = []
    cur = None
    for w in words:
        spk = getattr(w, "speaker", None)
        if cur is None or spk != cur["speaker"]:
            cur = {"speaker": spk, "start": w.start, "words": []}
            turns.append(cur)
        cur["words"].append(w.text)

    lines = []
    for t in turns:
        label = "INTERVIEWEE" if t["speaker"] == interviewee_id else "INTERVIEWER"
        m, s = int(t["start"] // 60), int(t["start"] % 60)
        text = " ".join(t["words"]).strip()
        lines.append(f"[{m}:{s:02d}] {label}: {text}")
    return "\n\n".join(lines)


def _build_qa_transcript(words, interviewee_id: str, max_chars: int = 9000) -> str:
    """Pair each interviewer turn with the interviewee answer that follows.

    Works on the FULL two-speaker word list (before filtering to interviewee).
    Groups contiguous words by speaker into turns, then emits Q/A blocks the
    coach LLM uses to populate question_handling. Returns "" if there is no
    second speaker to read questions from.
    """
    if not words or not interviewee_id:
        return ""
    # Group contiguous words into speaker turns
    turns: list[dict] = []
    cur = None
    for w in words:
        spk = getattr(w, "speaker", None)
        if cur is None or spk != cur["speaker"]:
            cur = {"speaker": spk, "start": w.start, "text": []}
            turns.append(cur)
        cur["text"].append(w.text)
    if len({t["speaker"] for t in turns if t["speaker"]}) < 2:
        return ""  # single speaker — nothing to pair

    blocks: list[str] = []
    i = 0
    while i < len(turns):
        t = turns[i]
        if t["speaker"] and t["speaker"] != interviewee_id:
            q = " ".join(t["text"]).strip()
            # find the next interviewee turn as the answer
            answer = ""
            for j in range(i + 1, len(turns)):
                if turns[j]["speaker"] == interviewee_id:
                    answer = " ".join(turns[j]["text"]).strip()
                    i = j
                    break
            if q:
                m, s = int(t["start"] // 60), int(t["start"] % 60)
                wc = len(answer.split())
                blocks.append(
                    f"[{m}:{s:02d}] INTERVIEWER: {q}\n"
                    f"INTERVIEWEE ({wc} words): {answer}"
                )
        i += 1

    text = "\n\n".join(blocks).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[truncated]"
    return text

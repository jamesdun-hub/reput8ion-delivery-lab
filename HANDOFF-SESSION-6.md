# Handover — Session 6 (Cowork) → Claude Code

**Date:** 3 June 2026
**Author:** Cowork session (James + assistant)
**Purpose:** Record every change made to the Reput8ion Delivery Lab in this
session so Claude Code can verify, reconcile, and (if the working copies were
wiped) reapply them. Read this top to bottom before touching code.

---

## 0. TL;DR for Claude Code

This session added a **question-handling** feature to the coach dashboard,
plus several integrity/honesty fixes, and — critically — discovered the project
has **two duplicate pipelines** that had drifted out of sync. Your jobs:

1. Verify the eight files in section 3 contain the changes described. Reference
   copies are in `_handover/snapshot/`.
2. If any change is missing (files were reverted/deleted), reapply it from the
   snapshot or the code blocks below.
3. **Strongly recommended refactor (section 6):** collapse the two duplicate
   pipelines into one shared function so they can never drift again. This is
   the root cause of most of the pain this session.

There is a known environment quirk: this project lives in **OneDrive**, which
delays file sync and rewrites `.pyc` timestamps. That caused Python to run
stale bytecode repeatedly. Mitigations are already in place (`-B` flag); see
section 5.

---

## 1. What the system is

A trainer's instrument (James Dunny, Reput8ion Dynamics) that takes an audio/
video file of a media-training session and produces:

- A **coach dashboard** (`dashboard.html`) — James's working view.
- A **participant report** (`report.docx`) — the gentler leave-behind.

Pipeline: AssemblyAI transcription (speaker-labelled) → prosody (librosa/
parselmouth) → metrics (pure functions) → coaching narrative (OpenAI tool-call,
schema in `coach.py`, prompt in `prompts/coach.md`) → render to docx + html.

### THE CRITICAL ARCHITECTURE FACT
There are **two entry points that each contain their own full copy of the
orchestration logic**:

- `src/cli.py` → `main()` — run via `python -m src.cli ...` (terminal, and the
  `watcher.py` subprocess).
- `launcher.pyw` → the `_run_pipeline` worker (approx lines 320–449) — the
  **desktop app** James actually uses day to day.

**Any pipeline change must be made in BOTH.** This session, changes were first
made only in `cli.py`; the desktop app kept producing old output until the same
changes were ported into `launcher.pyw`. This duplication is a latent bug
generator. See section 6 for the fix.

---

## 2. What changed this session, in plain terms

1. **Question handling (new feature).** For each interviewer question, the coach
   assesses: did the answer address it (answered/partial/deflected/dodged),
   answer length, time to substance, and how a loaded premise was handled.
   Renders as a table with a "X of Y answered" score and a weakest-exchange flag.

2. **Rocks reframed as perception.** Rocks are now "what actually landed" with
   per-rock strong/weak status and a coaching delta note. (James will never have
   pre-set rocks, so perception is the correct model.)

3. **Integrity fixes.** Audio-only presence flag; pitch/Hz reliability caveat;
   targets labelled as Reput8ion house standards; full-session storyboard (the
   old 8-tile cap hid the hot close).

4. **Pace reconciliation.** Card, pattern chip, storyboard and pillar previously
   disagreed. Card now downgrades to "watch" and notes the peak when any window
   breaches the upper ceiling; a late-spike insight names the hot close.

5. **Headline honesty.** Badge names the gap ("Message control is the gap");
   summary leads with a "Priority for the debrief" line from the weakest pillar,
   before the gentler shared overview.

6. **Closing focus-areas box.** Renders `tips_for_success` + `final_word` (the
   pipeline already generated these; the dashboard had been discarding them).

7. **Full transcript persisted.** `transcript_full.json` (both speakers, with
   labels) is now saved so question handling can be regenerated without
   re-transcribing.

8. **OneDrive/.pyc mitigation.** `watcher.py` now launches the cli subprocess
   with `-B` so Python never runs stale bytecode.

The **participant report (`report.py`) was deliberately NOT hardened** — it
keeps its softer "tips for success" framing. Only the coach dashboard leads with
the gap.

---

## 3. File-by-file change list (verify each)

Reference copies: `_handover/snapshot/`. NOTE: the snapshot was copied through
the OneDrive mount which can lag; if a snapshot file looks shorter than the
working copy, trust the working copy and this document.

### 3.1 `src/coach.py` — narrative schema + prompt plumbing
- Added to `NARRATIVE_SCHEMA["properties"]`:
  - `rock_strength` — array aligned to `inferred_rocks`, items
    `{strength: enum[strong,weak], note: str}`.
  - `rock_delta_note` — string, the single most important message point.
  - `question_handling` — object with `pairs` (array, maxItems 10, items
    `{question, verdict: enum[answered,partial,deflected,dodged],
    answer_length, time_to_substance, premise_handling}`) and
    `weakest_exchange` (string).
- `inferred_rocks` description rewritten to "rocks that ACTUALLY LANDED…
  perception, not stated intent".
- `_build_user_message(...)` gained a `qa_transcript_text` param; when present it
  appends a "## Interviewer questions paired with answers" block instructing the
  model to populate `question_handling`.
- `generate_coaching_narrative(...)` gained a `qa_transcript_text=None` param,
  passed through to `_build_user_message`.

### 3.2 `prompts/coach.md` — instructions for the new fields
- `inferred_rocks` section reframed to perception (what landed, not intent).
- New `rock_strength`, `rock_delta_note`, `question_handling` task sections.
  Question-handling instruction: judge each interviewer question fairly but
  exactingly; this goes to the coach, not the participant, so do not soften it;
  omit the field if no interviewer turns are provided.

### 3.3 `src/cli.py` — Q/A pairing, persistence, diagnostics
- New function `_build_qa_transcript(words, interviewee_id, max_chars=9000)` at
  end of file — groups the full two-speaker word list into contiguous speaker
  turns and pairs each interviewer turn with the following interviewee answer.
- In `main()`: builds `qa_transcript` (only when 2+ speakers), prints a count
  line, passes `qa_transcript_text=qa_transcript or None` to the narrative call.
- In `main()`: saves `transcript_full.json` ({interviewee_id, speaker_summary,
  words[ with speaker ]}) alongside the existing interviewee-only
  `transcript_words.json`.

### 3.4 `src/dashboard.py` — rendering of all new sections + fixes
- `_storyboard(...)`: `max_tiles` default changed from `8` to `0` (no cap);
  only sub-samples if a positive cap is passed.
- `_delivery_cards(...)`: pace card detects when any window exceeds `ideal_max`,
  appends "Peaks at N wpm — runs above the ceiling", downgrades status to watch.
- `_compute_correlations(...)`: added a late-spike insight that flags the peak
  in the final third when it exceeds 170 wpm.
- `_rocks_and_strengths(...)`: rocks rendered as "what actually landed" with
  strong/weak badges from `rock_strength` and a delta banner from
  `rock_delta_note`; strengths box detached into its own full-width box.
- `_session_summary_html(...)`: callouts sorted watch-first; zero flags/hooks
  added as a callout; badge logic names the gap ("Message control is the gap",
  or "Work on <pillar>"); a "Priority for the debrief" gap line is prepended
  before the shared overview; right-column label changed to "What landed
  (perception)".
- New builders: `_pitch_caveat_html`, `_presence_flag_html`,
  `_question_handling_html`, `_closing_summary_html`.
- Render body wired to call: presence flag (after speaker note), pitch caveat
  (after delivery cards), question handling (after compact tiles), closing
  summary (end of container).
- CSS block: added styles under a "Refit additions" comment (caveat, house-note,
  presence-flag, rock-line states, rs-*, delta-banner, qa-table, qv-*, qa-score,
  qa-flag, closing-box, closing-list/item).

### 3.5 `launcher.pyw` — DESKTOP APP, the same three pipeline changes
This is the file James runs. It carries its own pipeline copy; the cli.py changes
do NOT reach it automatically.
- Import line: `from src.cli import _build_timestamped_transcript,
  _build_qa_transcript`.
- Before the narrative call: build `qa_transcript` (when 2+ speakers), log the
  pair count, pass `qa_transcript_text=qa_transcript or None`.
- In the persist block: write `transcript_full.json` exactly as cli.py does.

### 3.6 `watcher.py` — bytecode mitigation
- The `subprocess.run([...])` in `run_pipeline` now passes `-B`:
  `[sys.executable, "-B", "-m", "src.cli", ...]`.

### 3.7 `regenerate_dashboard.py` — NEW helper
- Regenerates `dashboard.html` from saved JSONs with no API call/cost.
- `_maybe_add_question_handling(...)`: if narrative lacks `question_handling`
  but `transcript_full.json` exists and `OPENAI_API_KEY` is set, rebuilds just
  that block with one coach call and writes it back. Degrades cleanly otherwise.
- Docstring is a raw string (`r"""`) to avoid a `\D` SyntaxWarning.

### 3.8 `check_question_handling.py` — NEW diagnostic
- Reports whether `transcript_full.json` is present (and speaker count) and
  whether `narrative.json` carries a populated `question_handling` block.

---

## 4. How to verify it works (no guessing)

```
cd "C:\Users\james\OneDrive - Reput8ion Communications\Repu8ion\Claude\Media trainer"
# 1. Everything compiles
python -m py_compile src\coach.py src\dashboard.py src\cli.py launcher.pyw regenerate_dashboard.py check_question_handling.py
# 2. Clear any stale bytecode (OneDrive rewrites .pyc timestamps)
Remove-Item -Recurse -Force src\__pycache__, __pycache__ -ErrorAction SilentlyContinue
# 3. Run the REAL pipeline against existing cached audio (no re-transcribe cost)
python -m src.cli "Sessions\Damien audio 3.mp3" --candidate "Verify" --session "Mock interview" --date "3 June 2026"
# 4. Confirm question handling landed
python check_question_handling.py "output\Verify-3 June 2026"
```

Expected: console shows `Question handling: N interviewer/answer pairs built`
and `Full transcript saved to: ...`; the diagnostic reports
`question_handling present — N pairs`. A known-good reference output exists at
`output\Damien 6-3 June 2026\` (desktop run) and `output\Test 3-3 June 2026\`
(cli run) — both contain `transcript_full.json` and 7 real questions.

---

## 5. Environment quirk Claude Code MUST know

The project is inside **OneDrive**. Two consequences seen repeatedly this session:
- File edits take time to sync; a freshly edited file may read as its old
  version for a minute or more from some tools.
- OneDrive can rewrite `.pyc` timestamps so they look newer than the source,
  making Python skip recompilation and run **stale bytecode**. This produced
  hours of false "the fix didn't work" symptoms.

Rules of thumb:
- After any code edit, delete `__pycache__` before running.
- The watcher subprocess already runs with `-B`. Consider adding
  `sys.dont_write_bytecode = True` at the top of `launcher.pyw` too (NOT yet
  done) so the desktop app also never caches. Recommended.
- A long-running watcher/desktop process holds the code it loaded at launch.
  Always fully close and reopen after a code change.

---

## 6. RECOMMENDED REFACTOR (the real fix)

The duplicate pipelines in `cli.py:main()` and `launcher.pyw` are the root cause
of this session's churn. Recommend:

1. Extract the orchestration into one function, e.g.
   `src/pipeline.py::run_session(audio_path, candidate, session, date, *,
   coach_file=None, prior_metrics=None, log=print) -> Path` that does
   transcribe → prosody → metrics → qa_transcript → narrative → persist →
   report → dashboard, and returns the output dir.
2. `cli.py:main()` becomes arg-parsing + a call to `run_session`.
3. `launcher.pyw` worker becomes GUI plumbing + a call to `run_session` (passing
   its `self._log` as `log`).
4. Delete the duplicated bodies. After this, no change can ever land in one path
   but not the other.

Keep the participant-report softening (`report.py`) untouched by this refactor.

---

## 7. Open items / next steps (not yet done)

1. **Verbatim question phrasing.** Questions currently render lightly paraphrased
   (faithful but tightened). For media training the exact wording of loaded/
   hostile questions matters. One-line tightening in `coach.md` question-handling
   instruction: "quote the interviewer's actual words, removing only filler and
   false starts; do not paraphrase or summarise."
2. **Pipeline refactor** (section 6).
3. **`sys.dont_write_bytecode = True`** in `launcher.pyw` (section 5).
4. **Speaker-inversion guard.** Pipeline assumes the interviewee is the speaker
   with the most words. In a heavily interviewer-led session that could invert.
   Worth a sanity check/flag.
5. **Question-handling accuracy** depends on AssemblyAI speaker separation being
   clean. `check_question_handling.py` surfaces the speaker count; treat verdicts
   as draft until reviewed.

---

## 8. Backups already on disk
- `.refit-backup/` — pre-edit copies of cli.py, coach.py, dashboard.py, coach.md
  (made early this session).
- `output/Damien L v2-3 June 2026/dashboard-v2-backup.html` — first hand-edited
  dashboard.
- `_handover/snapshot/` — current copies of all eight changed files (this doc).

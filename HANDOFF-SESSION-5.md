# Handoff — Delivery Lab Session 5

## What this tool is

A local Python CLI that takes an audio recording of a media-training session and produces:
1. A **coach dashboard** (`dashboard.html`) — opens automatically in browser during/after the session, James's working view
2. A **leave-behind report** (`report.docx`) — formal branded Word document given to the participant after the session

The tool is complete and working end-to-end. Session 5 focus is **refining the .docx report** so it is a strong, professional leave-behind that matches the quality of the dashboard.

---

## Architecture (do not relitigate)

| Layer | Technology |
|---|---|
| Transcription | AssemblyAI with `disfluencies=True` and `speaker_labels=True` |
| Prosody | librosa + parselmouth (Praat) — pitch, pauses, energy |
| Coaching narrative | OpenAI GPT-4o via `OPENAI_API_KEY` |
| Report | python-docx, Reput8ion Dynamics brand |
| Keys | `.env` file, never committed |

**Two files James edits without touching Python:**
- `prompts/coach.md` — coaching framework, assessment criteria, style rules
- `config.yaml` — all thresholds, targets, phrase lists

**Pipeline order:**
1. AssemblyAI transcription (disfluencies + speaker labels)
2. Speaker identification (most words = interviewee)
3. Transcript filtered to interviewee
4. librosa + parselmouth prosody on full audio
5. Metrics computed on interviewee transcript
6. Timestamped transcript built for AI context
7. GPT-4o narrative generation
8. `.docx` report rendered
9. HTML dashboard generated and auto-opened

---

## Current state of the codebase

### Dashboard (`src/dashboard.py`) — COMPLETE, do not touch without reason

The dashboard was heavily iterated in Sessions 3–5 and is working well. Key features:

- **Session summary box** (above chart): overall verdict badge (Strong/Mixed/Needs work) + AI overview paragraph + 3 auto-callouts from hard metrics + inferred rocks on the right column
- **Combined chart**: Pace (WPM) + Pitch (Hz, right axis) + Fillers (amber bars) on one timeline
- **Storyboard tiles**: 8 tiles max, evenly sampled, 20-word snippets (populated from `transcript_words.json` on full runs)
- **Pattern analysis**: auto-detected correlations (pace/filler, pace trend, pitch/pace)
- **Pillar assessment**: 3 columns with verdict headline + scannable bullet points (not paragraphs)
- **Compact language row**: 4 tiles — narrative control / sentence openers / weak words / conciseness & repetition
- **Coaching moments**, tone, pause highlights, rocks + strengths all present

### Report (`src/report.py`) — BUILT, NEEDS REFINEMENT

The report was rebuilt in Session 4 around the four-pillar structure. It renders correctly and produces a valid `.docx`. Structure:

1. Title block (candidate | session | date)
2. Overview
3. Performance at a glance (3-row pillar scorecard table: Delivery / Story / Control)
4. Key messages heard in this session (inferred rocks as bullets)
5. What you did well (strengths as bullets)
6. Delivery: pace and tone (narrative + tone descriptors + pause moments)
7. Delivery: the measured detail (8-row hard numbers table)
8. Message discipline: story and control (filler/weak/control narratives + conciseness examples)
9. Coaching moments (timestamped table with Strength/Watch labels)
10. Three tips for success (numbered, bold tip + rationale)
11. A final word + sign-off

**Known issues and refinement priorities for Session 5:**

1. **No overall verdict in the report** — the dashboard shows "Mixed session / Strong session / Needs significant work" prominently. The report has no equivalent. The participant reads this cold after the session, so they need that framing too.

2. **Hard numbers table is dry** — Section 7 ("Delivery: the measured detail") is an 8-row data table with no interpretation. Consider adding a brief status-coded summary row or colour-coded status indicators so the participant can see at a glance which metrics are green/watch/red.

3. **Conciseness examples need visual separation** — the before/after examples are rendered as indented text but can get lost in the flow. They'd benefit from a lightly shaded box or border.

4. **Tips for success use ". " as separator** — this reads oddly when the tip itself ends mid-sentence. Consider a cleaner typographic treatment (e.g., tip in bold on its own line, rationale on the next line indented).

5. **No logo or header/footer** — the report has a text title but no logo image. `config.yaml` has `header_text` and `footer_text` under `brand` but they are not wired up. Consider adding a header with the logo/brand name and a footer with "Confidential coaching feedback".

6. **Em dash in brand subtitle** — `config.yaml` has `subtitle: "Telling your story — delivering with confidence"`. House style forbids em dashes. James's call to change it to a comma.

---

## Brand rules (house style — apply everywhere in the report)

- **UK spelling** (colour, recognise, organisation)
- **No em dashes** — use commas, full stops or parentheses instead
- **No Oxford comma**
- Colours: cyan `#0CC0DF` (accent/table headers), deep teal `#0A5C6B` (headings)
- Font: Arial throughout
- Page size: A4
- Tone: formal, forward-looking, "tips for success" — never punitive

---

## Narrative schema (what the AI returns — report must use all of these)

```python
{
  "inferred_rocks": [...],           # 2-3 key messages inferred from transcript
  "pillar_verdicts": {
    "delivery": {"status": "green|watch|red", "verdict": "..."},
    "story":    {"status": "green|watch|red", "verdict": "..."},
    "control":  {"status": "green|watch|red", "verdict": "..."},
  },
  "strengths": [...],                # 2-3 evidenced strengths
  "overview": "...",                 # 2-4 sentences, warm, forward-looking
  "pace_and_tone_narrative": "...",  # Delivery pillar detail
  "filler_and_weak_words_narrative": "...",
  "control_and_structure_narrative": "...",
  "tone_assessment": {
    "descriptors": [...],            # 3-6 single-word tone descriptors
    "narrative": "...",
  },
  "coaching_moments": [
    {"timestamp_approx": "1:20", "type": "strength|watch", "observation": "..."},
    ...
  ],
  "conciseness_analysis": {
    "estimated_excess_pct": 35,
    "assessment": "...",
    "examples": [{"original": "...", "suggested": "..."}, ...],
  },
  "pause_highlights": [
    {"timestamp_approx": "1:30", "quote": "...", "observation": "..."},
    ...
  ],
  "tips_for_success": [
    {"rank": 1, "tip": "...", "rationale": "..."},
    ...
  ],
  "final_word": "...",
}
```

---

## Test data (use this to iterate on the report without API calls)

Brian O'Flynn's session data is saved in:
```
output/Brian O'Flynn-2 June 2026/
  metrics.json       ← hard metrics
  narrative.json     ← full AI narrative (all fields populated)
  report.docx        ← current report output
  dashboard.html     ← current dashboard
```

**Regenerate the report only (no API calls):**
```python
import json
from src.config import load_config
from src.report import render_report

with open("output/Brian O'Flynn-2 June 2026/metrics.json") as f:
    metrics = json.load(f)
with open("output/Brian O'Flynn-2 June 2026/narrative.json") as f:
    narrative = json.load(f)

render_report(
    metrics=metrics,
    narrative=narrative,
    context={"candidate": "Brian O'Flynn", "session": "Mock interview", "date": "2 June 2026"},
    config=load_config(),
    out_path="output/Brian O'Flynn-2 June 2026/report.docx",
)
```

**Full pipeline (costs AssemblyAI + OpenAI credits):**
```
python -m src.cli "C:\Users\james\Downloads\Jun-02-12-22-PM_2026-06-02.mp3" --candidate "Brian O'Flynn" --session "Mock interview" --date "2 June 2026"
```

---

## Key files

| File | Purpose |
|---|---|
| `src/report.py` | Report renderer — Session 5 primary target |
| `src/dashboard.py` | Coach dashboard — complete, do not change without reason |
| `src/cli.py` | Pipeline orchestrator |
| `src/coach.py` | GPT-4o narrative generation + NARRATIVE_SCHEMA definition |
| `src/metrics.py` | All metric computation |
| `src/prosody.py` | Pitch, pauses, energy extraction |
| `src/transcribe.py` | AssemblyAI transcription |
| `config.yaml` | All thresholds, targets, phrase lists |
| `prompts/coach.md` | AI coaching system prompt |
| `output/Brian O'Flynn-2 June 2026/` | Test data for this session |

---

## Changes made in Sessions 4 and 5 (do not redo)

**Session 4:**
- `report.py` fully rebuilt around four-pillar structure (10 sections, 3 tables)
- `cli.py` now saves `transcript_words.json` for dashboard regeneration
- All em dashes removed from report code

**Session 5 (this session — dashboard only):**
- Session summary box with verdict badge, callouts, and rocks column
- Storyboard: max 8 tiles, 20-word snippets, wider tiles
- Pattern correlations box below storyboard
- Pillar columns: bullet points, not paragraphs
- Story/language: merged into 4 compact tiles in one row
- Filler card: shows % with target `<4%`, breakdown clean
- Summary callout uses % wording, not "per 100 words"
- `config.yaml`: filler `green_per_100_words` updated to 4.0, `watch_per_100_words` to 6.0

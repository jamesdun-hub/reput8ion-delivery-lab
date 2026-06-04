# Handoff — Delivery Lab Session 3

## Status

### Session 3 Completed

**Prosody fixes:**
- ✅ Pause detection fixed — was using inverted logic (treating speech intervals as pauses) and wrong unit conversion (sample indices passed to frame-time function). Now correctly finds gaps between speech intervals and converts with `sample / sr`.
- ✅ Pitch extraction fixed — `parselmouth.Sound(audio_path)` has patchy MP3 support. Now builds Sound from the numpy array librosa already decoded: `parselmouth.Sound(audio.astype(np.float64), sampling_frequency=float(sr))`. Also replaced `pitch.number_of_frames` (didn't exist in this parselmouth version) with `len(f0_all)` and numpy linspace for frame times.
- ✅ Pitch windows added — 30-second windowed mean Hz stored in `ProsodyData.pitch_windows` for the trend chart.

**Speaker diarization:**
- ✅ AssemblyAI `speaker_labels=True` enabled in `transcribe.py`
- ✅ `Word.speaker` field added; interviewee identified as speaker with most words
- ✅ `filter_to_speaker()` in `metrics.py` — filters transcript to interviewee only
- ✅ All metrics (pace, fillers, weak words, structure) computed on interviewee words only
- ✅ Prosody still runs on full audio (speaker separation at waveform level not yet implemented)

**Framework encoded:**
- ✅ James's five-pillar model: Presence | Delivery | Story | Control | Audience
- ✅ Delivery = five elements: pace, melody, volume, tone, pausing
- ✅ Control = bridging, flagging, hooking, ABC technique
- ✅ Rocks (key messages), Colour (concrete examples), Headline-first structure

**Config architecture (no Python needed for common changes):**
- ✅ `prompts/coach.md` — full AI system prompt, editable in any text editor
- ✅ `config.yaml` — all phrase lists (bridge/flag/hook), thresholds, targets

**New metrics (`metrics.py`):**
- ✅ `compute_repetition()` — detects 3+ word phrases repeated 3+ times, calculates repetition %
- ✅ `compute_control_signals()` — detects bridge/flag/hook language from config phrase lists
- ✅ `compute_story_signals()` — hedged vs declarative sentence openers, headline discipline

**New AI schema fields (`coach.py` / `prompts/coach.md`):**
- ✅ `inferred_rocks` — 2–3 key messages the candidate appeared to be carrying
- ✅ `pillar_verdicts` — Delivery / Story / Control with status (green/watch/red) + one-line verdict
- ✅ `strengths` — 2–3 specific evidenced strengths to open the debrief with
- ✅ `tone_assessment` — descriptors (confident, enthusiastic, etc.) + narrative with timestamps
- ✅ `coaching_moments` — 4–8 qualitative timestamped moments (answered/bridged/hooked/avoided)
- ✅ `conciseness_analysis` — estimated excess %, examples of verbose → tighter phrases
- ✅ `pause_highlights` — 2–4 moments with quotes where pauses worked or were needed

**Timestamped transcript passed to AI:**
- ✅ `cli.py` builds a transcript with `[M:SS]` markers every 30 seconds
- ✅ Passed to GPT-4o so it can cite specific moments and timestamps

**Dashboard redesign (`dashboard.py`):**
- ✅ Delivery analytics at top — 4 cards with rich sub-text (filler breakdown, pace gross/net, etc.)
- ✅ Combined timeline chart — Pace (left axis) + Pitch (right axis) + Fillers (amber bars), one chart
- ✅ Storyboard row — coloured tiles below chart (green/amber/red), time + WPM + first 5 words, no hover needed
- ✅ Three-column pillar assessment with full AI narrative paragraphs per column
- ✅ Coaching moments — AI qualitative insights, not speed flags
- ✅ Tone section — descriptor chips + narrative paragraph
- ✅ Conciseness section — % estimate, target <30%, before/after examples
- ✅ Pause highlights — timestamped quotes
- ✅ Language section — weak words %, sentence openers, repetition % with targets
- ✅ Removed: raw pause table, speed-based coaching flags
- ✅ Pace chart: windows <100 wpm nulled out (breaks line instead of plunging)
- ✅ Pace target updated to 140–170 wpm

## Current Metrics (Brian O'Flynn, Session 2 recording — Session 3 fixes not yet validated on a fresh run)

After Session 3 fixes, expected:
- Pauses: ~5–20 (was 1,398 — fixed)
- Pitch: real Hz value (was not_measured — fixed)
- Speaker split: Speaker A 89% (interviewee), Speaker B 11% (interviewer)
- Pace: 194.9 wpm gross, 208.9 wpm net (hard_fast vs 140–170 target)

## Files Changed in Session 3

| File | What changed |
|---|---|
| `src/prosody.py` | Pause logic inverted, sample→time conversion fixed, pitch uses numpy array, `number_of_frames` replaced, `_compute_pitch_windows()` added |
| `src/metrics.py` | `Word.speaker` field, `TranscriptData.speaker_summary`, `filter_to_speaker()`, `ProsodyData.pitch_windows`, `compute_repetition()`, `compute_control_signals()`, `compute_story_signals()`, all three added to `compute_all_metrics()` |
| `src/transcribe.py` | `speaker_labels=True`, populates `word.speaker`, computes `speaker_summary` |
| `src/coach.py` | Prompt loads from `prompts/coach.md`, expanded schema (7 fields → 11 fields), `transcript_text` param, offline placeholder updated |
| `src/dashboard.py` | Full redesign — combined chart, storyboard, pillar columns, coaching moments, tone, conciseness, pause highlights |
| `src/cli.py` | Speaker filtering, timestamped transcript, passes narrative to dashboard |
| `config.yaml` | Pace 140–170, bridge/flag/hook phrase lists, repetition/weak words/conciseness targets, `max_tokens: 4000`, `prompt_file` setting |
| `prompts/coach.md` | Created — full coaching system prompt with style reference example |

## Known Issues / Next Steps

### Immediate (Session 4)

1. **Run full pipeline and validate** — the dashboard redesign has not been tested on a real run yet. Run with Brian's recording and check:
   - Does the combined chart render correctly with three datasets?
   - Does the storyboard row appear with coloured tiles?
   - Do the AI narrative sections populate correctly with the new schema?
   - Is pitch now measured?

2. **Report (.docx) restructure** — `report.py` still uses the old narrative schema (no `inferred_rocks`, `pillar_verdicts`, `strengths`, `tone_assessment`, etc.). The report needs to be rebuilt around the four-pillar structure:
   - Section 1: Performance at a glance (pillar scorecard)
   - Section 2: Strengths (from `narrative.strengths`)
   - Section 3: Delivery (pace/tone narrative)
   - Section 4: Message discipline (story/control narrative)
   - Section 5: Three tips for success
   - Section 6: Close / final word

3. **Pitch calibration** — once pitch is confirmed working, validate that the mean Hz and semitone std values match auditory perception. Tune `config.yaml`:
   - `monotone_pitch_std_semitones_threshold` (currently 2.0)
   - Check monotone passage detection

4. **Test with additional recordings** — validate speaker diarization and metrics quality on a second sample before using with a live client.

### Later

5. **James's notes integration** — the report needs a section for James's handwritten coaching notes to be combined with the AI narrative. Currently the report is 100% AI-generated.

6. **Comparative mode** — `--previous metrics.json` flag exists but comparative framing in the narrative is not fully tested.

7. **Prosody speaker separation** — currently pitch, pauses and energy are measured from the full audio. Ideally they'd be filtered to interviewee segments only. Requires aligning AssemblyAI speaker timestamps with librosa audio windows.

## Testing Command

```bash
python -m src.cli "C:\Users\james\Downloads\Jun-02-12-22-PM_2026-06-02.mp3" \
    --candidate "Brian O'Flynn" \
    --session "Mock interview" \
    --date "2 June 2026"
```

Expected output files in `output/Brian O'Flynn-2 June 2026/`:
- `dashboard.html` — opens automatically in browser
- `report.docx` — leave-behind (currently needs restructuring, see above)
- `metrics.json` — raw metrics
- `narrative.json` — AI coaching narrative

## Architecture Reminder

**Two files James edits without touching Python:**
- `prompts/coach.md` — coaching framework, assessment criteria, style rules, what the AI produces
- `config.yaml` — all thresholds, targets, phrase lists (bridge/flag/hook detection, weak words, fillers, etc.)

**Pipeline order:**
1. AssemblyAI transcription (disfluencies + speaker labels)
2. Speaker identification (most words = interviewee)
3. Transcript filtered to interviewee
4. Librosa + parselmouth prosody on full audio
5. Metrics computed on interviewee transcript
6. Timestamped transcript built for AI context
7. GPT-4o narrative generation (loads prompt from `prompts/coach.md`)
8. .docx report rendered
9. HTML dashboard generated + auto-opened

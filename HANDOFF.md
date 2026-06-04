# Handoff — Delivery Lab v1

Foundation is in place. Remaining work is mostly library mechanics against
a stable contract. Switch to a cheaper model (Sonnet or Haiku) for what
follows.

## What is done

| File | Purpose | Status |
| --- | --- | --- |
| `config.yaml` | Tunable bands, word lists, brand, model choice | Done |
| `requirements.txt` | Pinned ranges | Done |
| `.env.example`, `.gitignore` | Secrets template, ignores | Done |
| `src/config.py` | Loads `config.yaml` | Done |
| `src/metrics.py` | Pure metrics engine | Done, 18/18 tests pass |
| `src/coach.py` | Anthropic narrative generation with offline fallback | Done |
| `tests/test_metrics.py` | Unit tests for the engine | Done |

Smoke-tested: text fixture flows end to end through metrics +
`_offline_placeholder`. Run the suite with:

```bash
python -m pytest tests/ -v
```

## What is left, in order

### 1. `src/transcribe.py` — AssemblyAI wrapper

Single function, returns a `TranscriptData` (defined in `src/metrics.py`).

```python
def transcribe(audio_path: str, api_key: str) -> TranscriptData: ...
```

Hard requirements:

- **`disfluencies=True`** on the transcription config. This is the whole
  point. Without it the filler count silently reads zero.
- Pull `duration` from the AssemblyAI response (`audio_duration`), not
  guessed from text length. The prototype reported 232 wpm because the
  denominator was wrong.
- Map AssemblyAI words to the `Word` dataclass — start and end are in
  **milliseconds** in the API, convert to seconds.
- If sentences are available (`transcript.get_sentences()`), populate
  `TranscriptData.sentences`. Otherwise leave `None` and let the engine's
  punctuation-based fallback handle it.
- Persist the raw AssemblyAI response to disk next to the audio
  (`<basename>.assemblyai.json`) for debugging.

### 2. `src/prosody.py` — librosa + parselmouth

Single function, returns a `ProsodyData` (defined in `src/metrics.py`).

```python
def analyse(audio_path: str, sentence_boundaries_s: list[float] | None, cfg: dict) -> ProsodyData: ...
```

What to extract:

- **Pitch (parselmouth):** F0 via `Sound.to_pitch()`. Compute mean Hz,
  range Hz, and std in semitones (log2 of pitch ratio). Slide a window
  of `monotone_passage_min_duration_seconds` to find passages whose
  in-window semitone std is below
  `monotone_pitch_std_semitones_threshold`. Merge overlapping passages.
- **Pauses (librosa):** detect silence regions longer than
  `pause_min_duration_seconds`. `librosa.effects.split` with a low
  top_db (e.g. 30) is the usual move. For each pause, classify
  `at_sentence_boundary=True` if its midpoint is within ~0.4s of any
  sentence-end timestamp passed in.
- **Speaking time:** total duration minus the sum of pause durations.
- **Energy (librosa):** RMS over short frames, convert to dB. Dynamic
  range is the 90th percentile minus the 10th. For trailing-off events,
  walk the last ~0.5s of each sentence and compare to that sentence's
  median energy; flag drops greater than `trailing_off_db_drop`.
- Set `pitch_measured=False` if pitch tracking returned no valid frames,
  `energy_measured=False` likewise. The engine treats those as
  "not measured" and the report says so honestly.

### 3. `src/report.py` — python-docx renderer

Single function:

```python
def render_report(
    metrics: dict,
    narrative: dict,            # matches NARRATIVE_SCHEMA in coach.py
    context: CoachContext,
    config: dict,
    out_path: str,
) -> None: ...
```

Structure (from the brief):

1. Title `config['brand']['title']` (cyan body, deep-teal heading colour),
   subtitle below.
2. Participant / session / date line.
3. **Overview** — `narrative['overview']`.
4. **Delivery — the measured detail** — three-column table (Measure /
   Result / What it tells us). Rows: Pace, Filler words, Weak words,
   Sentence openers, Sentence shape, Pitch, Pauses, Energy. Pull the raw
   values from `metrics`. If a metric is `status="not_measured"`, the
   Result cell reads "Not measured this session" and the third column
   explains why briefly. **Never fabricate.** Itemise filler counts
   (e.g. "27 um, 15 er") — do not aggregate them away.
5. **Pace and tone** — `narrative['pace_and_tone_narrative']`.
6. **Filler and weak words** — `narrative['filler_and_weak_words_narrative']`.
7. **Control and structure** — `narrative['control_and_structure_narrative']`.
8. **Tips for success** — numbered list from `narrative['tips_for_success']`,
   each item bolds the tip and follows with the rationale.
9. **A final word** — `narrative['final_word']`.
10. Signed line `config['brand']['signoff']`.

Branding from `config['brand']`:

- Page size A4, Arial throughout.
- Header text and footer text from config, with page number on the right
  of the footer.
- Heading colour: `#0A5C6B` (deep teal). Accent / table header fill:
  `#0CC0DF` (cyan).

**Style rules to enforce in any prose you generate around the narrative
(captions, table header cells, the "what it tells us" column):** UK
spelling, no em dashes, no Oxford comma, metric/euro. The Anthropic
narrative is already under these rules via the system prompt, but
anything `report.py` writes itself must obey too.

### 4. `src/cli.py` — wiring

```bash
python -m src.cli samples/session.mp3 \
    --candidate "Test Name" \
    --session "Mock interview" \
    --date "1 June 2026" \
    [--previous output/<earlier-run>/metrics.json]
```

Flow:

1. Load `.env` (`python-dotenv`).
2. Load config via `src.config.load_config()`.
3. `transcribe()` -> `TranscriptData`.
4. `analyse()` -> `ProsodyData` (passing sentence-end timestamps from
   `TranscriptData.sentences` if present).
5. `compute_all_metrics()` -> metrics dict.
6. Print a tight terminal summary: pace (gross/net, status), itemised
   filler counts, weak word top three, opener percentage with top
   offender, pitch/pause/energy lines, and any sanity warnings. This is
   what James reads during the session.
7. `generate_coaching_narrative()` -> narrative dict.
8. `render_report()` -> `output/<candidate>-<date>/report.docx`.
9. Persist `metrics.json` and `narrative.json` next to it for the
   comparative-mode flow.

Also stub `--local-transcription` as documented in the README (it can
raise `NotImplementedError` for now).

## Contracts to respect

- **`TranscriptData`, `Word`, `Sentence`, `ProsodyData`, `PauseEvent`,
  `MonotonePassage`** are defined in `src/metrics.py`. Import them, do
  not redefine.
- **Metrics dict shape** — see `compute_all_metrics()` return value and
  the tests in `tests/test_metrics.py`.
- **Narrative dict shape** — see `NARRATIVE_SCHEMA` in `src/coach.py`.
  The report renderer must tolerate every required key being present.

## Hard constraints (do not soften)

- **Filler metric is the whole point.** Sanity-check that disfluencies
  are coming through (the engine already warns if zero fillers appear in
  a clip over a minute).
- **Pace uses real speaking time from word timestamps,** never an
  estimated denominator.
- **Tone is measured.** If prosody fails, the report says so. Never
  fabricate a pitch number from word choice.
- **UK spelling, no em dashes, no Oxford comma, metric/euro** in all
  user-facing prose (terminal output and report).
- **`.env`** holds keys and is gitignored. Never log API keys.

## Target bands

Placeholders in `config.yaml`. James will tune against real samples
after the first end-to-end run. Two values in particular need samples:

- `prosody.monotone_pitch_std_semitones_threshold` (currently 2.0)
- `prosody.trailing_off_db_drop` (currently 9.0)

After the first real recording, print measured pitch std and a few
sentence-end energy deltas alongside the rendered report so James can
calibrate these against what he hears.

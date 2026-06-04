# Handoff — Delivery Lab Session 2

## Status

**Completed in Session 1:**
- ✅ src/metrics.py (18/18 tests passing)
- ✅ src/coach.py (OpenAI gpt-4o integration wired correctly)
- ✅ src/transcribe.py (AssemblyAI wrapper with duration fix)
- ✅ src/prosody.py (librosa + parselmouth analysis)
- ✅ src/report.py (python-docx renderer with XML fixes)
- ✅ src/cli.py (CLI end-to-end tested)
- ✅ config.yaml (configured for gpt-4o)

**Session 2 Completed:**
- ✅ First end-to-end test with Brian O'Flynn mock interview recording
- ✅ Duration calculation fixed (was returning 0.55s, now correctly calculates from word timings)
- ✅ OpenAI API integration fixed (system_prompt → messages array)
- ✅ Report rendering XML fixed
- ✅ Tips parsing fixed (now correctly handles dict structure from gpt-4o)

## Issues Fixed in Session 1

1. **AssemblyAI API compatibility** — Fixed `transcript.sentences` → `transcript.get_sentences()` method call
2. **Transcript object attributes** — Made `_save_raw_response()` defensive to handle missing attributes gracefully
3. **OpenAI integration** — Rewired coach.py from Anthropic to OpenAI gpt-4o with proper function calling format

## Issues Fixed in Session 2

1. **Unicode emoji encoding** — Windows cp1252 encoding, replaced all emojis with ASCII [LABEL] format
2. **LibrosaAI split() API** — Removed invalid `min_duration` parameter (already filtered after split)
3. **OpenAI chat.completions API** — Changed `system_prompt` parameter to messages array with role="system"
4. **Report XML shading** — Fixed malformed w:shd attribute syntax
5. **Tips parsing** — Tips are dict objects with "tip" and "rationale" fields, not strings
6. **Duration calculation** — AssemblyAI's `audio_duration` was returning 550ms for 9-minute audio. Now uses actual word timings as source of truth

## Next Steps

### Immediate (Session 3)

**Critical prosody bugs to fix:**

1. **Pause detection overflow** — 1,398 pauses with 183,780 seconds total (50+ hours) when audio is 545 seconds
   - Bug likely in `src/prosody.py:_extract_pauses()` 
   - Check librosa.effects.split() output and how frames are converted to time
   - Validate: `librosa.frames_to_time()` unit conversions

2. **Pitch measurement failure** — Returns "not_measured" instead of pitch analysis
   - Check parselmouth or librosa pitch extraction in `src/prosody.py:_extract_pitch()`
   - May be audio format incompatibility or parameter issue

3. **Test with additional recordings** to validate narrative quality beyond metrics issues

### After Prosody Fixes

4. **Calibrate prosody thresholds** against real recordings:
   - Once pitch/pause data is reliable, validate measured values match auditory perception
   - Tune `config.yaml`:
     - `prosody.monotone_pitch_std_semitones_threshold` (currently 2.0)
     - `prosody.trailing_off_db_drop` (currently 9.0)

5. **Narrative quality check**:
   - Does gpt-4o narrative feel natural and coachable?
   - Does it follow UK spelling, no em dashes, no Oxford comma rules? ✅ Confirmed
   - Does it cite measured numbers correctly? ✅ Confirmed

## Important Files

- **config.yaml** — All thresholds and model settings (gpt-4o configured)
- **src/coach.py** — OpenAI integration (uses function_calling, not tool_use)
- **src/cli.py** — Main entry point for analysis
- **.env** — API keys (OPENAI_API_KEY, ASSEMBLYAI_API_KEY required)

## Testing Command Template

```bash
python -m src.cli "PATH_TO_AUDIO.mp3" \
    --candidate "NAME" \
    --session "SESSION_TYPE" \
    --date "DATE"
```

## Known Limitations

- `--local-transcription` flag stubbed as NotImplementedError (not yet implemented)
- Prosody thresholds are placeholders pending calibration against real samples
- Pause detection is broken (overflow in silence frame calculations)
- Pitch measurement is not working (returns not_measured status)

## Context for Next Session

- This is a Python CLI tool for analysing delivery (pace, tone, fillers, structure) from recorded media training sessions
- Outputs a branded .docx report with measured metrics + coaching narrative
- Uses AssemblyAI for transcription (with disfluencies=True — critical for filler detection)
- Uses gpt-4o for narrative generation (system prompt encodes James Dunny's coaching model)
- Uses librosa + parselmouth for prosody analysis
- All user-facing text must follow: UK spelling, no em dashes, no Oxford comma, metric/euro units

## Session 2 Test Results

**Test Command:**
```bash
python -m src.cli "C:\Users\james\Downloads\Jun-02-12-22-PM_2026-06-02.mp3" \
    --candidate "Brian O'Flynn" \
    --session "Mock interview" \
    --date "2 June 2026"
```

**Output Generated:**
- ✅ `report.docx` (38.9 KB) — branded report with metrics and narrative
- ✅ `metrics.json` (2.5 KB) — raw metrics data  
- ✅ `narrative.json` (2.8 KB) — coaching narrative

**Metrics (Brian O'Flynn):**
- Pace: 219.6 wpm gross (target 140-165, status: hard_fast)
- Fillers: 1.1 per 100 words (23 total: 14 um, 9 uh) — status: green ✅
- Weak words: 2.54 per 100 words (top: "i suppose" 15x, "kind of" 13x) — status: green ✅
- Sentence openers: 51% crutch words (mostly "so") — status: watch
- Sentence shape: 20.9 words avg, 59 max — status: green ✅
- Pitch: not measured ❌
- Pauses: 1,398 detected (broken calculation) ❌
- Energy: 29.5 dB dynamic range, 16 trailing-off events — status: watch

**Narrative Quality:**
- Personalized greeting and context ✅
- Specific metrics cited correctly ✅
- UK spelling and tone ✅
- No Oxford commas ✅
- Three ranked, actionable tips ✅
- Warm, encouraging closing ✅

**Issues to Address Next:**
1. Pause detection calculation is broken (overflow)
2. Pitch measurement not working
3. Despite these, the core pipeline works and generates quality narratives

---

**Ready for Session 3: Debug prosody metrics and validate with additional recordings.**

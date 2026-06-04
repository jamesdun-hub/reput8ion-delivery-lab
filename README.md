# Reput8ion Delivery Lab

A trainer's command-line instrument. Takes an audio file of a media-training
session and produces:

1. Hard delivery metrics to the terminal, for James during or immediately
   after the session.
2. A formal branded `.docx` feedback report the participant takes away.

This is not a participant-facing app. James stays in the room and delivers
the coaching. The tool puts objective numbers underneath his judgement.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
# Edit .env and fill in ASSEMBLYAI_API_KEY and ANTHROPIC_API_KEY
```

## Run

```bash
python -m src.cli samples\session.mp3 ^
    --candidate "Test Name" ^
    --session "Mock interview" ^
    --date "1 June 2026"
```

Outputs a branded `.docx` to `output/` and a `metrics.json` alongside it.
Optionally pass `--previous output/<earlier-run>/metrics.json` to frame the
narrative comparatively against an earlier session.

## What it measures

**From the transcript (AssemblyAI, with `disfluencies=True`):**

- Pace in words per minute, gross and net, plus a per-window breakdown so
  passages of passion or panic are visible.
- Filler words: total and by token (um, uh, er, erm, ah, hmm, eh), plus a
  per-100-words rate.
- Weak hedging words and phrases (sort of, kind of, I think, just, really…).
- Sentence-opener crutches (so, well, and, but, yeah, I mean, you know…)
  as a percentage of sentences.
- Average sentence length and lexical variety.

**From the waveform (librosa + parselmouth):**

- Pitch contour. Mean pitch, pitch range, and a monotone score with the
  flattest passages timestamped.
- Pauses above 0.5s, split into sentence-boundary (controlled) and
  mid-sentence (hesitation) where possible.
- Energy dynamic range, with sentence-end "trailing off" flagged.

All thresholds and word lists live in `config.yaml` and are tunable without
touching the code.

## Privacy

Audio is uploaded to AssemblyAI (US) and metrics text is sent to the
Anthropic API. This is acceptable for standard media training but is a
conscious choice. A `--local-transcription` mode using openai-whisper is
stubbed for genuinely sensitive sessions in a future version.

## Build status

| Stage | Status |
| --- | --- |
| Config and scaffolding | done |
| Metrics engine (pure functions) | done |
| Unit tests for metrics | done |
| Coaching prompt (Anthropic) | done |
| AssemblyAI transcription wrapper | pending |
| Prosody (librosa + parselmouth) | pending |
| Report generation (python-docx) | pending |
| CLI | pending |
| Comparative mode | pending |

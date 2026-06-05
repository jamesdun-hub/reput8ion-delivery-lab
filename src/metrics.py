"""
Pure metrics engine for Reput8ion Delivery Lab.

Takes a transcript with word-level timing (from AssemblyAI with
disfluencies=True) and optional prosody data (from prosody.py), and returns
a JSON-serialisable dict of measured delivery metrics, each tagged with a
status against the bands in config.yaml.

No I/O. No external API calls. Deterministic, unit-tested.

Honesty rule: if prosody is absent or a measurement failed, the relevant
fields are marked status="not_measured" and a value of None. Never fabricate
a tone or pitch number from text.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable


# ---------- Input dataclasses ----------

@dataclass
class Word:
    """A single word with timing in seconds. Mirrors AssemblyAI's shape."""
    text: str
    start: float
    end: float
    confidence: float = 1.0
    speaker: str | None = None


@dataclass
class Sentence:
    """An optional pre-segmented sentence from AssemblyAI."""
    text: str
    start: float
    end: float


@dataclass
class TranscriptData:
    """Everything we need from the transcription stage."""
    words: list[Word]
    text: str
    duration_seconds: float
    sentences: list[Sentence] | None = None
    speaker_summary: dict | None = None


def filter_to_speaker(transcript: "TranscriptData", speaker_id: str) -> "TranscriptData":
    """Return a new TranscriptData containing only words from one speaker.

    duration_seconds is preserved as the full session length so gross pace
    measures how much of the session the interviewee spent speaking.
    """
    filtered = [w for w in transcript.words if w.speaker == speaker_id]
    text = " ".join(w.text for w in filtered)
    return TranscriptData(
        words=filtered,
        text=text,
        duration_seconds=transcript.duration_seconds,
        sentences=None,  # let metrics engine split from reconstructed text
        speaker_summary=transcript.speaker_summary,
    )


@dataclass
class PauseEvent:
    start: float
    end: float
    duration: float
    at_sentence_boundary: bool


@dataclass
class MonotonePassage:
    start: float
    end: float
    pitch_std_semitones: float


@dataclass
class ProsodyData:
    """Numeric prosody summary produced by prosody.py. All floats are scalars
    so the metrics engine never depends on numpy."""
    mean_pitch_hz: float
    pitch_range_hz: float
    pitch_std_semitones: float
    monotone_passages: list[MonotonePassage]
    pauses: list[PauseEvent]
    speaking_time_seconds: float
    dynamic_range_db: float
    trailing_off_events: list[float] = field(default_factory=list)
    pitch_windows: list[dict] = field(default_factory=list)
    pitch_measured: bool = True
    energy_measured: bool = True


# ---------- Tokenisation helpers ----------

# Keep apostrophes (don't, I'm) but strip surrounding punctuation.
_WORD_RE = re.compile(r"[a-z0-9']+", re.IGNORECASE)
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def normalise_tokens(text: str) -> list[str]:
    """Lowercase token sequence from raw text, punctuation stripped."""
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def split_sentences_from_text(text: str) -> list[str]:
    """Punctuation-based fallback if no sentence segmentation is provided."""
    chunks = [c.strip() for c in _SENT_SPLIT_RE.split(text.strip()) if c.strip()]
    return chunks or ([text.strip()] if text.strip() else [])


def _count_phrase_occurrences(tokens: list[str], phrase: str) -> int:
    """Count non-overlapping occurrences of a multi-word phrase in tokens."""
    phrase_tokens = phrase.lower().split()
    n = len(phrase_tokens)
    if n == 0:
        return 0
    hits = 0
    i = 0
    while i <= len(tokens) - n:
        if tokens[i:i + n] == phrase_tokens:
            hits += 1
            i += n
        else:
            i += 1
    return hits


# ---------- Status banding ----------

def _band(value: float, cfg: dict, kind: str) -> str:
    """Compute a categorical status for a numeric metric against config."""
    if kind == "pace":
        if value < cfg["slow_warning"]:
            return "too_slow"
        if value > cfg["fast_hard"]:
            return "hard_fast"
        if value > cfg["fast_warning"]:
            return "edge_fast"
        if cfg["ideal_min"] <= value <= cfg["ideal_max"]:
            return "ideal"
        return "watch"
    if kind == "filler_per_100":
        if value <= cfg["green_per_100_words"]:
            return "green"
        if value >= cfg["watch_per_100_words"]:
            return "watch"
        return "amber"
    if kind == "weak_per_100":
        return "watch" if value >= cfg["watch_per_100_words"] else "green"
    if kind == "opener_pct":
        return "watch" if value >= cfg["watch_percentage"] else "green"
    if kind == "sentence_len":
        return "watch" if value >= cfg["watch_avg_words"] else "green"
    return "neutral"


# ---------- Pace ----------

def compute_pace(
    transcript: TranscriptData,
    prosody: ProsodyData | None,
    cfg: dict,
) -> dict:
    """Pace in wpm: gross over total duration, net over speaking time, plus
    a per-window breakdown using word timestamps."""
    words = transcript.words
    word_count = len(words)
    duration = transcript.duration_seconds

    gross_wpm = (word_count / duration * 60.0) if duration > 0 else 0.0

    # Speaking time: subtract pause time when prosody is available, else
    # fall back to gross duration. Never use a guessed denominator.
    if prosody is not None and prosody.speaking_time_seconds > 0:
        speaking_time = prosody.speaking_time_seconds
    else:
        speaking_time = duration
    net_wpm = (word_count / speaking_time * 60.0) if speaking_time > 0 else 0.0

    # Per-window breakdown.
    window = float(cfg["window_seconds"])
    windows: list[dict] = []
    if duration > 0 and window > 0 and words:
        n_windows = int(duration // window) + (1 if duration % window > 0 else 0)
        for w in range(n_windows):
            t0 = w * window
            t1 = min((w + 1) * window, duration)
            wc = sum(1 for word in words if t0 <= word.start < t1)
            secs = max(t1 - t0, 1e-6)
            windows.append({
                "start_seconds": round(t0, 2),
                "end_seconds": round(t1, 2),
                "words": wc,
                "wpm": round(wc / secs * 60.0, 1),
            })

    return {
        "word_count": word_count,
        "duration_seconds": round(duration, 2),
        "speaking_time_seconds": round(speaking_time, 2),
        "gross_wpm": round(gross_wpm, 1),
        "net_wpm": round(net_wpm, 1),
        "status": _band(net_wpm, cfg, "pace"),
        "windows": windows,
        "target_band": f"{cfg['ideal_min']}-{cfg['ideal_max']} wpm",
    }


# ---------- Fillers ----------

def compute_fillers(
    transcript: TranscriptData,
    cfg: dict,
    acoustic_filler_count: int = 0,
) -> dict:
    """Count filler tokens and phrases against the configured filler set.

    Two-pass approach:
    1. Single-token disfluencies (um, uh, er, ...) from the ASR word stream.
       Note: ASR under-counts these; acoustic_filler_count supplements them.
    2. Multi-word filler phrases ("you know", "i mean", ...) from the
       normalised transcript text using the same phrase-matcher as weak words.

    acoustic_filler_count: probable hesitation sounds detected from the
    audio waveform independent of ASR (see detect_acoustic_fillers()).
    """
    filler_set = {t.lower() for t in cfg.get("tokens", [])}
    phrase_list = [p.lower() for p in cfg.get("phrases", [])]
    tokens = normalise_tokens(transcript.text)
    total_words = len(tokens)

    # Single-token pass
    by_token: Counter = Counter(t for t in tokens if t in filler_set)

    # Phrase pass
    by_phrase: Counter = Counter()
    for phrase in phrase_list:
        hits = _count_phrase_occurrences(tokens, phrase)
        if hits:
            by_phrase[phrase] = hits

    asr_total = sum(by_token.values()) + sum(by_phrase.values())

    # Acoustic supplement: if ASR missed um/uh sounds, the acoustic detector
    # provides an independent estimate. We take the max of ASR token counts
    # and the acoustic estimate for the "raw um/uh" bucket, then add phrases.
    phrase_total = sum(by_phrase.values())
    asr_token_total = sum(by_token.values())

    # If acoustic count exceeds what ASR found in tokens, the difference
    # represents sounds the ASR missed. We record this separately so the
    # report can surface "X probable additional hesitation sounds detected".
    acoustic_gap = max(0, acoustic_filler_count - asr_token_total)

    total_fillers = asr_total + acoustic_gap
    per_100 = (total_fillers / total_words * 100.0) if total_words > 0 else 0.0

    combined = dict(sorted({**dict(by_token), **dict(by_phrase)}.items(), key=lambda kv: -kv[1]))
    if acoustic_gap > 0:
        combined["[probable um/uh - acoustic]"] = acoustic_gap

    return {
        "total": total_fillers,
        "asr_total": asr_total,
        "acoustic_filler_count": acoustic_filler_count,
        "acoustic_gap": acoustic_gap,
        "by_token": combined,
        "per_100_words": round(per_100, 2),
        "status": _band(per_100, cfg, "filler_per_100"),
        "total_words": total_words,
    }


# ---------- Weak / hedging words ----------

def compute_weak_words(transcript: TranscriptData, cfg: dict) -> dict:
    """Count hedging single tokens and multi-word phrases. Single tokens are
    counted first; phrase counts are independent (they catch things like
    'I think' that single-word matching wouldn't).
    """
    tokens = normalise_tokens(transcript.text)
    total_words = len(tokens)

    single_set = {w.lower() for w in cfg.get("single", [])}
    phrase_list = [p.lower() for p in cfg.get("phrases", [])]

    by_term: Counter[str] = Counter()
    for tok in tokens:
        if tok in single_set:
            by_term[tok] += 1
    for phrase in phrase_list:
        hits = _count_phrase_occurrences(tokens, phrase)
        if hits:
            by_term[phrase] = hits

    total = sum(by_term.values())
    per_100 = (total / total_words * 100.0) if total_words > 0 else 0.0
    top = dict(sorted(by_term.items(), key=lambda kv: -kv[1])[:8])

    return {
        "total": total,
        "by_term": dict(sorted(by_term.items(), key=lambda kv: -kv[1])),
        "top_offenders": top,
        "per_100_words": round(per_100, 2),
        "status": _band(per_100, cfg, "weak_per_100"),
    }


# ---------- Sentences and openers ----------

def _sentence_texts(transcript: TranscriptData) -> list[str]:
    if transcript.sentences:
        return [s.text for s in transcript.sentences if s.text.strip()]
    return split_sentences_from_text(transcript.text)


def compute_sentence_openers(transcript: TranscriptData, cfg: dict) -> dict:
    """Percentage of sentences beginning with a crutch word or phrase, with
    a per-crutch breakdown."""
    sentences = _sentence_texts(transcript)
    n = len(sentences)
    single_crutches = {w.lower() for w in cfg["crutches"].get("single", [])}
    phrase_crutches = [p.lower().split() for p in cfg["crutches"].get("phrases", [])]

    by_opener: Counter[str] = Counter()
    crutch_count = 0
    for sent in sentences:
        toks = normalise_tokens(sent)
        if not toks:
            continue
        matched_phrase = None
        for ptoks in phrase_crutches:
            if len(toks) >= len(ptoks) and toks[:len(ptoks)] == ptoks:
                matched_phrase = " ".join(ptoks)
                break
        if matched_phrase is not None:
            by_opener[matched_phrase] += 1
            crutch_count += 1
        elif toks[0] in single_crutches:
            by_opener[toks[0]] += 1
            crutch_count += 1

    pct = (crutch_count / n * 100.0) if n > 0 else 0.0

    return {
        "sentence_count": n,
        "crutch_count": crutch_count,
        "crutch_percentage": round(pct, 1),
        "by_opener": dict(sorted(by_opener.items(), key=lambda kv: -kv[1])),
        "status": _band(pct, cfg, "opener_pct"),
    }


def compute_sentence_shape(transcript: TranscriptData, cfg: dict) -> dict:
    """Average sentence length in words and lexical variety."""
    sentences = _sentence_texts(transcript)
    sent_lengths = [len(normalise_tokens(s)) for s in sentences]
    sent_lengths = [n for n in sent_lengths if n > 0]
    avg_len = (sum(sent_lengths) / len(sent_lengths)) if sent_lengths else 0.0

    tokens = normalise_tokens(transcript.text)
    unique = len(set(tokens))
    lexical_variety = (unique / len(tokens)) if tokens else 0.0

    return {
        "sentence_count": len(sent_lengths),
        "avg_sentence_length_words": round(avg_len, 1),
        "longest_sentence_words": max(sent_lengths) if sent_lengths else 0,
        "status": _band(avg_len, cfg, "sentence_len"),
        "unique_words": unique,
        "total_words": len(tokens),
        "lexical_variety": round(lexical_variety, 3),
    }


# ---------- Prosody-derived metrics ----------

def compute_pitch(prosody: ProsodyData | None, cfg: dict) -> dict:
    """Pitch metrics. If prosody is absent or pitch tracking failed, returns
    status='not_measured' with values of None. Never inferred from text."""
    if prosody is None or not prosody.pitch_measured:
        return {
            "status": "not_measured",
            "mean_hz": None,
            "range_hz": None,
            "std_semitones": None,
            "monotone_passages": [],
        }
    std_st = prosody.pitch_std_semitones
    is_monotone = std_st < cfg["monotone_pitch_std_semitones_threshold"]
    passages = [
        {
            "start_seconds": round(p.start, 2),
            "end_seconds": round(p.end, 2),
            "duration_seconds": round(p.end - p.start, 2),
            "pitch_std_semitones": round(p.pitch_std_semitones, 2),
        }
        for p in prosody.monotone_passages
        if (p.end - p.start) >= cfg["monotone_passage_min_duration_seconds"]
    ]
    return {
        "status": "watch" if is_monotone else "green",
        "mean_hz": round(prosody.mean_pitch_hz, 1),
        "range_hz": round(prosody.pitch_range_hz, 1),
        "std_semitones": round(std_st, 2),
        "is_monotone_overall": is_monotone,
        "monotone_passages": passages,
    }


def compute_pauses(prosody: ProsodyData | None, cfg: dict) -> dict:
    if prosody is None:
        return {"status": "not_measured", "count": None}
    pauses = [p for p in prosody.pauses if p.duration >= cfg["pause_min_duration_seconds"]]
    if not pauses:
        return {
            "status": "green",
            "count": 0,
            "total_silent_seconds": 0.0,
            "avg_seconds": 0.0,
            "longest_seconds": 0.0,
            "at_sentence_boundary": 0,
            "mid_sentence": 0,
        }
    total = sum(p.duration for p in pauses)
    avg = total / len(pauses)
    longest = max(p.duration for p in pauses)
    boundary = sum(1 for p in pauses if p.at_sentence_boundary)
    mid = len(pauses) - boundary
    return {
        "status": "green",
        "count": len(pauses),
        "total_silent_seconds": round(total, 2),
        "avg_seconds": round(avg, 2),
        "longest_seconds": round(longest, 2),
        "at_sentence_boundary": boundary,
        "mid_sentence": mid,
    }


def compute_energy(prosody: ProsodyData | None, cfg: dict) -> dict:
    if prosody is None or not prosody.energy_measured:
        return {"status": "not_measured", "dynamic_range_db": None}
    trailing = list(prosody.trailing_off_events or [])
    return {
        "status": "watch" if trailing else "green",
        "dynamic_range_db": round(prosody.dynamic_range_db, 1),
        "trailing_off_count": len(trailing),
        "trailing_off_timestamps": [round(t, 2) for t in trailing],
    }


# ---------- Repetition ----------

def compute_repetition(transcript: TranscriptData, cfg: dict) -> dict:
    """Detect phrases repeated at or above the configured threshold.

    Uses n-gram counting over the normalised token stream. Sub-phrases of
    a longer repeated phrase are suppressed so 'kind of think' does not
    swamp 'kind of'.
    """
    rep_cfg = cfg.get("repetition", {})
    min_words = int(rep_cfg.get("min_phrase_words", 3))
    flag_at = int(rep_cfg.get("flag_at_count", 3))

    tokens = normalise_tokens(transcript.text)
    if len(tokens) < min_words:
        return {"repeated_phrases": {}, "total_flagged": 0}

    counts: Counter[str] = Counter()
    max_n = min(7, len(tokens))
    for n in range(min_words, max_n + 1):
        for i in range(len(tokens) - n + 1):
            counts[" ".join(tokens[i : i + n])] += 1

    repeated = {p: c for p, c in counts.items() if c >= flag_at}

    # Suppress sub-phrases: if a phrase is a strict substring of a longer
    # repeated phrase with the same or higher count, drop the shorter one.
    sorted_by_len = sorted(repeated.items(), key=lambda kv: -len(kv[0]))
    kept: dict[str, int] = {}
    for phrase, count in sorted_by_len:
        if not any(phrase in longer and phrase != longer for longer in kept):
            kept[phrase] = count

    top = dict(sorted(kept.items(), key=lambda kv: -kv[1])[:10])

    # Repetition %: excess instances × phrase length / total words
    total_words = len(tokens)
    excess_words = sum(
        (count - 1) * len(phrase.split())
        for phrase, count in top.items()
    )
    repetition_pct = round(excess_words / total_words * 100, 1) if total_words > 0 else 0.0

    return {
        "repeated_phrases": top,
        "total_flagged": len(top),
        "repetition_pct": repetition_pct,
    }


# ---------- Control signals ----------

def compute_control_signals(transcript: TranscriptData, cfg: dict) -> dict:
    """Detect bridge, flag, and hook language in the transcript.

    Phrase lists are loaded from config.yaml (control section) so James can
    add or remove phrases without changing any Python.
    """
    control_cfg = cfg.get("control", {})
    bridge_phrases = [p.lower() for p in control_cfg.get("bridge_phrases", [])]
    flag_phrases = [p.lower() for p in control_cfg.get("flag_phrases", [])]
    hook_phrases = [p.lower() for p in control_cfg.get("hook_phrases", [])]

    text_lower = transcript.text.lower()

    def _find(phrases: list[str]) -> tuple[list[str], int]:
        found = [p for p in phrases if p in text_lower]
        count = sum(text_lower.count(p) for p in found)
        return found[:6], count

    bridges_found, bridge_count = _find(bridge_phrases)
    flags_found, flag_count = _find(flag_phrases)
    hooks_found, hook_count = _find(hook_phrases)

    return {
        "bridge_count": bridge_count,
        "bridges_detected": bridges_found,
        "flag_count": flag_count,
        "flags_detected": flags_found,
        "hook_count": hook_count,
        "hooks_detected": hooks_found,
        "total_control_signals": bridge_count + flag_count + hook_count,
    }


# ---------- Story signals ----------

def compute_story_signals(transcript: TranscriptData, cfg: dict) -> dict:
    """Assess headline discipline: are answers opened with a declarative
    statement (strong) or a hedge (buried lead)?

    Phrase lists are loaded from config.yaml (story section).
    """
    story_cfg = cfg.get("story", {})
    hedged = [p.lower() for p in story_cfg.get("hedged_openers", [])]
    declarative = [p.lower() for p in story_cfg.get("declarative_openers", [])]

    sentences = _sentence_texts(transcript)
    n = len(sentences)
    hedged_count = 0
    declarative_count = 0

    for sent in sentences:
        s = sent.lower().strip()
        if any(s.startswith(h) for h in hedged):
            hedged_count += 1
        elif any(s.startswith(d) for d in declarative):
            declarative_count += 1

    hedged_pct = round(hedged_count / n * 100, 1) if n > 0 else 0.0
    declarative_pct = round(declarative_count / n * 100, 1) if n > 0 else 0.0

    return {
        "sentence_count": n,
        "hedged_openings": hedged_count,
        "hedged_opening_pct": hedged_pct,
        "declarative_openings": declarative_count,
        "declarative_opening_pct": declarative_pct,
        "headline_status": (
            "green" if declarative_pct >= 20 and hedged_pct < 30
            else "watch" if hedged_pct >= 30
            else "neutral"
        ),
    }


# ---------- Top-level assembly ----------

def compute_all_metrics(
    transcript: TranscriptData,
    prosody: ProsodyData | None,
    config: dict,
    acoustic_filler_count: int = 0,
) -> dict:
    """Run every metric and return a single JSON-serialisable dict.

    The shape of this dict is the contract between the metrics engine, the
    Anthropic coaching prompt (coach.py), the report renderer (report.py)
    and the terminal output (cli.py). Keep keys stable.
    """
    pace = compute_pace(transcript, prosody, config["pace"])
    fillers = compute_fillers(transcript, config["filler_words"], acoustic_filler_count)
    weak = compute_weak_words(transcript, config["weak_words"])
    openers = compute_sentence_openers(transcript, config["sentence_openers"])
    shape = compute_sentence_shape(transcript, config["sentence_length"])
    pitch = compute_pitch(prosody, config["prosody"])
    pauses = compute_pauses(prosody, config["prosody"])
    energy = compute_energy(prosody, config["prosody"])
    repetition = compute_repetition(transcript, config.get("control", {}))
    control_signals = compute_control_signals(transcript, config)
    story_signals = compute_story_signals(transcript, config)

    warnings = list(_sanity_warnings(transcript, fillers))

    return {
        "schema_version": 1,
        "pace": pace,
        "fillers": fillers,
        "weak_words": weak,
        "sentence_openers": openers,
        "sentence_shape": shape,
        "pitch": pitch,
        "pauses": pauses,
        "energy": energy,
        "repetition": repetition,
        "control_signals": control_signals,
        "story_signals": story_signals,
        "warnings": warnings,
    }


def _sanity_warnings(transcript: TranscriptData, fillers: dict) -> Iterable[str]:
    """Soft checks that catch the failure modes the brief calls out."""
    if transcript.duration_seconds >= 60 and fillers["total"] == 0:
        yield (
            "Filler count is zero on a recording longer than a minute. "
            "Confirm AssemblyAI was called with disfluencies=True and that "
            "the transcript is not a post-cleaned export (Fireflies strips fillers)."
        )
    if transcript.duration_seconds <= 0:
        yield "Audio duration is zero or unknown; pace metrics are unreliable."
    # Catch the prototype bug: word-count over a guessed duration.
    if transcript.duration_seconds > 0:
        gross_wpm = len(transcript.words) / transcript.duration_seconds * 60.0
        if gross_wpm > 220:
            yield (
                f"Gross pace reads {gross_wpm:.0f} wpm — suspicious for natural "
                "speech. Confirm duration is from the audio file, not estimated."
            )

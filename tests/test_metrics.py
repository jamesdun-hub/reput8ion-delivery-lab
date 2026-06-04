"""Unit tests for the pure metrics engine.

These tests use fabricated transcripts with known word timings so that the
expected outputs are computable by hand. No audio, no network, no prosody
needed unless a test specifically exercises prosody-dependent code.
"""

from __future__ import annotations

import pytest

from src.metrics import (
    MonotonePassage,
    PauseEvent,
    ProsodyData,
    Sentence,
    TranscriptData,
    Word,
    compute_all_metrics,
    compute_fillers,
    compute_pace,
    compute_pitch,
    compute_sentence_openers,
    compute_sentence_shape,
    compute_weak_words,
    normalise_tokens,
)


# ---------- Helpers ----------

def _make_words(text: str, wpm: float = 150.0) -> tuple[list[Word], float]:
    """Distribute words evenly across time at the requested wpm so that pace
    calculations have a known expected answer."""
    tokens = text.split()
    seconds_per_word = 60.0 / wpm
    out: list[Word] = []
    t = 0.0
    for tok in tokens:
        out.append(Word(text=tok, start=t, end=t + seconds_per_word * 0.8))
        t += seconds_per_word
    duration = t
    return out, duration


def _cfg() -> dict:
    """Minimal config matching the schema in src/metrics.py."""
    return {
        "pace": {
            "ideal_min": 140,
            "ideal_max": 165,
            "fast_warning": 165,
            "fast_hard": 175,
            "slow_warning": 120,
            "window_seconds": 30,
        },
        "filler_words": {
            "tokens": ["um", "uh", "er", "erm", "ah", "hmm", "eh"],
            "green_per_100_words": 1.5,
            "watch_per_100_words": 3.0,
        },
        "weak_words": {
            "single": ["just", "really", "very", "actually", "like"],
            "phrases": ["sort of", "kind of", "i think", "you know"],
            "watch_per_100_words": 4.0,
        },
        "sentence_openers": {
            "crutches": {
                "single": ["so", "well", "and", "but", "yeah", "okay"],
                "phrases": ["i mean", "you know"],
            },
            "watch_percentage": 20,
        },
        "sentence_length": {"watch_avg_words": 24},
        "prosody": {
            "pause_min_duration_seconds": 0.5,
            "monotone_pitch_std_semitones_threshold": 2.0,
            "monotone_passage_min_duration_seconds": 8.0,
            "trailing_off_db_drop": 9.0,
        },
    }


# ---------- Tokenisation ----------

def test_normalise_tokens_keeps_contractions_and_strips_punctuation():
    assert normalise_tokens("I don't know, really!") == ["i", "don't", "know", "really"]


# ---------- Pace ----------

def test_pace_gross_and_net_match_when_no_prosody():
    text = " ".join(["hello"] * 150)
    words, dur = _make_words(text, wpm=150.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_pace(tx, prosody=None, cfg=_cfg()["pace"])
    assert 148 <= out["gross_wpm"] <= 152
    assert out["gross_wpm"] == out["net_wpm"]
    assert out["status"] == "ideal"
    assert out["windows"], "expected at least one per-window bucket"


def test_pace_net_uses_speaking_time_when_prosody_present():
    text = " ".join(["word"] * 100)
    words, dur = _make_words(text, wpm=120.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    prosody = ProsodyData(
        mean_pitch_hz=180.0,
        pitch_range_hz=80.0,
        pitch_std_semitones=3.0,
        monotone_passages=[],
        pauses=[],
        speaking_time_seconds=dur / 2,  # half the audio was silence
        dynamic_range_db=12.0,
    )
    out = compute_pace(tx, prosody=prosody, cfg=_cfg()["pace"])
    # Net should be ~double gross because speaking time is half the duration.
    assert out["net_wpm"] == pytest.approx(out["gross_wpm"] * 2, rel=0.02)


def test_pace_status_bands():
    cfg = _cfg()["pace"]
    text = " ".join(["w"] * 200)
    words, dur = _make_words(text, wpm=200.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_pace(tx, prosody=None, cfg=cfg)
    assert out["status"] == "hard_fast"

    words, dur = _make_words(text, wpm=100.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_pace(tx, prosody=None, cfg=cfg)
    assert out["status"] == "too_slow"


# ---------- Fillers ----------

def test_filler_counts_by_token_and_per_100():
    text = "um so I was uh thinking about er the project and um the um plan"
    # tokens: um(3), uh(1), er(1); total tokens = 16
    words, dur = _make_words(text, wpm=150.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_fillers(tx, _cfg()["filler_words"])
    assert out["total"] == 5
    assert out["by_token"]["um"] == 3
    assert out["by_token"]["uh"] == 1
    assert out["by_token"]["er"] == 1
    # 5 / 16 * 100 = 31.25; well above the watch threshold
    assert out["per_100_words"] > 3.0
    assert out["status"] == "watch"


def test_filler_zero_when_clean():
    text = "I delivered the message with clarity and structure."
    words, dur = _make_words(text, wpm=150.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_fillers(tx, _cfg()["filler_words"])
    assert out["total"] == 0
    assert out["status"] == "green"


# ---------- Weak words and phrases ----------

def test_weak_words_count_single_and_phrases():
    text = "I think this is just a sort of basic idea, really. Kind of like a test."
    # 'just' 'really' 'like' as singles; 'i think', 'sort of', 'kind of' as phrases
    words, dur = _make_words(text, wpm=150.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_weak_words(tx, _cfg()["weak_words"])
    assert out["by_term"]["just"] == 1
    assert out["by_term"]["really"] == 1
    assert out["by_term"]["like"] == 1
    assert out["by_term"]["i think"] == 1
    assert out["by_term"]["sort of"] == 1
    assert out["by_term"]["kind of"] == 1
    assert out["total"] == 6


def test_weak_phrase_non_overlap():
    # "sort of sort of" is two non-overlapping hits, not three
    text = "sort of sort of sort of"
    words, dur = _make_words(text, wpm=150.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_weak_words(tx, _cfg()["weak_words"])
    assert out["by_term"]["sort of"] == 3


# ---------- Sentence openers ----------

def test_sentence_openers_single_and_phrase_crutches():
    text = (
        "So this is one thing. Well that is another. "
        "I mean obviously this matters. And finally, here we are."
    )
    words, dur = _make_words(text, wpm=150.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_sentence_openers(tx, _cfg()["sentence_openers"])
    assert out["sentence_count"] == 4
    assert out["crutch_count"] == 4
    assert out["crutch_percentage"] == 100.0
    assert out["by_opener"]["so"] == 1
    assert out["by_opener"]["well"] == 1
    assert out["by_opener"]["i mean"] == 1
    assert out["by_opener"]["and"] == 1
    assert out["status"] == "watch"


def test_sentence_openers_phrase_wins_over_single():
    # "you know" is a phrase crutch; the first single token would also match
    # 'you' if it were a single crutch (it isn't, but make sure phrase fires).
    text = "You know this matters. Other sentence ends here."
    words, dur = _make_words(text, wpm=150.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_sentence_openers(tx, _cfg()["sentence_openers"])
    assert out["by_opener"].get("you know") == 1


# ---------- Sentence shape and lexical variety ----------

def test_sentence_shape_avg_length_and_variety():
    text = "One two three. Four five six seven eight."  # 3 + 5 = avg 4
    words, dur = _make_words(text, wpm=150.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_sentence_shape(tx, _cfg()["sentence_length"])
    assert out["sentence_count"] == 2
    assert out["avg_sentence_length_words"] == 4.0
    assert out["longest_sentence_words"] == 5
    # All 8 tokens are unique, so variety = 1.0
    assert out["lexical_variety"] == 1.0


def test_sentence_shape_uses_provided_sentence_segmentation():
    sents = [
        Sentence(text="Hello world here.", start=0.0, end=1.0),
        Sentence(text="Goodbye.", start=1.0, end=1.5),
    ]
    tx = TranscriptData(
        words=[Word("hello", 0, 0.3), Word("world", 0.3, 0.6),
               Word("here", 0.6, 0.9), Word("goodbye", 0.9, 1.5)],
        text="Hello world here. Goodbye.",
        duration_seconds=1.5,
        sentences=sents,
    )
    out = compute_sentence_shape(tx, _cfg()["sentence_length"])
    assert out["sentence_count"] == 2
    assert out["avg_sentence_length_words"] == 2.0


# ---------- Prosody-derived metrics ----------

def test_pitch_not_measured_when_prosody_absent():
    out = compute_pitch(prosody=None, cfg=_cfg()["prosody"])
    assert out["status"] == "not_measured"
    assert out["mean_hz"] is None
    assert out["std_semitones"] is None


def test_pitch_monotone_flagged_below_threshold():
    prosody = ProsodyData(
        mean_pitch_hz=120.0,
        pitch_range_hz=20.0,
        pitch_std_semitones=1.2,  # below 2.0 threshold
        monotone_passages=[MonotonePassage(start=10.0, end=22.0, pitch_std_semitones=1.0)],
        pauses=[],
        speaking_time_seconds=60.0,
        dynamic_range_db=8.0,
    )
    out = compute_pitch(prosody, cfg=_cfg()["prosody"])
    assert out["status"] == "watch"
    assert out["is_monotone_overall"] is True
    assert len(out["monotone_passages"]) == 1


def test_pitch_not_measured_when_pitch_tracking_failed():
    prosody = ProsodyData(
        mean_pitch_hz=0.0,
        pitch_range_hz=0.0,
        pitch_std_semitones=0.0,
        monotone_passages=[],
        pauses=[],
        speaking_time_seconds=60.0,
        dynamic_range_db=8.0,
        pitch_measured=False,
    )
    out = compute_pitch(prosody, cfg=_cfg()["prosody"])
    assert out["status"] == "not_measured"


# ---------- Top-level assembly and sanity warnings ----------

def test_compute_all_metrics_shape():
    text = "Um so I just sort of think this is fine."
    words, dur = _make_words(text, wpm=150.0)
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_all_metrics(tx, prosody=None, config=_cfg())
    assert set(out.keys()) >= {
        "pace", "fillers", "weak_words", "sentence_openers",
        "sentence_shape", "pitch", "pauses", "energy", "warnings",
    }
    assert out["pitch"]["status"] == "not_measured"
    assert out["pauses"]["status"] == "not_measured"
    assert out["energy"]["status"] == "not_measured"


def test_sanity_warning_when_zero_fillers_on_long_clip():
    # 90 seconds of clean speech with no fillers.
    text = " ".join(["word"] * 200)
    words, dur = _make_words(text, wpm=133.0)  # ~90 seconds
    tx = TranscriptData(words=words, text=text, duration_seconds=dur)
    out = compute_all_metrics(tx, prosody=None, config=_cfg())
    assert any("disfluencies" in w.lower() for w in out["warnings"])


def test_sanity_warning_when_pace_implausibly_high():
    # Many words across a tiny duration: should trip the implausible pace check.
    words = [Word(text=f"w{i}", start=i * 0.1, end=i * 0.1 + 0.05) for i in range(50)]
    tx = TranscriptData(
        words=words,
        text=" ".join(w.text for w in words),
        duration_seconds=5.0,  # 50 words in 5s = 600 wpm
    )
    out = compute_all_metrics(tx, prosody=None, config=_cfg())
    assert any("wpm" in w for w in out["warnings"])

"""
AssemblyAI transcription wrapper for Reput8ion Delivery Lab.

Returns a TranscriptData object with word-level timing, optional sentence
segmentation, and audio duration from the API response (not guessed).

Persists the raw AssemblyAI JSON for debugging.
"""

import json
from collections import Counter
from pathlib import Path

import assemblyai as aai

from src.metrics import TranscriptData, Word, Sentence


def transcribe(audio_path: str, api_key: str) -> TranscriptData:
    """
    Transcribe audio via AssemblyAI with disfluencies=True and speaker_labels=True.

    Returns a TranscriptData with:
    - words: list of Word objects with start/end in seconds and speaker label
    - text: full transcript text
    - duration_seconds: from word timings (most reliable source)
    - sentences: list of Sentence objects if available, else None
    - speaker_summary: {counts: {speaker: word_count}, interviewee: speaker_id,
                        speaker_count: n} — interviewee is the speaker with most words

    Persists raw response to <audio_path>.assemblyai.json for debugging.
    """
    aai.settings.api_key = api_key

    config = aai.TranscriptionConfig(disfluencies=True, speaker_labels=True)
    transcriber = aai.Transcriber(config=config)

    transcript = transcriber.transcribe(audio_path)

    # Extract words with timing (convert ms to seconds) and speaker label
    words = []
    if transcript.words:
        for w in transcript.words:
            words.append(Word(
                text=w.text,
                start=w.start / 1000.0,
                end=w.end / 1000.0,
                confidence=w.confidence if hasattr(w, 'confidence') else 1.0,
                speaker=getattr(w, 'speaker', None),
            ))
    
    # Extract sentences if available
    sentences = None
    try:
        sent_list = transcript.get_sentences()
        if sent_list:
            sentences = [
                Sentence(
                    text=s.text,
                    start=s.start / 1000.0,
                    end=s.end / 1000.0,
                )
                for s in sent_list
            ]
    except (AttributeError, TypeError):
        # Sentences not available
        pass
    
    # Full transcript text
    text = transcript.text or ""

    # Audio duration: use word timings if available, fall back to API response
    if words:
        duration_seconds = max(w.end for w in words)
    else:
        duration_seconds = transcript.audio_duration / 1000.0 if transcript.audio_duration else 0.0

    # Speaker summary: count words per speaker, identify interviewee (most words)
    speaker_counts = Counter(w.speaker for w in words if w.speaker)
    if speaker_counts:
        interviewee = max(speaker_counts, key=speaker_counts.get)
        speaker_summary = {
            "counts": dict(speaker_counts),
            "interviewee": interviewee,
            "speaker_count": len(speaker_counts),
        }
    else:
        speaker_summary = None

    # Persist raw response for debugging
    _save_raw_response(audio_path, transcript)

    return TranscriptData(
        words=words,
        text=text,
        duration_seconds=duration_seconds,
        sentences=sentences,
        speaker_summary=speaker_summary,
    )


def _save_raw_response(audio_path: str, transcript) -> None:
    """Save the raw AssemblyAI response JSON next to the audio file."""
    base_path = Path(audio_path)
    output_path = base_path.parent / f"{base_path.stem}.assemblyai.json"

    # Convert transcript object to dict for serialisation, safely handling missing attributes
    response_dict = {
        "id": getattr(transcript, "id", None),
        "text": getattr(transcript, "text", ""),
        "audio_duration": getattr(transcript, "audio_duration", 0),
        "confidence": getattr(transcript, "confidence", None),
    }

    # Add optional attributes if they exist
    if hasattr(transcript, "language_code"):
        response_dict["language_code"] = transcript.language_code
    if hasattr(transcript, "speech_model"):
        response_dict["speech_model"] = transcript.speech_model
    if hasattr(transcript, "language_detection"):
        response_dict["language_detection"] = transcript.language_detection

    # Words
    response_dict["words"] = [
        {
            "text": w.text,
            "start": w.start,
            "end": w.end,
            "confidence": w.confidence if hasattr(w, "confidence") else None,
        }
        for w in (transcript.words or [])
    ]

    # Sentences
    try:
        sent_list = transcript.get_sentences()
        response_dict["sentences"] = [
            {
                "text": s.text,
                "start": s.start,
                "end": s.end,
            }
            for s in (sent_list or [])
        ]
    except (AttributeError, TypeError):
        response_dict["sentences"] = []

    with open(output_path, "w") as f:
        json.dump(response_dict, f, indent=2)

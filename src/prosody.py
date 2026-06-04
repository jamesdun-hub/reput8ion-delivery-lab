"""
Prosody analysis for Reput8ion Delivery Lab.

Extracts pitch (via parselmouth), pauses (via librosa), and energy metrics.
Returns a ProsodyData object with all measured values and flags for missing data.
"""

import subprocess
import tempfile
import warnings
from pathlib import Path

import librosa
import numpy as np
import parselmouth

from src.metrics import ProsodyData, PauseEvent, MonotonePassage

_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def _extract_audio_if_video(audio_path: str) -> tuple[str, bool]:
    """If the file is a video container, extract audio to a temp MP3 using bundled FFmpeg.
    Returns (path_to_use, is_temp). Caller must delete the temp file if is_temp is True."""
    if Path(audio_path).suffix.lower() not in _VIDEO_EXTENSIONS:
        return audio_path, False
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError(
            "imageio-ffmpeg is required to process video files. "
            "Run: pip install imageio-ffmpeg"
        )
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    result = subprocess.run(
        [ffmpeg, "-y", "-i", audio_path, "-vn",
         "-acodec", "libmp3lame", "-q:a", "2", tmp.name],
        capture_output=True,
    )
    if result.returncode != 0:
        Path(tmp.name).unlink(missing_ok=True)
        raise RuntimeError(f"Audio extraction failed:\n{result.stderr.decode()}")
    return tmp.name, True


def analyse(audio_path: str, sentence_boundaries_s: list[float] | None, cfg: dict) -> ProsodyData:
    """
    Analyse prosody of an audio file.

    Args:
        audio_path: Path to audio file (MP3, WAV, M4A, or video container such as MP4)
        sentence_boundaries_s: List of sentence-end timestamps (seconds) for pause classification
        cfg: Prosody configuration dict from config.yaml

    Returns:
        ProsodyData with pitch, pauses, speaking time, and energy metrics.
        Sets pitch_measured and energy_measured flags if extraction failed.
    """
    audio_path, is_temp = _extract_audio_if_video(audio_path)
    try:
        audio, sr = librosa.load(audio_path, sr=None, mono=True)
    finally:
        if is_temp:
            Path(audio_path).unlink(missing_ok=True)
    duration_s = librosa.get_duration(y=audio, sr=sr)

    pitch_data = _extract_pitch(audio, sr, cfg)
    pauses = _extract_pauses(audio, sr, sentence_boundaries_s, cfg)
    speaking_time = _compute_speaking_time(duration_s, pauses)
    energy_data = _extract_energy(audio, sr, sentence_boundaries_s, cfg)
    
    return ProsodyData(
        mean_pitch_hz=pitch_data["mean_hz"],
        pitch_range_hz=pitch_data["range_hz"],
        pitch_std_semitones=pitch_data["std_semitones"],
        monotone_passages=pitch_data["monotone_passages"],
        pauses=pauses,
        speaking_time_seconds=speaking_time,
        dynamic_range_db=energy_data["dynamic_range_db"],
        trailing_off_events=energy_data["trailing_off_events"],
        pitch_windows=pitch_data["pitch_windows"],
        pitch_measured=pitch_data["measured"],
        energy_measured=energy_data["measured"],
    )


def _extract_pitch(audio: np.ndarray, sr: int, cfg: dict) -> dict:
    """
    Extract pitch using parselmouth (Praat).

    Accepts a numpy audio array so parselmouth never touches the file directly —
    this avoids MP3 compatibility issues that silently return no pitch data.

    Returns dict with mean_hz, range_hz, std_semitones, monotone_passages, and measured flag.
    """
    _empty = {
        "mean_hz": 0.0,
        "range_hz": 0.0,
        "std_semitones": 0.0,
        "monotone_passages": [],
        "pitch_windows": [],
        "measured": False,
    }
    try:
        # Build Sound from the already-decoded numpy array, bypassing file format issues
        sound = parselmouth.Sound(audio.astype(np.float64), sampling_frequency=float(sr))
        pitch = sound.to_pitch()

        # Extract voiced f0 values — prefer the array interface (parselmouth >= 0.4)
        f0_all = None
        try:
            f0_all = pitch.selected_array['frequency']
            f0_arr = f0_all[~np.isnan(f0_all) & (f0_all > 0)]
        except (AttributeError, KeyError):
            # Frame-by-frame fallback for older parselmouth builds
            f0_list = []
            for i in range(pitch.number_of_frames):
                f0 = pitch.get_value_at_time(pitch.get_time_from_frame_number(i + 1))
                if f0 is not None and not np.isnan(f0) and f0 > 0:
                    f0_list.append(f0)
            f0_arr = np.array(f0_list)

        if len(f0_arr) == 0:
            return _empty

        mean_hz = float(np.mean(f0_arr))
        range_hz = float(np.max(f0_arr) - np.min(f0_arr))
        log_f0 = np.log2(f0_arr)
        std_semitones = float(np.std(log_f0) * 12)  # octaves -> semitones

        monotone_passages = _find_monotone_passages(
            pitch, cfg["monotone_passage_min_duration_seconds"],
            cfg["monotone_pitch_std_semitones_threshold"]
        )

        pitch_windows = _compute_pitch_windows(pitch, f0_all, window_seconds=30.0)

        return {
            "mean_hz": mean_hz,
            "range_hz": range_hz,
            "std_semitones": std_semitones,
            "monotone_passages": monotone_passages,
            "pitch_windows": pitch_windows,
            "measured": True,
        }
    except Exception as exc:
        warnings.warn(f"Pitch extraction failed: {exc}")
        return _empty


def _compute_pitch_windows(pitch, f0_all: np.ndarray | None, window_seconds: float = 30.0) -> list[dict]:
    """Mean voiced pitch per fixed time window, used for the trend chart.

    Requires f0_all (the full frequency array from selected_array). Returns []
    if that array was unavailable (older parselmouth fallback).
    """
    if f0_all is None or len(f0_all) == 0:
        return []

    duration = pitch.xmax
    frame_times = np.linspace(pitch.xmin, pitch.xmax, len(f0_all))

    windows: list[dict] = []
    t = 0.0
    while t < duration:
        t_end = min(t + window_seconds, duration)
        mask = (frame_times >= t) & (frame_times < t_end)
        segment = f0_all[mask]
        voiced = segment[~np.isnan(segment) & (segment > 0)]
        mean_hz = float(np.mean(voiced)) if len(voiced) > 0 else None
        windows.append({
            "start_seconds": round(t, 1),
            "end_seconds": round(t_end, 1),
            "mean_hz": round(mean_hz, 1) if mean_hz is not None else None,
        })
        t += window_seconds
    return windows


def _find_monotone_passages(pitch, min_duration: float, threshold: float) -> list[MonotonePassage]:
    """Find passages where pitch variation is below threshold.

    Uses selected_array + linspace frame times to avoid number_of_frames/
    get_time_from_frame_number API differences across parselmouth versions.
    """
    try:
        f0_all = pitch.selected_array['frequency']
    except (AttributeError, KeyError):
        return []

    frame_times = np.linspace(pitch.xmin, pitch.xmax, len(f0_all))
    duration = pitch.xmax
    step = 0.1

    passages = []
    i = 0.0
    while i + min_duration <= duration:
        t_start = i
        t_end = i + min_duration
        mask = (frame_times >= t_start) & (frame_times <= t_end)
        voiced = f0_all[mask]
        voiced = voiced[~np.isnan(voiced) & (voiced > 0)]
        if len(voiced) > 0:
            std_st = float(np.std(np.log2(voiced)) * 12)
            if std_st < threshold:
                passages.append(MonotonePassage(start=t_start, end=t_end, pitch_std_semitones=std_st))
        i += step
    
    # Merge overlapping passages
    if not passages:
        return []
    
    merged = []
    current = passages[0]
    for p in passages[1:]:
        if p.start <= current.end + 0.1:  # Allow small overlap
            current = MonotonePassage(
                start=current.start,
                end=max(current.end, p.end),
                pitch_std_semitones=min(current.pitch_std_semitones, p.pitch_std_semitones),
            )
        else:
            merged.append(current)
            current = p
    merged.append(current)
    
    return merged


def _extract_pauses(audio: np.ndarray, sr: int, sentence_boundaries_s: list[float] | None, cfg: dict) -> list[PauseEvent]:
    """
    Extract silence regions using librosa.effects.split.

    librosa.effects.split returns NON-SILENT (speech) intervals as sample-index pairs.
    Pauses are the GAPS between those intervals, not the intervals themselves.
    Time conversion: sample_index / sr (not librosa.frames_to_time, which expects hop frames).

    Classifies pauses as at_sentence_boundary if midpoint is within ~0.4s of a sentence end.
    """
    min_pause_duration = cfg["pause_min_duration_seconds"]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Returns sample-index pairs for non-silent (speech) regions
        speech_intervals = librosa.effects.split(audio, top_db=30)

    if len(speech_intervals) == 0:
        return []

    total_samples = len(audio)

    # Build silence regions as gaps before, between, and after speech intervals
    silence_regions: list[tuple[int, int]] = []
    if speech_intervals[0][0] > 0:
        silence_regions.append((0, int(speech_intervals[0][0])))
    for i in range(len(speech_intervals) - 1):
        silence_regions.append((int(speech_intervals[i][1]), int(speech_intervals[i + 1][0])))
    if speech_intervals[-1][1] < total_samples:
        silence_regions.append((int(speech_intervals[-1][1]), total_samples))

    pauses = []
    for gap_start, gap_end in silence_regions:
        t_start = gap_start / sr   # sample index -> seconds
        t_end = gap_end / sr
        duration = t_end - t_start

        if duration < min_pause_duration:
            continue

        midpoint = (t_start + t_end) / 2
        at_boundary = False
        if sentence_boundaries_s:
            for boundary in sentence_boundaries_s:
                if abs(midpoint - boundary) < 0.4:
                    at_boundary = True
                    break

        pauses.append(PauseEvent(
            start=t_start,
            end=t_end,
            duration=duration,
            at_sentence_boundary=at_boundary,
        ))

    return pauses


def _compute_speaking_time(duration_s: float, pauses: list[PauseEvent]) -> float:
    """Speaking time = total duration minus pause durations."""
    pause_time = sum(p.duration for p in pauses)
    return max(duration_s - pause_time, 0.0)


def _extract_energy(audio: np.ndarray, sr: int, sentence_boundaries_s: list[float] | None, cfg: dict) -> dict:
    """
    Extract energy metrics: RMS, dB levels, dynamic range, trailing-off events.
    """
    try:
        # Compute RMS per frame
        S = librosa.feature.melspectrogram(y=audio, sr=sr)
        energy = librosa.power_to_db(S, ref=np.max)
        
        # Use librosa's built-in RMS
        rms = librosa.feature.rms(y=audio)[0]
        rms_db = librosa.power_to_db(np.mean(rms**2), ref=1.0)
        
        if len(rms) == 0:
            return {
                "dynamic_range_db": 0.0,
                "trailing_off_events": [],
                "measured": False,
            }
        
        # Dynamic range: 90th percentile minus 10th percentile
        rms_db_frames = librosa.power_to_db(rms**2, ref=np.max(rms)**2)
        p90 = np.percentile(rms_db_frames, 90)
        p10 = np.percentile(rms_db_frames, 10)
        dynamic_range = float(p90 - p10)
        
        # Trailing-off: compare sentence-end energy to sentence median
        trailing_off_events = []
        if sentence_boundaries_s:
            frame_times = librosa.frames_to_time(np.arange(len(rms_db_frames)), sr=sr)
            trailing_threshold = cfg["trailing_off_db_drop"]
            
            for boundary_s in sentence_boundaries_s:
                # Last 0.5s of sentence before boundary
                window_start = boundary_s - 0.5
                window_end = boundary_s
                
                # Find frames in this window
                window_mask = (frame_times >= window_start) & (frame_times <= window_end)
                window_frames = rms_db_frames[window_mask]
                
                if len(window_frames) > 0:
                    sentence_median = np.median(window_frames)
                    # Check last few frames for drop
                    if len(window_frames) > 2:
                        final_energy = np.mean(window_frames[-3:])
                        if final_energy < sentence_median - trailing_threshold:
                            trailing_off_events.append(float(boundary_s))
        
        return {
            "dynamic_range_db": dynamic_range,
            "trailing_off_events": trailing_off_events,
            "measured": True,
        }
    except Exception:
        return {
            "dynamic_range_db": 0.0,
            "trailing_off_events": [],
            "measured": False,
        }

"""
Coach dashboard generator for Reput8ion Delivery Lab.

Layout (top to bottom — optimised for glancing, no mouse required):

1.  Header
2.  Speaker split note
3.  DELIVERY ANALYTICS — 4 metric cards with full detail sub-text
4.  COMBINED TIMELINE — pace + pitch + fillers on one chart
5.  STORYBOARD — coloured tiles below the chart (time / WPM / snippet),
    visible without hovering so James can scan while talking
6.  PILLAR ASSESSMENT — 3 full columns (Delivery | Story | Control)
    with narrative paragraphs from the AI
7.  Rocks + Strengths side by side
8.  Tone section
9.  Coaching moments
10. Story & Control detail — signals + full narrative
11. Language & Conciseness — weak words, openers, conciseness, repetition
12. Pause highlights
"""

import html
import json
import webbrowser
from pathlib import Path


def generate_dashboard(
    metrics: dict,
    prosody_data,
    transcript_data,
    context: dict,
    config: dict,
    out_path: str,
    narrative: dict | None = None,
    auto_open: bool = True,
) -> str:
    """Generate the HTML dashboard and return its file path."""
    speaker_info = transcript_data.speaker_summary or {}
    filler_set = {t.lower() for t in config.get("filler_words", {}).get("tokens", [])}
    pace_cfg = config.get("pace", {})
    chart_min_wpm = pace_cfg.get("chart_min_wpm", 100)

    pace_windows = metrics.get("pace", {}).get("windows", [])
    pitch_windows = list(getattr(prosody_data, "pitch_windows", []) or [])
    filler_by_window = _count_fillers_by_window(pace_windows, transcript_data.words, filler_set)
    pace_snippets = _pace_window_snippets(pace_windows, transcript_data.words)
    pitch_measured = getattr(prosody_data, "pitch_measured", False) if prosody_data else False

    html_str = _render_html(
        context=context,
        metrics=metrics,
        pace_windows=pace_windows,
        pace_snippets=pace_snippets,
        pitch_windows=pitch_windows,
        filler_by_window=filler_by_window,
        speaker_info=speaker_info,
        pace_cfg=pace_cfg,
        chart_min_wpm=chart_min_wpm,
        pitch_measured=pitch_measured,
        narrative=narrative or {},
        config=config,
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_str, encoding="utf-8")
    if auto_open:
        webbrowser.open(out.resolve().as_uri())
    return str(out)


# ---------- Data helpers ----------

def _count_fillers_by_window(pace_windows: list[dict], words, filler_set: set) -> list[int]:
    """Filler count aligned to each pace window, for the combined chart."""
    if not words or not pace_windows:
        return [0] * len(pace_windows)
    counts = []
    for w in pace_windows:
        t0, t1 = w["start_seconds"], w["end_seconds"]
        c = sum(1 for wd in words if t0 <= wd.start < t1 and wd.text.lower().strip(".,!?") in filler_set)
        counts.append(c)
    return counts


def _pace_window_snippets(pace_windows: list[dict], words) -> list[str]:
    """First 20 words spoken in each pace window, for the storyboard tiles."""
    if not words:
        return [""] * len(pace_windows)
    snippets = []
    for w in pace_windows:
        t0, t1 = w["start_seconds"], w["end_seconds"]
        window_words = [wd.text for wd in words if t0 <= wd.start < t1]
        snippet = " ".join(window_words[:20])
        if len(window_words) > 20:
            snippet += "…"
        snippets.append(snippet)
    return snippets


# ---------- Formatting helpers ----------

def _fmt_time(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


_STATUS_CLASS = {
    "green": "green", "ideal": "green",
    "watch": "watch", "amber": "watch",
    "hard_fast": "red", "too_slow": "red", "edge_fast": "watch",
    "not_measured": "not_measured", "red": "red",
}
_STATUS_LABEL = {
    "green": "Good", "ideal": "Ideal", "watch": "Watch", "amber": "Amber",
    "hard_fast": "Too fast", "too_slow": "Too slow", "edge_fast": "Edge fast",
    "not_measured": "Not measured", "red": "Red flag",
}

def _css(s: str) -> str:
    return _STATUS_CLASS.get(s, "neutral")

def _slabel(s: str) -> str:
    return _STATUS_LABEL.get(s, s.replace("_", " ").title())


def _tile_colour(wpm: float, pace_cfg: dict) -> str:
    """CSS class for a storyboard tile based on WPM."""
    if wpm < pace_cfg.get("chart_min_wpm", 100):
        return "tile-gray"
    if wpm > pace_cfg.get("fast_hard", 185):
        return "tile-red"
    if wpm > pace_cfg.get("fast_warning", 170):
        return "tile-amber"
    if wpm < pace_cfg.get("slow_warning", 120):
        return "tile-amber"
    if pace_cfg.get("ideal_min", 140) <= wpm <= pace_cfg.get("ideal_max", 170):
        return "tile-green"
    return "tile-amber"


# ---------- HTML section builders ----------

def _speaker_note(speaker_info: dict) -> str:
    if not speaker_info or speaker_info.get("speaker_count", 1) < 2:
        return ""
    counts = speaker_info.get("counts", {})
    interviewee = speaker_info.get("interviewee", "")
    total = sum(counts.values()) or 1
    parts = []
    for spk, cnt in sorted(counts.items()):
        role = "interviewee (analysed)" if spk == interviewee else "interviewer (excluded)"
        parts.append(f"Speaker {html.escape(spk)}: {cnt} words ({cnt/total*100:.0f}%) — {role}")
    return '<div class="speaker-note">' + " &nbsp;|&nbsp; ".join(parts) + "</div>"


def _delivery_cards(metrics: dict, config: dict) -> str:
    pace = metrics.get("pace", {})
    fillers = metrics.get("fillers", {})
    pitch = metrics.get("pitch", {})
    pauses = metrics.get("pauses", {})
    ideal_min = config.get("pace", {}).get("ideal_min", 140)
    ideal_max = config.get("pace", {}).get("ideal_max", 170)

    # Pace card
    net_wpm = pace.get("net_wpm", "—")
    gross_wpm = pace.get("gross_wpm", "—")
    speak_s = pace.get("speaking_time_seconds", 0)
    speak_min = f"{speak_s/60:.1f}" if speak_s else "—"
    pace_detail = f"Gross: {gross_wpm} wpm &nbsp;|&nbsp; Speaking time: {speak_min} min"
    # The net average can sit "ideal" while individual windows run hot. If any
    # window breaches the upper ceiling, surface it on the card so the card
    # does not contradict the storyboard. Status downgrades to watch.
    pace_status = pace.get("status", "neutral")
    windows = pace.get("windows", []) or []
    window_paces = [w.get("wpm", 0) for w in windows if w.get("wpm")]
    peak = max(window_paces) if window_paces else 0
    if peak > ideal_max and pace_status in ("green", "ideal"):
        pace_detail += f"<br>Peaks at {peak:.0f} wpm — runs above the {ideal_max} ceiling"
        pace_status = "watch"
    c_pace = _card(
        "Pace", f"{net_wpm} wpm",
        f"target {ideal_min}–{ideal_max} wpm",
        pace_detail,
        pace_status,
    )

    # Filler card
    by_token = fillers.get("by_token", {})
    filler_parts = [f"{n} {tok}" for tok, n in list(by_token.items())[:4]]
    filler_breakdown = " &nbsp;|&nbsp; ".join(filler_parts) if filler_parts else "none detected"
    filler_total = fillers.get("total", 0)
    filler_pct = fillers.get("per_100_words", "—")
    filler_green_target = config.get("filler_words", {}).get("green_per_100_words", 1.5)
    c_filler = _card(
        "Fillers", f"{filler_pct}%",
        f"{filler_total} total &nbsp;|&nbsp; target &lt;{filler_green_target}%",
        filler_breakdown,
        fillers.get("status", "neutral"),
    )

    # Melody / pitch card
    if pitch.get("status") == "not_measured":
        c_pitch = _card("Melody", "—", "not measured", "Re-run to capture pitch data", "not_measured")
    else:
        mean_hz = pitch.get("mean_hz", "—")
        std_st = pitch.get("std_semitones", "—")
        mono = pitch.get("monotone_passages", [])
        mono_str = f"{len(mono)} monotone passage{'s' if len(mono) != 1 else ''}" if mono else "no monotone passages"
        c_pitch = _card(
            "Melody", f"{mean_hz} Hz",
            f"{std_st} st variation",
            mono_str,
            pitch.get("status", "neutral"),
        )

    # Pauses card
    if pauses.get("status") == "not_measured":
        c_pause = _card("Pauses", "—", "not measured", "", "not_measured")
    else:
        count = pauses.get("count", 0)
        avg_s = pauses.get("avg_seconds", 0)
        boundary = pauses.get("at_sentence_boundary", 0)
        mid = pauses.get("mid_sentence", 0)
        pause_detail = f"Avg {avg_s:.1f}s &nbsp;|&nbsp; {boundary} at sentence end, {mid} mid-sentence"
        c_pause = _card(
            "Pauses", str(count),
            f"{pauses.get('total_silent_seconds',0):.0f}s total silence",
            pause_detail,
            pauses.get("status", "green"),
        )

    return (
        '<h2 class="section-heading">Delivery analytics</h2>'
        f'<div class="cards four-col">{c_pace}{c_filler}{c_pitch}{c_pause}</div>'
    )


def _card(label, value, sub, detail, status):
    cls = _css(status)
    return (
        f'<div class="card {cls}">'
        f'<div class="card-label">{label}</div>'
        f'<div class="card-value">{html.escape(str(value))}</div>'
        f'<div class="card-sub">{sub}</div>'
        f'<div class="card-detail">{detail}</div>'
        f'<div class="card-status">{_slabel(status)}</div>'
        f'</div>'
    )


def _storyboard(pace_windows, pace_snippets, pace_cfg, max_tiles: int = 0) -> str:
    """Coloured tiles, one per spoken window across the FULL session, visible
    without hovering. The storyboard must cover the whole session — truncating
    it hides exactly the passages (often the close) where pace runs hot.
    max_tiles=0 means no cap; pass a positive value only to sub-sample very
    long sessions."""
    if not pace_windows:
        return ""
    chart_min = pace_cfg.get("chart_min_wpm", 100)

    # Collect eligible (above chart_min) with their original index
    eligible = [
        (i, w, pace_snippets[i] if i < len(pace_snippets) else "")
        for i, w in enumerate(pace_windows)
        if w["wpm"] >= chart_min
    ]
    # Only sub-sample if an explicit positive cap is set and we exceed it
    if max_tiles and len(eligible) > max_tiles:
        stride = max(1, len(eligible) // max_tiles)
        eligible = eligible[::stride][:max_tiles]

    tiles = []
    for _i, w, snippet in eligible:
        wpm = w["wpm"]
        t = _fmt_time(w["start_seconds"])
        colour = _tile_colour(wpm, pace_cfg)
        tiles.append(
            f'<div class="stile {colour}">'
            f'<div class="stile-time">{html.escape(t)}</div>'
            f'<div class="stile-wpm">{wpm:.0f}</div>'
            f'<div class="stile-snippet">{html.escape(snippet)}</div>'
            f'</div>'
        )
    if not tiles:
        return ""
    legend = (
        '<div class="storyboard-legend">'
        '<span class="leg tile-green">Ideal pace</span>'
        '<span class="leg tile-amber">Watch</span>'
        '<span class="leg tile-red">Too fast</span>'
        '</div>'
    )
    return (
        '<div class="storyboard-wrap">'
        + legend
        + '<div class="storyboard">' + "".join(tiles) + "</div>"
        + "</div>"
    )


def _pillar_columns(narrative: dict, metrics: dict) -> str:
    """Three columns — Delivery, Story, Control — with verdict headline and
    scannable bullet points so James can glance without reading a paragraph."""
    verdicts = narrative.get("pillar_verdicts", {})
    if not verdicts:
        return ""

    def _bullets(text: str) -> str:
        """Split a narrative paragraph into bullet points (max 4)."""
        if not text:
            return ""
        sentences = [
            s.strip().rstrip(".")
            for s in text.replace("\n", " ").split(". ")
            if s.strip()
        ]
        items = "".join(
            f'<li class="pillar-bullet">{html.escape(s)}.</li>'
            for s in sentences[:4]
        )
        return f'<ul class="pillar-bullet-list">{items}</ul>'

    def col(title, key, extra_html=""):
        v = verdicts.get(key, {})
        status = v.get("status", "watch")
        verdict = v.get("verdict", "")
        return (
            f'<div class="pillar-col {_css(status)}-border">'
            f'<div class="pillar-header">'
            f'<span class="pillar-title">{title}</span>'
            f'<span class="pillar-badge {_css(status)}">{_slabel(status)}</span>'
            f'</div>'
            f'<div class="pillar-verdict">{html.escape(verdict)}</div>'
            + extra_html +
            f'</div>'
        )

    cs = metrics.get("control_signals", {})
    control_chips = ""
    if cs:
        b = cs.get("bridge_count", 0)
        f_ = cs.get("flag_count", 0)
        h = cs.get("hook_count", 0)
        control_chips = (
            f'<div class="pillar-signals">'
            f'<span class="sig-chip sig-bridge">{b} bridge{"s" if b!=1 else ""}</span>'
            f'<span class="sig-chip sig-flag">{f_} flag{"s" if f_!=1 else ""}</span>'
            f'<span class="sig-chip sig-hook">{h} hook{"s" if h!=1 else ""}</span>'
            f'</div>'
        )

    return (
        '<h2 class="section-heading">Pillar assessment</h2>'
        '<div class="pillar-grid">'
        + col("Delivery", "delivery", _bullets(narrative.get("pace_and_tone_narrative", "")))
        + col("Story", "story", _bullets(narrative.get("control_and_structure_narrative", "")))
        + col("Control", "control", control_chips + _bullets(narrative.get("filler_and_weak_words_narrative", "")))
        + '</div>'
    )


def _rocks_and_strengths(narrative: dict) -> str:
    rocks = narrative.get("inferred_rocks", [])
    strengths = narrative.get("strengths", [])
    rocks_offline = rocks and "[OFFLINE]" in rocks[0]
    str_offline = strengths and "[OFFLINE]" in strengths[0]

    rock_html = ""
    if rocks and not rocks_offline:
        # rock_strength is an optional list aligned to inferred_rocks, each
        # {strength: strong|weak, note: ...}. Falls back to plain list if absent.
        strengths_meta = narrative.get("rock_strength", [])
        delta_note = narrative.get("rock_delta_note", "")
        lines = ""
        for i, r in enumerate(rocks):
            meta = strengths_meta[i] if i < len(strengths_meta) else {}
            strength = (meta.get("strength") or "").lower()
            note = meta.get("note", "")
            cls = {"strong": "landed", "weak": "weak", "missed": "missed"}.get(strength, "")
            badge = {"strong": "Strong", "weak": "Weak", "missed": "Missed"}.get(strength, "")
            badge_cls = {"strong": "rs-landed", "weak": "rs-weak", "missed": "rs-missed"}.get(strength, "")
            note_html = f' — {html.escape(note)}' if note else ""
            badge_html = f'<span class="rock-state {badge_cls}">{badge}</span>' if badge else ""
            lines += (
                f'<div class="rock-line {cls}"><span><strong>{html.escape(r)}</strong>'
                f'{note_html}</span>{badge_html}</div>'
            )
        delta_html = (
            f'<div class="delta-banner"><strong>The coaching point:</strong> '
            f'{html.escape(delta_note)}</div>' if delta_note else ""
        )
        rock_html = (
            '<div class="full-box">'
            '<h3>Key messages — what actually landed</h3>'
            '<p class="house-note" style="margin-bottom:12px">The messages a listener '
            'would take away, ranked by how clearly they registered. This is perception, '
            'not stated intent — the coaching question is whether the right messages '
            'landed, and landed cleanly.</p>'
            f'{lines}{delta_html}'
            '</div>'
        )

    str_html = ""
    if strengths and not str_offline:
        items = "".join(f'<li class="strength-item">{html.escape(s)}</li>' for s in strengths)
        str_html = (
            '<div class="full-box strength-box">'
            '<h3>Open the debrief with these strengths</h3>'
            f'<ul class="strength-list">{items}</ul>'
            '</div>'
        )

    if not rock_html and not str_html:
        return ""
    return rock_html + str_html


def _tone_html(narrative: dict) -> str:
    tone = narrative.get("tone_assessment", {})
    if not tone or "[OFFLINE]" in tone.get("narrative", ""):
        return ""
    descriptors = [d for d in tone.get("descriptors", []) if d != "[offline]"]
    text = tone.get("narrative", "")
    chips = "".join(f'<span class="tone-chip">{html.escape(d)}</span>' for d in descriptors)
    return (
        '<div class="full-box tone-box">'
        '<h3>Tone</h3>'
        f'<div class="tone-chips">{chips}</div>'
        f'<p class="box-narrative">{html.escape(text)}</p>'
        '</div>'
    )


def _coaching_moments_html(narrative: dict) -> str:
    moments = narrative.get("coaching_moments", [])
    offline = moments and "[OFFLINE]" in moments[0].get("observation", "")
    if not moments or offline:
        return (
            '<div class="full-box">'
            '<h3>Coaching moments — what to raise</h3>'
            '<p class="muted">Requires OPENAI_API_KEY.</p>'
            '</div>'
        )
    rows = []
    for m in moments:
        t = m.get("timestamp_approx", "—")
        obs = m.get("observation", "")
        badge = "strength-badge" if m.get("type") == "strength" else "watch-badge"
        badge_text = "Strong" if m.get("type") == "strength" else "Raise"
        rows.append(
            f'<div class="moment-row">'
            f'<span class="moment-time">{html.escape(t)}</span>'
            f'<span class="moment-text">{html.escape(obs)}</span>'
            f'<span class="moment-badge {badge}">{badge_text}</span>'
            f'</div>'
        )
    return (
        '<div class="full-box">'
        '<h3>Coaching moments — what to raise in the debrief</h3>'
        + "\n".join(rows) +
        '</div>'
    )


def _session_summary_html(narrative: dict, metrics: dict, config: dict = None) -> str:
    """Two-column summary box above the chart.
    Left: overall verdict + AI overview + 3 metric callouts.
    Right: inferred rocks so James can verify alignment at a glance."""
    verdicts = narrative.get("pillar_verdicts", {})
    overview = narrative.get("overview", "")
    overview_offline = not overview or "[OFFLINE]" in overview
    rocks = narrative.get("inferred_rocks", [])
    rocks_offline = rocks and "[OFFLINE]" in rocks[0]

    # Overall verdict derived from pillar statuses. This is a COACH instrument,
    # so the badge names the gap rather than offering a soft "developing well".
    statuses = {k: v.get("status", "watch") for k, v in verdicts.items() if v}
    status_list = list(statuses.values())
    reds = status_list.count("red")
    greens = status_list.count("green")
    watches = status_list.count("watch")
    # Which pillars are weak, in priority order
    weak_pillars = [k for k in ("story", "control", "delivery") if statuses.get(k) in ("watch", "red")]
    weak_label = {"story": "story", "control": "control", "delivery": "delivery"}
    if reds == 0 and greens >= 2:
        overall, overall_cls = "Strong session", "green"
    elif reds >= 2:
        overall, overall_cls = "Needs significant work", "red"
    elif {"story", "control"} <= set(weak_pillars):
        overall, overall_cls = "Message control is the gap", "watch"
    elif weak_pillars:
        overall, overall_cls = f"Work on {weak_label.get(weak_pillars[0], weak_pillars[0])}", "watch"
    else:
        overall, overall_cls = "Developing well", "watch"

    # Auto-callouts from hard metrics
    callouts = []
    pace = metrics.get("pace", {})
    if pace.get("status") == "hard_fast":
        callouts.append(("watch", f"Pace {pace['net_wpm']} wpm — well above the {pace.get('target_band','140–170')} target"))
    elif pace.get("status") == "edge_fast":
        callouts.append(("watch", f"Pace {pace['net_wpm']} wpm — nudging the upper edge of target"))
    elif pace.get("status") == "green":
        callouts.append(("strength", f"Pace {pace['net_wpm']} wpm — in the ideal range"))

    fillers = metrics.get("fillers", {})
    filler_target = (config or {}).get("filler_words", {}).get("green_per_100_words", 4.0)
    if fillers.get("status") == "green":
        callouts.append(("strength", f"Filler control good — {fillers.get('per_100_words','—')}% (target <{filler_target:.0f}%)"))
    else:
        callouts.append(("watch", f"Fillers at {fillers.get('per_100_words','—')}% — above the {filler_target:.0f}% target"))

    openers = metrics.get("sentence_openers", {})
    crutch_pct = openers.get("crutch_percentage", 0)
    top_o = next(iter(openers.get("by_opener", {})), "")
    if crutch_pct >= 30:
        callouts.append(("watch", f"{crutch_pct:.0f}% crutch openers — '{top_o}' dominates"))
    elif crutch_pct < 20:
        callouts.append(("strength", f"Opener discipline good — only {crutch_pct:.0f}% crutch openers"))

    # Control signals: zero flags/hooks is a real gap worth surfacing
    cs = metrics.get("control_signals", {})
    if cs:
        flags = cs.get("flag_count", 0)
        hooks = cs.get("hook_count", 0)
        if flags == 0 and hooks == 0:
            callouts.append(("watch", "0 flags, 0 hooks — no signposting under his own steam"))

    # Lead with the gap: this is a coach instrument, not a reassurance.
    # Order watch callouts before strengths so the work shows first.
    callouts.sort(key=lambda c: 0 if c[0] == "watch" else 1)

    callout_html = "".join(
        f'<div class="summary-callout callout-{"strength" if t=="strength" else "watch"}">'
        f'{"&#10003;" if t=="strength" else "&#9679;"}&nbsp;{html.escape(text)}</div>'
        for t, text in callouts[:3]
    )
    # Coach instrument: lead the prose with the gap, drawn from the weakest
    # pillar's own verdict, before the (deliberately gentler) shared overview.
    gap_lead = ""
    if weak_pillars:
        wk = weak_pillars[0]
        wv = verdicts.get(wk, {}).get("verdict", "")
        if wv:
            gap_lead = (
                f'<p class="summary-overview"><strong>Priority for the debrief '
                f'({wk}):</strong> {html.escape(wv)}</p>'
            )
    overview_html = gap_lead + (
        f'<p class="summary-overview">{html.escape(overview)}</p>'
        if not overview_offline else ""
    )

    left_html = (
        f'<div class="summary-left">'
        f'<div class="summary-header">'
        f'<span class="summary-badge {overall_cls}">{overall}</span>'
        f'</div>'
        + overview_html
        + callout_html
        + '</div>'
    )

    right_html = ""
    if rocks and not rocks_offline:
        items = "".join(
            f'<li class="summary-rock">{html.escape(r)}</li>'
            for r in rocks
        )
        right_html = (
            '<div class="summary-right">'
            '<div class="summary-rocks-label">What landed (perception)</div>'
            f'<ul class="summary-rock-list">{items}</ul>'
            '<p class="house-note">The messages a listener took away — see strength breakdown below.</p>'
            '</div>'
        )

    return f'<div class="summary-box">{left_html}{right_html}</div>'


def _compute_correlations(
    pace_windows: list, filler_by_window: list,
    pitch_windows: list, chart_min_wpm: int = 100,
) -> list:
    """Return up to 3 short insight strings from pace/filler/pitch correlations."""
    insights = []
    valid = [
        (w["wpm"], f)
        for w, f in zip(pace_windows, filler_by_window)
        if w["wpm"] >= chart_min_wpm
    ]
    if len(valid) >= 4:
        paces = [p for p, _ in valid]
        fillers = [f for _, f in valid]
        n = len(paces)
        mean_p = sum(paces) / n
        mean_f = sum(fillers) / n
        if mean_f > 0:
            cov = sum((p - mean_p) * (f - mean_f) for p, f in zip(paces, fillers)) / n
            std_p = (sum((p - mean_p) ** 2 for p in paces) / n) ** 0.5
            std_f = (sum((f - mean_f) ** 2 for f in fillers) / n) ** 0.5
            if std_p > 0 and std_f > 0:
                r = cov / (std_p * std_f)
                if r > 0.45:
                    insights.append("Fillers spike with pace — both peak in the same windows")
                elif r < -0.45:
                    insights.append("Fillers drop when pace is highest — the fast windows are the cleaner ones")

        # Pace trend: first half vs second half
        mid = n // 2
        if mid > 0:
            fh = sum(paces[:mid]) / mid
            sh = sum(paces[mid:]) / (n - mid)
            diff = (sh - fh) / fh if fh else 0
            if diff > 0.08:
                insights.append(f"Pace accelerated across the session — {fh:.0f} wpm in the first half, {sh:.0f} wpm in the second")
            elif diff < -0.08:
                insights.append(f"Pace eased as the session progressed — {fh:.0f} wpm in the first half, {sh:.0f} wpm in the second")

        # Late spike: an average can hide a hot close. Flag the peak in the
        # final third explicitly so the chip agrees with the storyboard.
        third = max(1, n // 3)
        final_third = paces[-third:]
        if final_third:
            peak = max(final_third)
            # 170 is the upper ideal edge; flag if the close runs above it
            if peak > 170:
                insights.append(f"Pace ran hot in the closing stretch — peaking at {peak:.0f} wpm, above the 170 wpm ceiling. The session average masks this.")

    if pitch_windows and pace_windows:
        valid_pp = [
            (w["wpm"], pw.get("mean_hz"))
            for w, pw in zip(pace_windows, pitch_windows)
            if w["wpm"] >= chart_min_wpm and pw.get("mean_hz")
        ]
        if len(valid_pp) >= 4:
            paces = [p for p, _ in valid_pp]
            pitches = [h for _, h in valid_pp]
            n = len(paces)
            mean_p = sum(paces) / n
            mean_h = sum(pitches) / n
            cov = sum((p - mean_p) * (h - mean_h) for p, h in zip(paces, pitches)) / n
            std_p = (sum((p - mean_p) ** 2 for p in paces) / n) ** 0.5
            std_h = (sum((h - mean_h) ** 2 for h in pitches) / n) ** 0.5
            if std_p > 0 and std_h > 0:
                r = cov / (std_p * std_h)
                if r > 0.45:
                    insights.append("Pitch rises with pace — faster windows are also higher-pitched")
                elif r < -0.45:
                    insights.append("Pitch drops as pace increases — the fast passages are flatter in delivery")

    return insights


def _correlations_html(
    pace_windows: list, filler_by_window: list,
    pitch_windows: list, chart_min_wpm: int = 100,
) -> str:
    insights = _compute_correlations(pace_windows, filler_by_window, pitch_windows, chart_min_wpm)
    if not insights:
        return ""
    chips = "".join(f'<span class="insight-chip">{html.escape(i)}</span>' for i in insights)
    return (
        '<div class="insight-box">'
        '<span class="insight-label">Pattern analysis</span>'
        + chips +
        '</div>'
    )


def _compact_tiles_section(metrics: dict, narrative: dict, config: dict) -> str:
    """Four compact tiles in one row replacing the two-section Story/Language layout."""
    cs = metrics.get("control_signals", {})
    rep = metrics.get("repetition", {})
    story_signals = metrics.get("story_signals", {})
    openers = metrics.get("sentence_openers", {})
    weak = metrics.get("weak_words", {})
    total_words = metrics.get("sentence_shape", {}).get("total_words", 1) or 1
    ca = narrative.get("conciseness_analysis", {})

    # ── Tile 1: Narrative control ─────────────────────────────────────────
    b = cs.get("bridge_count", 0)
    f_ = cs.get("flag_count", 0)
    h = cs.get("hook_count", 0)
    total_signals = b + f_ + h
    sig_cls = "green-text" if total_signals >= 4 else "watch-text"

    def sig_row(count, phrases, chip_cls, label):
        ex = " / ".join(f'"{p}"' for p in phrases[:2]) if phrases else "none"
        return (
            f'<div class="compact-sig">'
            f'<span class="sig-chip {chip_cls}">{count}x {label}</span>'
            f'<span class="compact-examples">{html.escape(ex)}</span>'
            f'</div>'
        )

    tile1 = (
        '<div class="compact-tile">'
        '<div class="compact-tile-label">Narrative control</div>'
        f'<div class="compact-big {sig_cls}">{total_signals}</div>'
        '<div class="compact-tile-sub">control signals total</div>'
        + sig_row(b, cs.get("bridges_detected", []), "sig-bridge", "bridges")
        + sig_row(f_, cs.get("flags_detected", []), "sig-flag", "flags")
        + sig_row(h, cs.get("hooks_detected", []), "sig-hook", "hooks")
        + '</div>'
    )

    # ── Tile 2: Sentence openers ──────────────────────────────────────────
    crutch_pct = openers.get("crutch_percentage", 0)
    by_opener = openers.get("by_opener", {})
    opener_top = ", ".join(f'"{t}" ({c}x)' for t, c in list(by_opener.items())[:3])
    hedged_pct = story_signals.get("hedged_opening_pct", 0)
    decl_pct = story_signals.get("declarative_opening_pct", 0)
    opener_cls = "watch-text" if crutch_pct >= 20 else "green-text"

    tile2 = (
        '<div class="compact-tile">'
        '<div class="compact-tile-label">Sentence openers</div>'
        f'<div class="compact-big {opener_cls}">{crutch_pct:.0f}%</div>'
        '<div class="compact-tile-sub">crutch openers (target &lt;20%)</div>'
        f'<p class="compact-note">Top: {html.escape(opener_top)}</p>'
        f'<div class="compact-row">'
        f'<span class="compact-stat green-text">{decl_pct:.0f}%</span>'
        f'<span class="compact-stat-label"> declarative &nbsp;</span>'
        f'<span class="compact-stat watch-text">{hedged_pct:.0f}%</span>'
        f'<span class="compact-stat-label"> hedged</span>'
        f'</div>'
        '</div>'
    )

    # ── Tile 3: Weak / hedging words ──────────────────────────────────────
    wk_total = weak.get("total", 0)
    wk_pct = round(wk_total / total_words * 100, 1)
    wk_target = config.get("weak_words", {}).get("target_pct", 4.0)
    wk_cls = "green-text" if wk_pct <= wk_target else "watch-text"
    top_weak = list(weak.get("top_offenders", {}).items())[:4]
    weak_bars = ""
    if top_weak:
        max_c = top_weak[0][1]
        for term, count in top_weak:
            w_bar = count / max_c * 100
            weak_bars += (
                f'<div class="word-bar">'
                f'<span class="word-label">{html.escape(term)}</span>'
                f'<div class="word-bar-fill" style="width:{w_bar:.0f}%"></div>'
                f'<span class="word-count">{count}x</span>'
                f'</div>'
            )

    tile3 = (
        '<div class="compact-tile">'
        '<div class="compact-tile-label">Weak / hedging words</div>'
        f'<div class="compact-big {wk_cls}">{wk_pct}%</div>'
        f'<div class="compact-tile-sub">of words (target &lt;{wk_target:.0f}%)</div>'
        + weak_bars
        + '</div>'
    )

    # ── Tile 4: Conciseness + repetition ──────────────────────────────────
    conc_pct = ca.get("estimated_excess_pct", 0)
    conc_target = config.get("conciseness", {}).get("target_excess_pct", 30.0)
    conc_cls = "green-text" if conc_pct <= conc_target else "watch-text"
    conc_offline = "[OFFLINE]" in ca.get("assessment", "")
    examples = ca.get("examples", [])
    ex_html = ""
    if examples and not conc_offline:
        ex = examples[0]
        ex_html = (
            f'<div class="conc-ex">'
            f'<div class="conc-orig">"{html.escape(ex.get("original",""))}"</div>'
            f'<div class="conc-sug">&#8594; "{html.escape(ex.get("suggested",""))}"</div>'
            f'</div>'
        )
    rep_pct = rep.get("repetition_pct", 0)
    rep_target = config.get("control", {}).get("repetition", {}).get("target_pct", 3.0)
    rep_cls = "green-text" if rep_pct <= rep_target else "watch-text"
    top_phrase = next(iter(rep.get("repeated_phrases", {})), "")
    top_count = rep.get("repeated_phrases", {}).get(top_phrase, 0) if top_phrase else 0

    tile4 = (
        '<div class="compact-tile">'
        '<div class="compact-tile-label">Conciseness &amp; repetition</div>'
        + (
            f'<div class="compact-big {conc_cls}">~{conc_pct:.0f}%</div>'
            f'<div class="compact-tile-sub">estimated excess (target &lt;{conc_target:.0f}%)</div>'
            + ex_html
            if not conc_offline else
            '<p class="muted" style="margin:8px 0">Conciseness requires API key.</p>'
        )
        + f'<div style="margin-top:8px">'
        f'<span class="compact-stat {rep_cls}">{rep_pct:.1f}%</span>'
        f'<span class="compact-stat-label"> repetition'
        + (f' — &ldquo;{html.escape(top_phrase)}&rdquo; ({top_count}x)' if top_phrase else "")
        + '</span></div>'
        + '</div>'
    )

    return (
        '<h2 class="section-heading">Story, control &amp; language</h2>'
        f'<div class="compact-grid">{tile1}{tile2}{tile3}{tile4}</div>'
    )


def _story_control_section(metrics: dict, narrative: dict) -> str:
    cs = metrics.get("control_signals", {})
    rep = metrics.get("repetition", {})
    story_signals = metrics.get("story_signals", {})

    def sig_row(label, count, phrases, colour):
        phrase_str = " / ".join(f'"{p}"' for p in phrases[:3]) if phrases else "none detected"
        w = min(count * 14, 100)
        return (
            f'<div class="signal-row">'
            f'<span class="signal-label">{label}</span>'
            f'<div class="signal-bar-wrap"><div class="signal-bar" style="width:{w}%;background:{colour}"></div></div>'
            f'<span class="signal-count">{count}x</span>'
            f'<span class="signal-examples">{html.escape(phrase_str)}</span>'
            f'</div>'
        )

    signals_html = (
        '<div class="story-col">'
        '<h4 class="sub-heading">Narrative control signals</h4>'
        + sig_row("Bridges", cs.get("bridge_count", 0), cs.get("bridges_detected", []), "#0CC0DF")
        + sig_row("Flags", cs.get("flag_count", 0), cs.get("flags_detected", []), "#0A5C6B")
        + sig_row("Hooks", cs.get("hook_count", 0), cs.get("hooks_detected", []), "#22c55e")
        + '</div>'
    )

    phrases = rep.get("repeated_phrases", {})
    rep_pct = rep.get("repetition_pct", 0)
    rep_rows = ""
    if phrases:
        max_c = max(phrases.values())
        for phrase, count in list(phrases.items())[:6]:
            w = count / max_c * 100
            rep_rows += (
                f'<div class="word-bar">'
                f'<span class="word-label-lg">{html.escape(phrase)}</span>'
                f'<div class="word-bar-fill" style="width:{w:.0f}%;background:#0A5C6B"></div>'
                f'<span class="word-count">{count}x</span>'
                f'</div>'
            )

    openers = metrics.get("sentence_openers", {})
    crutch_pct = openers.get("crutch_percentage", 0)
    by_opener = openers.get("by_opener", {})
    opener_top = ", ".join(f'"{t}" ({c}x)' for t, c in list(by_opener.items())[:3]) or "none"
    hedged_pct = story_signals.get("hedged_opening_pct", 0)
    decl_pct = story_signals.get("declarative_opening_pct", 0)

    detail_col = (
        '<div class="story-col">'
        '<h4 class="sub-heading">Sentence openers</h4>'
        f'<div class="opener-stat">'
        f'<span class="opener-num {"watch-text" if crutch_pct >= 20 else "green-text"}">{crutch_pct:.0f}%</span>'
        f'<span class="opener-label"> crutch openers — target &lt;20%</span>'
        f'</div>'
        f'<p class="signal-note">Top: {html.escape(opener_top)}</p>'
        f'<div class="opener-stat" style="margin-top:8px">'
        f'<span class="opener-num green-text">{decl_pct:.0f}%</span>'
        f'<span class="opener-label"> declarative</span>'
        f'<span class="opener-num watch-text" style="margin-left:16px">{hedged_pct:.0f}%</span>'
        f'<span class="opener-label"> hedged</span>'
        f'</div>'
        '<h4 class="sub-heading" style="margin-top:14px">Repetition</h4>'
        f'<div class="opener-stat">'
        f'<span class="opener-num {"watch-text" if rep_pct > 3 else "green-text"}">{rep_pct:.1f}%</span>'
        f'<span class="opener-label"> of words — target &lt;3%</span>'
        f'</div>'
        + rep_rows +
        '</div>'
    )

    return (
        '<h2 class="section-heading">Story &amp; control</h2>'
        f'<div class="story-grid">{signals_html}{detail_col}</div>'
    )


def _language_section(metrics: dict, narrative: dict, config: dict) -> str:
    weak = metrics.get("weak_words", {})
    total_words = metrics.get("sentence_shape", {}).get("total_words", 1) or 1
    wk_total = weak.get("total", 0)
    wk_pct = round(wk_total / total_words * 100, 1)
    wk_target = config.get("weak_words", {}).get("target_pct", 4.0)
    wk_cls = "green-text" if wk_pct <= wk_target else "watch-text"
    top = list(weak.get("top_offenders", {}).items())[:6]
    wk_rows = ""
    if top:
        max_c = top[0][1]
        for term, count in top:
            w = count / max_c * 100
            wk_rows += (
                f'<div class="word-bar">'
                f'<span class="word-label">{html.escape(term)}</span>'
                f'<div class="word-bar-fill" style="width:{w:.0f}%"></div>'
                f'<span class="word-count">{count}x</span>'
                f'</div>'
            )

    weak_col = (
        '<div class="lang-col">'
        '<h4 class="sub-heading">Weak / hedging words</h4>'
        f'<div class="opener-stat">'
        f'<span class="opener-num {wk_cls}">{wk_pct}%</span>'
        f'<span class="opener-label"> of words — target &lt;{wk_target:.0f}%</span>'
        f'</div>'
        + wk_rows +
        '</div>'
    )

    ca = narrative.get("conciseness_analysis", {})
    conc_pct = ca.get("estimated_excess_pct", 0)
    conc_target = config.get("conciseness", {}).get("target_excess_pct", 30.0)
    conc_cls = "green-text" if conc_pct <= conc_target else "watch-text"
    conc_text = ca.get("assessment", "")
    examples = ca.get("examples", [])
    offline_conc = "[OFFLINE]" in conc_text
    ex_html = ""
    if not offline_conc:
        for ex in examples[:3]:
            orig = ex.get("original", "")
            sug = ex.get("suggested", "")
            ex_html += (
                f'<div class="conc-ex">'
                f'<div class="conc-orig">"{html.escape(orig)}"</div>'
                f'<div class="conc-sug">&#8594; "{html.escape(sug)}"</div>'
                f'</div>'
            )

    conc_col = (
        '<div class="lang-col">'
        '<h4 class="sub-heading">Conciseness</h4>'
        + (
            f'<div class="opener-stat">'
            f'<span class="opener-num {conc_cls}">~{conc_pct:.0f}%</span>'
            f'<span class="opener-label"> estimated excess — target &lt;{conc_target:.0f}%</span>'
            f'</div>'
            f'<p class="signal-note" style="margin-bottom:8px">{html.escape(conc_text)}</p>'
            + ex_html
            if not offline_conc else
            '<p class="muted">Requires OPENAI_API_KEY.</p>'
        )
        + '</div>'
    )

    return (
        '<h2 class="section-heading">Language &amp; conciseness</h2>'
        f'<div class="lang-grid">{weak_col}{conc_col}</div>'
    )


def _pause_highlights_html(narrative: dict) -> str:
    highlights = narrative.get("pause_highlights", [])
    offline = highlights and "[OFFLINE]" in highlights[0].get("observation", "")
    if not highlights or offline:
        return ""
    rows = []
    for h in highlights:
        t = h.get("timestamp_approx", "—")
        quote = h.get("quote", "")
        obs = h.get("observation", "")
        rows.append(
            f'<div class="pause-row">'
            f'<span class="pause-time">{html.escape(t)}</span>'
            f'<div class="pause-body">'
            f'<div class="pause-quote">"{html.escape(quote)}"</div>'
            f'<div class="pause-obs">{html.escape(obs)}</div>'
            f'</div>'
            f'</div>'
        )
    return (
        '<h2 class="section-heading">Use of pauses</h2>'
        '<div class="full-box">'
        '<h3>Pause moments — give the audience time to absorb</h3>'
        + "\n".join(rows) +
        '</div>'
    )


def _pitch_caveat_html(metrics: dict) -> str:
    """Reliability caveat under the delivery cards. Pitch is estimated from
    single-channel audio and is the least trustworthy metric — say so, and
    flag confidence, so James knows how far to trust the Hz figures when he
    quotes them. Targets are named as house standards, not external benchmarks."""
    pitch = metrics.get("pitch", {})
    measured = pitch.get("status") != "not_measured"
    rel = pitch.get("reliability", "medium") if measured else None
    caveat = ""
    if measured:
        rel_word = {"high": "high", "medium": "medium", "low": "low"}.get(rel, "medium")
        caveat = (
            '<p class="caveat">Pitch / melody is estimated from single-channel '
            'interview audio — treat as indicative, not instrument-grade. '
            f'Reliability this session: {rel_word}. Pace, fillers and pauses are '
            'measured directly and reliable.</p>'
        )
    house = (
        '<p class="house-note">Targets throughout (pace, fillers, crutch openers, '
        'weak words, conciseness) are Reput8ion house coaching standards set in '
        'config, not external benchmarks.</p>'
    )
    return caveat + house


def _question_handling_html(narrative: dict) -> str:
    """Question-handling table. The core media-training skill: did the answer
    meet the question, how long was it, did he accept or challenge a loaded
    premise. Built from interviewer turns paired with the answer that followed.
    Verdicts are AI draft judgements for James to confirm."""
    qa = narrative.get("question_handling", {})
    pairs = qa.get("pairs", []) if isinstance(qa, dict) else []
    offline = pairs and "[OFFLINE]" in str(pairs[0])
    if not pairs or offline:
        return ""

    verdict_cls = {
        "answered": "qv-yes", "yes": "qv-yes",
        "partial": "qv-partial",
        "deflected": "qv-deflected",
        "dodged": "qv-dodged",
    }
    verdict_label = {
        "answered": "Answered", "yes": "Answered", "partial": "Partial",
        "deflected": "Deflected", "dodged": "Dodged",
    }
    rows = ""
    answered = 0
    for p in pairs:
        v = (p.get("verdict") or "").lower()
        if v in ("answered", "yes"):
            answered += 1
        rows += (
            '<tr>'
            f'<td><span class="qa-q">{html.escape(p.get("question",""))}</span></td>'
            f'<td><span class="qa-verdict {verdict_cls.get(v,"qv-partial")}">'
            f'{verdict_label.get(v, v.title() or "—")}</span></td>'
            f'<td>{html.escape(str(p.get("answer_length","—")))}</td>'
            f'<td>{html.escape(str(p.get("time_to_substance","—")))}</td>'
            f'<td>{html.escape(p.get("premise_handling",""))}</td>'
            '</tr>'
        )
    score = f"{answered} / {len(pairs)}"
    weakest = qa.get("weakest_exchange", "")
    weakest_html = (
        f'<div class="qa-flag"><strong>Weakest exchange to raise:</strong> '
        f'{html.escape(weakest)}</div>' if weakest else ""
    )
    return (
        '<h2 class="section-heading">Question handling</h2>'
        '<div class="full-box">'
        '<h3>Did the answer meet the question?</h3>'
        f'<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:12px">'
        f'<span class="qa-score">{score}</span>'
        f'<span class="compact-stat-label">questions directly answered</span></div>'
        '<table class="qa-table"><thead><tr>'
        '<th>Question (interviewer)</th><th>Verdict</th><th>Answer length</th>'
        '<th>Time to substance</th><th>Premise handling</th>'
        '</tr></thead><tbody>'
        + rows +
        '</tbody></table>'
        + weakest_html +
        '<p class="caveat">Verdicts and premise-handling are AI draft judgements '
        'for review, not fixed scores — confirm against your own read of the session.</p>'
        '</div>'
    )


def _closing_summary_html(narrative: dict) -> str:
    """Closing 'focus areas to improve' box. Renders tips_for_success (ranked)
    and final_word — both already generated by the coach pass but previously
    discarded by the dashboard. This is the section James lifts into the
    debrief, so it leads with the work, not the reassurance."""
    tips = narrative.get("tips_for_success", [])
    tips_offline = tips and "[OFFLINE]" not in str(tips)
    if not tips or not tips_offline:
        return ""
    ordered = sorted(tips, key=lambda t: t.get("rank", 99))
    items = ""
    for t in ordered:
        tip = t.get("tip", "")
        rationale = t.get("rationale", "")
        items += (
            f'<li class="closing-item"><strong>{html.escape(tip)}</strong> '
            f'{html.escape(rationale)}</li>'
        )
    return (
        '<h2 class="section-heading">In summary — focus areas to improve</h2>'
        '<div class="closing-box">'
        '<h3>What to work on before the next session — ranked by impact</h3>'
        f'<ol class="closing-list">{items}</ol>'
        '</div>'
    )


def _presence_flag_html(pitch_measured: bool, has_video: bool = False) -> str:
    """Honest scope flag. Presence (eye contact, gesture, posture) cannot be
    judged from audio. State that plainly rather than letting the reader
    assume it was assessed."""
    if has_video:
        return ""
    return (
        '<div class="presence-flag">&#9679;&nbsp;<strong>Audio-only session</strong> '
        '— physical presence (eye contact, gesture, posture) not assessed. '
        'Delivery, story and control below are from voice and transcript.</div>'
    )


# ---------- Main renderer ----------

def _render_html(
    context, metrics, pace_windows, pace_snippets, pitch_windows,
    filler_by_window, speaker_info, pace_cfg, chart_min_wpm,
    pitch_measured, narrative, config,
) -> str:
    candidate = html.escape(context.get("candidate", ""))
    session = html.escape(context.get("session", ""))
    date = html.escape(context.get("date", ""))

    ideal_min = pace_cfg.get("ideal_min", 140)
    ideal_max = pace_cfg.get("ideal_max", 170)
    n = len(pace_windows)

    pace_labels = json.dumps([_fmt_time(w["start_seconds"]) for w in pace_windows])
    pace_values = json.dumps([w["wpm"] if w["wpm"] >= chart_min_wpm else None for w in pace_windows])
    ideal_min_data = json.dumps([ideal_min] * n)
    ideal_max_data = json.dumps([ideal_max] * n)
    filler_data = json.dumps(filler_by_window)

    pitch_values = json.dumps([w["mean_hz"] for w in pitch_windows] if pitch_measured and pitch_windows else [None] * n)
    # Interpolate pitch to match pace window count if lengths differ
    if pitch_measured and pitch_windows and len(pitch_windows) != n:
        pitch_values = json.dumps([None] * n)

    pitch_dataset = ""
    pitch_axis = ""
    if pitch_measured and pitch_windows:
        pitch_dataset = f"""
      {{
        label: 'Pitch (Hz)',
        data: {pitch_values},
        type: 'line',
        borderColor: '#0A5C6B',
        backgroundColor: 'transparent',
        fill: false, tension: 0.35, pointRadius: 3,
        pointBackgroundColor: '#0A5C6B', borderWidth: 1.5,
        spanGaps: false, yAxisID: 'yHz', order: 2,
      }},"""
        pitch_axis = """
      yHz: {
        type: 'linear', position: 'right', display: true,
        title: {display: true, text: 'Pitch (Hz)', color: '#0A5C6B'},
        grid: {drawOnChartArea: false},
        ticks: {color: '#0A5C6B'},
      },"""

    css = """
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:Arial,sans-serif;background:#f0f4f8;color:#1e293b;font-size:14px}
    header{background:#0A5C6B;color:#fff;padding:18px 32px}
    header h1{font-size:1.3rem;font-weight:700}
    header p{opacity:.7;margin-top:3px;font-size:.82rem}
    .container{max-width:1300px;margin:0 auto;padding:16px 28px}
    .speaker-note{background:#e0f7fa;border-left:4px solid #0CC0DF;padding:9px 14px;
      margin-bottom:14px;font-size:.78rem;border-radius:0 4px 4px 0;color:#0A5C6B}
    .section-heading{font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;
      color:#94a3b8;margin:18px 0 8px;padding-bottom:5px;border-bottom:1px solid #e2e8f0}
    /* Delivery cards */
    .cards.four-col{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px}
    .card{background:#fff;border-radius:8px;padding:14px 16px;
      box-shadow:0 1px 3px rgba(0,0,0,.07);border-top:4px solid #e2e8f0}
    .card.green{border-top-color:#22c55e}.card.watch{border-top-color:#f59e0b}
    .card.red{border-top-color:#ef4444}.card.not_measured{border-top-color:#94a3b8}
    .card-label{font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;
      color:#64748b;margin-bottom:5px}
    .card-value{font-size:1.7rem;font-weight:700;color:#0f172a;line-height:1}
    .card-sub{font-size:.72rem;color:#94a3b8;margin-top:4px}
    .card-detail{font-size:.72rem;color:#64748b;margin-top:6px;line-height:1.5}
    .card-status{font-size:.68rem;font-weight:700;margin-top:8px}
    .card.green .card-status{color:#22c55e}.card.watch .card-status{color:#d97706}
    .card.red .card-status{color:#dc2626}.card.not_measured .card-status{color:#94a3b8}
    /* Charts */
    .chart-box{background:#fff;border-radius:8px;padding:16px;
      box-shadow:0 1px 3px rgba(0,0,0,.07);margin-bottom:10px}
    .chart-box h3{font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;
      color:#64748b;margin-bottom:12px}
    /* Storyboard */
    .storyboard-wrap{margin-bottom:14px}
    .storyboard-legend{display:flex;gap:10px;margin-bottom:6px}
    .leg{font-size:.68rem;font-weight:700;padding:2px 8px;border-radius:4px}
    .storyboard{display:flex;flex-wrap:wrap;gap:8px}
    .stile{border-radius:6px;padding:8px 10px;min-width:150px;max-width:220px;flex:1}
    .tile-green{background:#dcfce7;border:1px solid #86efac}
    .tile-amber{background:#fef3c7;border:1px solid #fcd34d}
    .tile-red{background:#fee2e2;border:1px solid #fca5a5}
    .tile-gray{background:#f1f5f9;border:1px solid #cbd5e1}
    .stile-time{font-family:monospace;font-size:.7rem;font-weight:700;color:#334155}
    .stile-wpm{font-size:1rem;font-weight:700;color:#0f172a;margin:2px 0}
    .stile-snippet{font-size:.68rem;color:#475569;line-height:1.3}
    .tile-green .stile-wpm{color:#166534}.tile-amber .stile-wpm{color:#92400e}
    .tile-red .stile-wpm{color:#991b1b}
    .leg.tile-green{background:#dcfce7;color:#166534}
    .leg.tile-amber{background:#fef3c7;color:#92400e}
    .leg.tile-red{background:#fee2e2;color:#991b1b}
    /* Pillar columns */
    .pillar-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:12px}
    .pillar-col{background:#fff;border-radius:8px;padding:16px;
      box-shadow:0 1px 3px rgba(0,0,0,.07);border-top:4px solid #e2e8f0}
    .pillar-col.green-border{border-top-color:#22c55e}
    .pillar-col.watch-border{border-top-color:#f59e0b}
    .pillar-col.red-border{border-top-color:#ef4444}
    .pillar-header{display:flex;align-items:center;gap:10px;margin-bottom:10px}
    .pillar-title{font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;
      font-weight:700;color:#334155}
    .pillar-badge{font-size:.65rem;font-weight:700;padding:2px 8px;border-radius:999px}
    .pillar-badge.green{background:#dcfce7;color:#166534}
    .pillar-badge.watch{background:#fef3c7;color:#92400e}
    .pillar-badge.red{background:#fee2e2;color:#991b1b}
    .pillar-verdict{font-size:.85rem;font-weight:600;color:#1e293b;
      margin-bottom:10px;line-height:1.4}
    .pillar-narrative{font-size:.8rem;color:#475569;line-height:1.6;
      border-top:1px solid #f1f5f9;padding-top:10px;margin-top:4px}
    .pillar-signals{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
    .sig-chip{font-size:.68rem;font-weight:700;padding:2px 8px;border-radius:999px}
    .sig-bridge{background:#e0f7fa;color:#0A5C6B}
    .sig-flag{background:#e0f2fe;color:#075985}
    .sig-hook{background:#dcfce7;color:#166534}
    /* Two-col for rocks + strengths */
    .two-col{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
    .half-box{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.07)}
    .half-box h3{font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;
      color:#64748b;margin-bottom:10px}
    .strength-box{border-left:3px solid #22c55e}
    .rock-list,.strength-list{list-style:none;padding:0}
    .rock-item{padding:6px 0 6px 12px;border-left:2px solid #0CC0DF;
      margin-bottom:7px;font-size:.84rem;color:#1e293b;line-height:1.4}
    .strength-item{padding:6px 0 6px 12px;border-left:2px solid #22c55e;
      margin-bottom:7px;font-size:.84rem;color:#1e293b;line-height:1.4}
    .box-note{font-size:.7rem;color:#94a3b8;margin-top:8px;font-style:italic}
    /* Tone */
    .full-box{background:#fff;border-radius:8px;padding:16px;
      box-shadow:0 1px 3px rgba(0,0,0,.07);margin-bottom:12px}
    .full-box h3{font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;
      color:#64748b;margin-bottom:10px}
    .tone-box{border-left:3px solid #0CC0DF}
    .tone-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
    .tone-chip{background:#e0f7fa;color:#0A5C6B;font-size:.72rem;font-weight:700;
      padding:3px 10px;border-radius:999px}
    .box-narrative{font-size:.84rem;color:#374151;line-height:1.6}
    /* Coaching moments */
    .moment-row{display:flex;align-items:flex-start;gap:10px;padding:8px 0;
      border-bottom:1px solid #f8fafc}
    .moment-row:last-child{border-bottom:none}
    .moment-time{font-family:monospace;font-size:.76rem;color:#0A5C6B;
      font-weight:700;min-width:36px;padding-top:1px}
    .moment-text{font-size:.84rem;color:#374151;flex:1;line-height:1.4}
    .moment-badge{font-size:.65rem;font-weight:700;padding:2px 8px;
      border-radius:999px;white-space:nowrap;margin-top:1px}
    .strength-badge{background:#dcfce7;color:#166534}
    .watch-badge{background:#fef3c7;color:#92400e}
    /* Story & control */
    .story-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
    .story-col{background:#fff;border-radius:8px;padding:16px;
      box-shadow:0 1px 3px rgba(0,0,0,.07)}
    .sub-heading{font-size:.65rem;text-transform:uppercase;letter-spacing:.07em;
      color:#94a3b8;margin-bottom:10px;font-weight:700}
    .signal-row{display:flex;align-items:center;gap:8px;margin-bottom:9px}
    .signal-label{font-size:.76rem;color:#374151;min-width:54px;font-weight:600}
    .signal-bar-wrap{flex:1;background:#f1f5f9;border-radius:3px;height:12px;overflow:hidden}
    .signal-bar{height:12px;border-radius:3px;min-width:3px}
    .signal-count{font-size:.72rem;color:#64748b;min-width:24px;text-align:right}
    .signal-examples{font-size:.68rem;color:#94a3b8;flex:2}
    .signal-note{font-size:.72rem;color:#64748b;margin-top:6px;font-style:italic}
    .opener-stat{display:flex;align-items:center;margin-bottom:8px}
    .opener-num{font-size:1.05rem;font-weight:700;margin-right:4px}
    .opener-label{font-size:.76rem;color:#64748b}
    .green-text{color:#22c55e}.watch-text{color:#d97706}
    .word-bar{display:flex;align-items:center;gap:8px;margin-bottom:6px}
    .word-label{font-size:.76rem;color:#374151;min-width:100px}
    .word-label-lg{font-size:.74rem;color:#374151;min-width:150px}
    .word-bar-fill{height:14px;background:#0CC0DF;border-radius:3px;min-width:3px}
    .word-count{font-size:.7rem;color:#94a3b8}
    /* Language */
    .lang-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
    .lang-col{background:#fff;border-radius:8px;padding:16px;
      box-shadow:0 1px 3px rgba(0,0,0,.07)}
    .conc-ex{background:#f8fafc;border-radius:5px;padding:8px 10px;margin-bottom:6px}
    .conc-orig{font-size:.78rem;color:#64748b;margin-bottom:3px}
    .conc-sug{font-size:.78rem;color:#0A5C6B;font-weight:600}
    /* Pauses */
    .pause-row{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid #f8fafc}
    .pause-row:last-child{border-bottom:none}
    .pause-time{font-family:monospace;font-size:.76rem;color:#0A5C6B;
      font-weight:700;min-width:36px;padding-top:2px}
    .pause-body{flex:1}
    .pause-quote{font-size:.82rem;color:#374151;font-style:italic;margin-bottom:3px}
    .pause-obs{font-size:.78rem;color:#64748b}
    .muted{color:#94a3b8;font-style:italic;font-size:.82rem}
    /* Session summary — two-column */
    .summary-box{background:#fff;border-radius:8px;padding:14px 16px;
      box-shadow:0 1px 3px rgba(0,0,0,.07);margin-bottom:12px;
      border-left:4px solid #0CC0DF;display:flex;gap:20px}
    .summary-left{flex:3;min-width:0}
    .summary-right{flex:1.1;border-left:2px solid #f1f5f9;padding-left:18px;min-width:180px}
    .summary-header{margin-bottom:8px}
    .summary-badge{font-size:.78rem;font-weight:700;padding:3px 12px;border-radius:999px;display:inline-block}
    .summary-badge.green{background:#dcfce7;color:#166534}
    .summary-badge.watch{background:#fef3c7;color:#92400e}
    .summary-badge.red{background:#fee2e2;color:#991b1b}
    .summary-overview{font-size:.84rem;color:#374151;line-height:1.6;margin-bottom:8px}
    .summary-callout{font-size:.82rem;padding:4px 0;border-bottom:1px solid #f8fafc}
    .summary-callout:last-child{border-bottom:none}
    .callout-strength{color:#166534}.callout-watch{color:#92400e}
    .summary-rocks-label{font-size:.65rem;text-transform:uppercase;letter-spacing:.07em;
      color:#64748b;font-weight:700;margin-bottom:8px}
    .summary-rock-list{list-style:none;padding:0;margin:0}
    .summary-rock{font-size:.8rem;color:#1e293b;padding:5px 0 5px 10px;
      border-left:2px solid #0CC0DF;margin-bottom:6px;line-height:1.4}
    /* Pattern insights */
    .insight-box{background:#f8fafc;border-radius:8px;padding:8px 14px;
      margin-bottom:12px;display:flex;flex-wrap:wrap;align-items:center;gap:8px}
    .insight-label{font-size:.65rem;text-transform:uppercase;letter-spacing:.07em;
      color:#94a3b8;font-weight:700}
    .insight-chip{background:#e0f7fa;color:#0A5C6B;font-size:.76rem;
      padding:3px 10px;border-radius:999px;font-style:italic}
    /* Compact 4-column tiles */
    .compact-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px}
    .compact-tile{background:#fff;border-radius:8px;padding:14px;
      box-shadow:0 1px 3px rgba(0,0,0,.07)}
    .compact-tile-label{font-size:.65rem;text-transform:uppercase;letter-spacing:.07em;
      color:#64748b;margin-bottom:5px;font-weight:700}
    .compact-big{font-size:1.5rem;font-weight:700;line-height:1}
    .compact-tile-sub{font-size:.68rem;color:#94a3b8;margin-top:2px;margin-bottom:6px}
    .compact-note{font-size:.72rem;color:#64748b;margin-bottom:5px;font-style:italic}
    .compact-sig{display:flex;align-items:center;gap:6px;margin-bottom:4px;flex-wrap:wrap}
    .compact-examples{font-size:.68rem;color:#94a3b8;font-style:italic}
    .compact-row{display:flex;align-items:center;flex-wrap:wrap;margin-top:5px;gap:2px}
    .compact-stat{font-size:.95rem;font-weight:700}
    .compact-stat-label{font-size:.72rem;color:#64748b}
    /* Pillar bullets */
    .pillar-bullet-list{margin:8px 0 0;padding:0;list-style:none;
      border-top:1px solid #f1f5f9;padding-top:8px}
    .pillar-bullet{font-size:.8rem;color:#475569;line-height:1.5;
      padding:3px 0 3px 14px;position:relative}
    .pillar-bullet::before{content:"›";position:absolute;left:0;
      color:#0CC0DF;font-weight:700}
    /* Refit additions */
    .caveat{font-size:.68rem;color:#94a3b8;font-style:italic;margin-top:6px;line-height:1.4}
    .house-note{font-size:.65rem;color:#b0bcc9;font-style:italic;margin-top:4px}
    .presence-flag{background:#f1f5f9;border:1px dashed #cbd5e1;border-radius:8px;
      padding:12px 16px;margin-bottom:12px;font-size:.82rem;color:#64748b;text-align:center}
    .rock-line{display:flex;align-items:flex-start;gap:8px;justify-content:space-between;
      padding:6px 0 6px 10px;border-left:2px solid #cbd5e1;margin-bottom:7px;
      font-size:.84rem;color:#1e293b;line-height:1.4}
    .rock-line.landed{border-left-color:#22c55e}
    .rock-line.weak{border-left-color:#f59e0b}
    .rock-line.missed{border-left-color:#ef4444}
    .rock-state{font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;
      padding:1px 7px;border-radius:999px;white-space:nowrap;margin-top:1px}
    .rs-landed{background:#dcfce7;color:#166534}
    .rs-weak{background:#fef3c7;color:#92400e}
    .rs-missed{background:#fee2e2;color:#991b1b}
    .delta-banner{background:#f8fafc;border-radius:6px;padding:8px 12px;margin-top:12px;
      font-size:.8rem;color:#475569;line-height:1.5;border-left:3px solid #0CC0DF}
    .qa-table{width:100%;border-collapse:collapse;font-size:.78rem}
    .qa-table th{text-align:left;font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;
      color:#94a3b8;font-weight:700;padding:6px 8px;border-bottom:1px solid #e2e8f0}
    .qa-table td{padding:8px;border-bottom:1px solid #f1f5f9;vertical-align:top;
      color:#374151;line-height:1.4}
    .qa-q{font-weight:600;color:#1e293b}
    .qa-verdict{font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;
      padding:2px 7px;border-radius:999px;white-space:nowrap}
    .qv-yes{background:#dcfce7;color:#166534}
    .qv-partial{background:#fef3c7;color:#92400e}
    .qv-deflected{background:#ffedd5;color:#9a3412}
    .qv-dodged{background:#fee2e2;color:#991b1b}
    .qa-score{font-size:1.4rem;font-weight:700;color:#0f172a}
    .qa-flag{background:#fef3c7;border-left:3px solid #f59e0b;padding:8px 12px;
      border-radius:0 4px 4px 0;font-size:.78rem;color:#92400e;margin-top:10px;line-height:1.4}
    .closing-box{background:#0A5C6B;color:#fff;border-radius:8px;padding:20px 24px;margin-bottom:14px}
    .closing-box h3{font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;
      color:#9fdce6;margin-bottom:14px}
    .closing-list{list-style:none;padding:0;margin:0;counter-reset:cl}
    .closing-item{counter-increment:cl;position:relative;padding:8px 0 8px 38px;
      font-size:.9rem;line-height:1.5;border-bottom:1px solid rgba(255,255,255,.12)}
    .closing-item:last-child{border-bottom:none}
    .closing-item::before{content:counter(cl);position:absolute;left:0;top:8px;
      width:24px;height:24px;background:#0CC0DF;color:#04323a;border-radius:50%;
      display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700}
    .closing-item strong{color:#9fdce6}
    footer{text-align:center;padding:16px;color:#cbd5e1;font-size:.68rem}
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Coach Dashboard — {candidate}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>{css}</style>
</head>
<body>
<header>
  <h1>{candidate} — {session}</h1>
  <p>{date} &nbsp;·&nbsp; Reput8ion Delivery Lab &nbsp;·&nbsp; Coach view</p>
</header>
<div class="container">
  {_speaker_note(speaker_info)}
  {_presence_flag_html(pitch_measured, context.get("has_video", False))}
  {_delivery_cards(metrics, config)}
  {_pitch_caveat_html(metrics)}
  {_session_summary_html(narrative, metrics, config)}

  <div class="chart-box">
    <h3>Pace · Pitch · Fillers — combined timeline ({_fmt_time(pace_windows[-1]["end_seconds"] if pace_windows else 0)} session)</h3>
    <canvas id="mainChart" height="80"></canvas>
  </div>
  {_storyboard(pace_windows, pace_snippets, pace_cfg)}
  {_correlations_html(pace_windows, filler_by_window, pitch_windows, chart_min_wpm)}

  {_pillar_columns(narrative, metrics)}
  {_rocks_and_strengths(narrative)}
  {_tone_html(narrative)}
  {_coaching_moments_html(narrative)}
  {_compact_tiles_section(metrics, narrative, config)}
  {_question_handling_html(narrative)}
  {_pause_highlights_html(narrative)}
  {_closing_summary_html(narrative)}
</div>
<footer>Reput8ion Delivery Lab &nbsp;·&nbsp; {date}</footer>

<script>
Chart.defaults.font.family = 'Arial, sans-serif';
Chart.defaults.font.size = 11;

new Chart(document.getElementById('mainChart').getContext('2d'), {{
  data: {{
    labels: {pace_labels},
    datasets: [
      {{
        label: 'Ideal min',
        type: 'line',
        data: {ideal_min_data},
        borderColor: 'rgba(34,197,94,0.35)', borderDash: [5,3],
        borderWidth: 1.5, pointRadius: 0, fill: false,
        yAxisID: 'yWpm', order: 5,
      }},
      {{
        label: 'Ideal max',
        type: 'line',
        data: {ideal_max_data},
        borderColor: 'rgba(34,197,94,0.35)', borderDash: [5,3],
        borderWidth: 1.5, pointRadius: 0,
        fill: '-1', backgroundColor: 'rgba(34,197,94,0.06)',
        yAxisID: 'yWpm', order: 4,
      }},
      {{
        label: 'Fillers',
        type: 'bar',
        data: {filler_data},
        backgroundColor: 'rgba(245,158,11,0.35)',
        borderColor: 'rgba(245,158,11,0.6)',
        borderWidth: 1, borderRadius: 2,
        yAxisID: 'yFillers', order: 3,
      }},
      {pitch_dataset}
      {{
        label: 'Pace (WPM)',
        type: 'line',
        data: {pace_values},
        borderColor: '#0CC0DF', backgroundColor: 'rgba(12,192,223,0.08)',
        fill: false, tension: 0.3, pointRadius: 3,
        pointBackgroundColor: '#0CC0DF', borderWidth: 2,
        spanGaps: false, yAxisID: 'yWpm', order: 1,
      }},
    ]
  }},
  options: {{
    responsive: true,
    interaction: {{mode:'index', intersect:false}},
    plugins: {{
      legend: {{
        display: true,
        labels: {{
          filter: item => !['Ideal min','Ideal max'].includes(item.text),
          boxWidth: 18,
        }}
      }},
      tooltip: {{
        callbacks: {{
          label: ctx => {{
            if (ctx.dataset.label === 'Pace (WPM)' && ctx.parsed.y !== null)
              return 'Pace: ' + ctx.parsed.y.toFixed(0) + ' wpm';
            if (ctx.dataset.label === 'Fillers')
              return 'Fillers: ' + ctx.parsed.y;
            if (ctx.dataset.label === 'Pitch (Hz)' && ctx.parsed.y)
              return 'Pitch: ' + ctx.parsed.y.toFixed(0) + ' Hz';
            return '';
          }}
        }}
      }}
    }},
    scales: {{
      yWpm: {{
        type: 'linear', position: 'left', min: 80,
        title: {{display:true, text:'WPM', color:'#0CC0DF'}},
        grid: {{color:'rgba(0,0,0,0.04)'}},
        ticks: {{color:'#64748b'}},
      }},
      yFillers: {{
        type: 'linear', position: 'right', min: 0, max: 12,
        display: false,
      }},
      {pitch_axis}
      x: {{
        title: {{display:true, text:'Time', color:'#94a3b8'}},
        grid: {{display:false}},
        ticks: {{maxRotation:45, color:'#94a3b8'}},
      }}
    }}
  }}
}});
</script>
</body>
</html>"""

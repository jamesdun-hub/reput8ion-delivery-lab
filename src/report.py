"""
Report renderer for Reput8ion Delivery Lab.

Participant-facing Word document — data-driven, second-person, mirrors the
depth of the coach dashboard. Every section is rendered from metrics and
narrative dicts; no AI generation happens here.

Sections
--------
1.  Cover page
2.  Delivery scorecard  (four-metric table)
3.  Pace chart          (matplotlib PNG or fallback table)
4.  Pillar assessment   (Delivery / Story / Control blocks)
5.  What landed         (rocks with strength verdicts)
6.  Tone profile
7.  Question by question
8.  Story, control and language
9.  Performance analytics  (analytics_section from narrative)
10. Before your next session (tips)
11. A final word           (cleaned of banned phrases)

render_client_report() is unchanged — it generates the 7-section
client-facing Word document driven by the client_report.md prompt.
"""

import io
import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import parse_xml


# ── Status colour/label maps ──────────────────────────────────────────────────

_STATUS_COLORS = {
    "green": (0, 153, 51),
    "watch": (204, 140, 0),
    "red":   (204, 0, 0),
}

_STATUS_LABELS = {
    "green": "Green",
    "watch": "Watch",
    "red":   "Needs work",
}

# Light tinted backgrounds for hard-numbers table cells
_STATUS_LIGHT_HEX = {
    "green": "E8F5EC",
    "watch": "FFF3E0",
    "red":   "FDECEA",
}

# Phrases that must not appear in the closing section
_BANNED_CLOSING = {
    "commendable",
    "well on your way",
    "significant progress",
    "keep building",
    "strong foundation",
    "further enhance",
    "as you refine",
    "continue to develop",
    "continuing to develop",
}


# ── Scorecard helpers ─────────────────────────────────────────────────────────

def _scorecard_badge(raw_status: str) -> tuple:
    """Map a metrics status string to (display label, RGB colour tuple)."""
    label = {
        "ideal":        "Good",
        "green":        "Good",
        "watch":        "Watch",
        "amber":        "Watch",
        "edge_fast":    "Watch",
        "hard_fast":    "Develop",
        "too_slow":     "Develop",
        "red":          "Develop",
        "not_measured": "—",
    }.get(raw_status or "", "—")
    colour = {
        "Good":    (0, 153, 51),
        "Watch":   (204, 140, 0),
        "Develop": (204, 0, 0),
        "—":       (120, 120, 120),
    }.get(label, (120, 120, 120))
    return label, colour


# ── Text cleaning ─────────────────────────────────────────────────────────────

def _to_second_person(text: str, first_name: str) -> str:
    """Replace first-name references with second-person pronouns.

    Handles possessive (Mark's → your), vocative (Mark, → you,) and
    standalone subject use (Mark used → you used).
    """
    if not text or not first_name:
        return text
    fn = re.escape(first_name)
    text = re.sub(rf"\b{fn}'s\b",  "your", text)
    text = re.sub(rf"\b{fn},",     "you,", text)
    text = re.sub(rf"\b{fn}\b",    "you",  text)
    # Fix grammar artefacts from the substitution
    text = re.sub(r"\byou is\b",   "you are", text)
    text = re.sub(r"\byou was\b",  "you were", text)
    text = re.sub(r"\byou's\b",    "your", text)
    return text


def _clean_final_word(text: str) -> str:
    """Strip sentences that contain banned closing phrases.

    Returns the remaining sentences joined. If the result is under 20 words
    the caller should use the overview as a fallback.
    """
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    clean = [s for s in sentences
             if not any(phrase in s.lower() for phrase in _BANNED_CLOSING)]
    return " ".join(clean)


# ── Pace chart ────────────────────────────────────────────────────────────────

def _build_pace_chart_png(pace_data: dict) -> bytes | None:
    """Generate a coloured bar chart of pace windows.

    Returns PNG bytes, or None if matplotlib is unavailable.
    Bars coloured: cyan (#0CC0DF) = ideal 140–170 wpm,
                   amber (#F59E0B) = below target or edge-fast,
                   red (#EF4444) = above 170 wpm.
    Dashed reference lines at 140 wpm (green) and 170 wpm (amber).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    windows = [w for w in (pace_data.get("windows") or []) if w.get("wpm", 0) > 50]
    if not windows:
        return None

    labels = [
        f"{int(w['start_seconds'] // 60)}:{int(w['start_seconds'] % 60):02d}"
        for w in windows
    ]
    values = [w["wpm"] for w in windows]
    colours = [
        "#EF4444" if v > 170 else "#0CC0DF" if v >= 140 else "#F59E0B"
        for v in values
    ]

    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    ax.bar(range(len(labels)), values, color=colours, width=0.75,
           edgecolor="white", linewidth=0.4)
    ax.axhline(140, color="#22C55E", linewidth=1.2, linestyle="--", alpha=0.85)
    ax.axhline(170, color="#F59E0B", linewidth=1.2, linestyle="--", alpha=0.85)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Words per minute", fontsize=8)
    ax.set_ylim(0, max(max(values) * 1.2, 210))
    ax.set_title("Pace across the session", fontsize=10, pad=6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="y", labelsize=7)

    n = len(labels)
    ax.text(n - 0.5, 172, "170 wpm", fontsize=6,
            color="#F59E0B", va="bottom", ha="right")
    ax.text(n - 0.5, 142, "140 wpm", fontsize=6,
            color="#22C55E", va="bottom", ha="right")

    plt.tight_layout(pad=0.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _add_pace_fallback_table(doc, windows: list, cyan_hex: str) -> None:
    """Plain table fallback when matplotlib is unavailable.

    TODO: upgrade to matplotlib chart — add matplotlib to requirements.txt
    and the import guard in _build_pace_chart_png will enable it automatically.
    """
    active = [w for w in windows if w.get("wpm", 0) > 50]
    if not active:
        _add_body(doc, "Pace window data not available.")
        return
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    for i, label in enumerate(["Window", "WPM", "Zone"]):
        table.rows[0].cells[i].text = label
        for p in table.rows[0].cells[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Arial"
                r.font.size = Pt(9)
        _shade_cell(table.rows[0].cells[i], cyan_hex)
    for w in active:
        wpm = w.get("wpm", 0)
        zone = ("Ideal" if 140 <= wpm <= 170
                else "Above target" if wpm > 170 else "Below target")
        start = w.get("start_seconds", 0)
        lbl = f"{int(start // 60)}:{int(start % 60):02d}"
        row = table.add_row().cells
        row[0].text = lbl
        row[1].text = str(wpm)
        row[2].text = zone
        for cell in row:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.name = "Arial"
                    r.font.size = Pt(9)


def _add_pace_chart(doc, pace_data: dict, cyan_hex: str) -> None:
    """Embed matplotlib chart or fall back to plain table."""
    png = _build_pace_chart_png(pace_data)
    if png:
        doc.add_picture(io.BytesIO(png), width=Inches(6.0))
        doc.paragraphs[-1].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    else:
        windows = [w for w in (pace_data.get("windows") or []) if w.get("wpm", 0) > 50]
        _add_pace_fallback_table(doc, windows, cyan_hex)


# ── Section renderers ─────────────────────────────────────────────────────────

def _add_delivery_scorecard(doc, metrics: dict, cyan_hex: str) -> None:
    """Four-row scorecard: Pace, Filler words, Vocal variety, Pauses."""
    pace   = metrics.get("pace")   or {}
    fill   = metrics.get("fillers") or {}
    pitch  = metrics.get("pitch")  or {}
    pauses = metrics.get("pauses") or {}

    pitch_result = (
        f"{pitch.get('mean_hz', '—')} Hz  ·  {pitch.get('std_semitones', '—')} semitone variation"
        if pitch.get("status") != "not_measured"
        else "Not measured this session"
    )
    pause_result = (
        f"{pauses.get('count', '—')} pauses  ·  {pauses.get('avg_seconds', '—')}s average"
        if pauses.get("status") != "not_measured"
        else "Not measured this session"
    )

    rows_data = [
        (
            "Pace",
            f"{pace.get('net_wpm', '—')} wpm  (gross {pace.get('gross_wpm', '—')} wpm)",
            "140–170 wpm",
            _scorecard_badge(pace.get("status", "")),
        ),
        (
            "Filler words",
            f"{fill.get('total', '—')} total  ·  {fill.get('per_100_words', '—')} per 100 words",
            "Under 4.0 per 100",
            _scorecard_badge(fill.get("status", "")),
        ),
        (
            "Vocal variety",
            pitch_result,
            "Above 4 semitones",
            _scorecard_badge(pitch.get("status", "")),
        ),
        (
            "Pauses",
            pause_result,
            "30–60 pauses",
            _scorecard_badge(pauses.get("status", "")),
        ),
    ]

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for i, lbl in enumerate(["Metric", "Your result", "Target", "Status"]):
        c = table.rows[0].cells[i]
        c.text = lbl
        for p in c.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Arial"
                r.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        _shade_cell(c, cyan_hex)

    for metric_name, result, target, (badge_label, badge_rgb) in rows_data:
        row = table.add_row().cells
        row[0].text = metric_name
        for p in row[0].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Arial"
                r.font.size = Pt(10)

        for col_i, content in enumerate([result, target], start=1):
            row[col_i].text = content
            for p in row[col_i].paragraphs:
                for r in p.runs:
                    r.font.name = "Arial"
                    r.font.size = Pt(10)

        sp = row[3].paragraphs[0]
        sp.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        sr = sp.add_run(badge_label)
        sr.font.name  = "Arial"
        sr.font.size  = Pt(10)
        sr.font.bold  = True
        sr.font.color.rgb = RGBColor(*badge_rgb)


def _add_pillar_blocks(doc, verdicts: dict, teal_hex: str) -> None:
    """Render Delivery / Story / Control as a 3-column visual table."""
    pillars = [
        ("Delivery", _coerce_verdict(verdicts.get("delivery") or {})),
        ("Story",    _coerce_verdict(verdicts.get("story") or {})),
        ("Control",  _coerce_verdict(verdicts.get("control") or {})),
    ]

    table = doc.add_table(rows=2, cols=3)
    table.style = "Table Grid"

    for col_i, (name, v) in enumerate(pillars):
        status = v.get("status", "watch")
        verdict_text = v.get("verdict", "")
        badge_label, badge_rgb = _scorecard_badge(status)

        # Header row: teal background, pillar name + badge
        hc = table.rows[0].cells[col_i]
        hp = hc.paragraphs[0]
        hp.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        hr1 = hp.add_run(name.upper())
        hr1.font.name  = "Arial"
        hr1.font.size  = Pt(10)
        hr1.font.bold  = True
        hr1.font.color.rgb = RGBColor(255, 255, 255)
        hr2 = hp.add_run(f"  {badge_label}")
        hr2.font.name  = "Arial"
        hr2.font.size  = Pt(9)
        hr2.font.bold  = True
        hr2.font.color.rgb = RGBColor(*badge_rgb)
        _shade_cell(hc, teal_hex)

        # Verdict row: verdict text in plain body
        vc = table.rows[1].cells[col_i]
        vp = vc.paragraphs[0]
        vp.paragraph_format.space_before = Pt(5)
        vp.paragraph_format.space_after  = Pt(5)
        vr = vp.add_run(verdict_text)
        vr.font.name = "Arial"
        vr.font.size = Pt(10)


def _add_rocks_section(doc, rocks: list, rock_strengths: list,
                       delta: str, teal_hex: str, first_name: str) -> None:
    """Rock listing with strength verdict and coaching delta note."""
    for i, rock in enumerate(rocks):
        meta = rock_strengths[i] if i < len(rock_strengths) else {}
        strength = (meta.get("strength") or "").lower()
        note = meta.get("note", "")

        badge = ("Landed strongly"    if strength == "strong"
                 else "Needs reinforcement" if strength == "weak"
                 else "")
        badge_rgb = ((0, 153, 51) if strength == "strong"
                     else (204, 140, 0))

        rock_p = doc.add_paragraph()
        rock_p.paragraph_format.left_indent  = Inches(0.15)
        rock_p.paragraph_format.space_before = Pt(6)
        rock_p.paragraph_format.space_after  = Pt(2)
        rr = rock_p.add_run(rock)
        rr.font.name = "Arial"
        rr.font.size = Pt(11)

        verdict_p = doc.add_paragraph()
        verdict_p.paragraph_format.left_indent  = Inches(0.3)
        verdict_p.paragraph_format.space_before = Pt(2)
        verdict_p.paragraph_format.space_after  = Pt(8)
        if badge:
            vr1 = verdict_p.add_run(badge)
            vr1.font.name  = "Arial"
            vr1.font.size  = Pt(9)
            vr1.font.bold  = True
            vr1.font.color.rgb = RGBColor(*badge_rgb)
        if note:
            sep = verdict_p.add_run(("  —  " if badge else "") + note)
            sep.font.name  = "Arial"
            sep.font.size  = Pt(9)
            sep.font.color.rgb = RGBColor(100, 100, 100)

    if delta:
        clean_delta = _to_second_person(delta, first_name)
        delta_p = doc.add_paragraph()
        delta_p.paragraph_format.left_indent  = Inches(0.15)
        delta_p.paragraph_format.space_before = Pt(8)
        d1 = delta_p.add_run("The coaching point:  ")
        d1.font.name  = "Arial"
        d1.font.size  = Pt(10)
        d1.font.bold  = True
        d1.font.color.rgb = RGBColor(*_hex_to_rgb(teal_hex))
        d2 = delta_p.add_run(clean_delta)
        d2.font.name = "Arial"
        d2.font.size = Pt(10)


def _add_story_control_language(doc, metrics: dict,
                                narrative: dict, teal_hex: str) -> None:
    """Section 8 — three sub-sections from metrics and narrative."""
    cs         = metrics.get("control_signals")  or {}
    openers    = metrics.get("sentence_openers") or {}
    weak       = metrics.get("weak_words")       or {}
    shape      = metrics.get("sentence_shape")   or {}
    conciseness = narrative.get("conciseness_analysis") or {}
    total_words = shape.get("total_words", 1) or 1

    # 8.1 Narrative control
    _add_subsection_heading(doc, "Narrative control", teal_hex)
    b  = cs.get("bridge_count", 0)
    f_ = cs.get("flag_count", 0)
    h  = cs.get("hook_count", 0)
    total_sigs = cs.get("total_control_signals", b + f_ + h)

    ctrl_p = doc.add_paragraph()
    cr = ctrl_p.add_run(
        f"You used {total_sigs} control signal{'s' if total_sigs != 1 else ''} "
        f"across the session: "
        f"{b} bridge{'s' if b != 1 else ''}, "
        f"{f_} flag{'s' if f_ != 1 else ''}, "
        f"{h} hook{'s' if h != 1 else ''}."
    )
    cr.font.name = "Arial"
    cr.font.size = Pt(11)

    if b == 0 and f_ == 0:
        note_p = doc.add_paragraph()
        note_p.paragraph_format.space_before = Pt(4)
        nr = note_p.add_run(
            "Bridging and flagging are the primary techniques for steering an "
            "interview toward your messages. The practice section below covers "
            "how to build these."
        )
        nr.font.name   = "Arial"
        nr.font.size   = Pt(10)
        nr.font.italic = True
        nr.font.color.rgb = RGBColor(100, 100, 100)

    # 8.2 Sentence openers
    _add_subsection_heading(doc, "Sentence openers", teal_hex)
    crutch_pct = openers.get("crutch_percentage", 0)
    by_opener  = openers.get("by_opener") or {}
    top_opener = next(iter(by_opener), None)
    top_count  = by_opener.get(top_opener, 0) if top_opener else 0

    op_p = doc.add_paragraph()
    opr = op_p.add_run(
        f"{crutch_pct}% of your sentences opened with a crutch word."
        + (f"  The dominant opener was '{top_opener}' ({top_count} times)." if top_opener else "")
        + "  Target: under 20%."
    )
    opr.font.name = "Arial"
    opr.font.size = Pt(11)

    # 8.3 Language precision
    _add_subsection_heading(doc, "Language precision", teal_hex)

    wk_total = weak.get("total", 0)
    wk_rate  = round(wk_total / total_words * 100, 1)
    top_offenders = list((weak.get("top_offenders") or {}).items())[:4]

    wk_p = doc.add_paragraph()
    wkr  = wk_p.add_run(
        f"Weak and hedging words: {wk_rate}% of words — target under 4%."
    )
    wkr.font.name = "Arial"
    wkr.font.size = Pt(11)

    if top_offenders:
        offender_str = ", ".join(
            f"'{term}' ({count}×)" for term, count in top_offenders
        )
        off_p = doc.add_paragraph()
        off_p.paragraph_format.space_before = Pt(2)
        offr = off_p.add_run(offender_str)
        offr.font.name  = "Arial"
        offr.font.size  = Pt(10)
        offr.font.color.rgb = RGBColor(80, 80, 80)

    excess_pct = conciseness.get("estimated_excess_pct", 0)
    conc_p = doc.add_paragraph()
    conc_p.paragraph_format.space_before = Pt(6)
    concr = conc_p.add_run(
        f"Conciseness: approximately {excess_pct}% of words were "
        "unnecessary — target under 30%."
    )
    concr.font.name = "Arial"
    concr.font.size = Pt(11)

    examples = conciseness.get("examples") or []
    if examples:
        ex   = examples[0]
        orig = ex.get("original", "")
        sug  = ex.get("suggested", "")
        if orig and sug:
            _add_conciseness_example(doc, orig, sug)


# ── Main participant report renderer ──────────────────────────────────────────

def render_report(
    metrics: dict,
    narrative: dict,
    context: dict,
    config: dict,
    out_path: str,
) -> None:
    """Render the participant-facing delivery report as a Word document.

    11 sections, all data-driven from metrics and narrative dicts.
    Written in second person directly to the participant.
    No AI generation happens here — every number comes from the metrics
    engine and every verdict from the coaching narrative.
    """
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = config["brand"]["font"]
    style.font.size = Pt(11)

    brand      = config["brand"]
    deep_teal  = brand["deep_teal"]
    cyan       = brand["cyan"]
    candidate  = context.get("candidate", "")
    first_name = candidate.split()[0] if candidate else ""

    # ── Page setup (A4) ───────────────────────────────────────────────────────
    from docx.shared import Mm
    sect = doc.sections[0]
    sect.page_width    = Mm(210)
    sect.page_height   = Mm(297)
    sect.top_margin    = Mm(20)
    sect.bottom_margin = Mm(20)
    sect.left_margin   = Mm(25)
    sect.right_margin  = Mm(25)

    # ── Header ────────────────────────────────────────────────────────────────
    header_text = brand.get("header_text", brand.get("title", ""))
    if header_text:
        hdr_para = sect.header.paragraphs[0]
        hdr_para.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        hdr_run = hdr_para.add_run(header_text)
        hdr_run.font.name  = brand["font"]
        hdr_run.font.size  = Pt(9)
        hdr_run.font.color.rgb = RGBColor(*_hex_to_rgb(deep_teal))

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_text = brand.get("footer_text", "")
    if footer_text:
        ftr_para = sect.footer.paragraphs[0]
        ftr_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        ftr_run = ftr_para.add_run(footer_text)
        ftr_run.font.name   = brand["font"]
        ftr_run.font.size   = Pt(9)
        ftr_run.font.italic = True
        ftr_run.font.color.rgb = RGBColor(120, 120, 120)

    # ── SECTION 1: COVER ──────────────────────────────────────────────────────
    _add_centred_run(doc, brand["title"],    deep_teal, size=24, bold=True)
    _add_centred_run(doc, brand["subtitle"], deep_teal, size=12, italic=True)
    doc.add_paragraph()

    meta = doc.add_paragraph()
    meta.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    mr = meta.add_run(
        f"{candidate}  |  {context.get('session', '')}  |  {context.get('date', '')}"
    )
    mr.font.size   = Pt(10)
    mr.font.italic = True

    prep = doc.add_paragraph()
    prep.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    pr = prep.add_run(brand.get("signoff", "Prepared by James Dunny, Reput8ion Dynamics"))
    pr.font.size = Pt(10)
    pr.font.color.rgb = RGBColor(*_hex_to_rgb(deep_teal))
    doc.add_paragraph()

    # ── SECTION 2: DELIVERY SCORECARD ─────────────────────────────────────────
    _add_section_heading(doc, "Your delivery at a glance", deep_teal)
    _add_delivery_scorecard(doc, metrics, cyan)

    cav_p = doc.add_paragraph()
    cav_p.paragraph_format.space_before = Pt(6)
    cr = cav_p.add_run(
        "Pace, fillers and pauses are measured directly from your audio. "
        "Vocal variety is estimated and should be treated as indicative."
    )
    cr.font.name   = "Arial"
    cr.font.size   = Pt(9)
    cr.font.italic = True
    cr.font.color.rgb = RGBColor(120, 120, 120)
    doc.add_paragraph()

    # ── SECTION 3: PACE CHART ─────────────────────────────────────────────────
    _add_section_heading(doc, "Pace across the session", deep_teal)
    _add_pace_chart(doc, metrics.get("pace") or {}, cyan)

    pace_narrative = narrative.get("pace_and_tone_narrative", "")
    if pace_narrative:
        sents = [s.strip() for s in
                 re.split(r"(?<=[.!?])\s+", pace_narrative.strip()) if s.strip()]
        summary = ". ".join(sents[:2])
        if summary and not summary.endswith((".", "!", "?")):
            summary += "."
        summary = _to_second_person(summary, first_name)
        note_p = doc.add_paragraph()
        note_p.paragraph_format.space_before = Pt(6)
        note_r = note_p.add_run(summary)
        note_r.font.name   = "Arial"
        note_r.font.size   = Pt(10)
        note_r.font.italic = True
    doc.add_paragraph()

    # ── SECTION 4: PILLAR ASSESSMENT ─────────────────────────────────────────
    verdicts = narrative.get("pillar_verdicts")
    if verdicts and isinstance(verdicts, dict):
        _add_section_heading(doc, "Session assessment", deep_teal)
        _add_pillar_blocks(doc, verdicts, deep_teal)
        doc.add_paragraph()

    # ── SECTION 5: WHAT LANDED ───────────────────────────────────────────────
    rocks = narrative.get("inferred_rocks") or []
    if rocks:
        _add_section_heading(doc, "What your audience took away", deep_teal)

        intro_p = doc.add_paragraph()
        intro_p.paragraph_format.space_after = Pt(8)
        ir = intro_p.add_run(
            "These are the messages a listener would take away from this session — "
            "ranked by how clearly they registered."
        )
        ir.font.name   = "Arial"
        ir.font.size   = Pt(11)
        ir.font.italic = True

        _add_rocks_section(
            doc, rocks,
            narrative.get("rock_strength") or [],
            narrative.get("rock_delta_note", ""),
            deep_teal, first_name,
        )
        doc.add_paragraph()

    # ── SECTION 6: TONE PROFILE ──────────────────────────────────────────────
    tone         = narrative.get("tone_assessment") or {}
    descriptors  = tone.get("descriptors") or []
    tone_text    = tone.get("narrative", "")
    offline_tone = "[OFFLINE]" in tone_text if tone_text else False

    if descriptors or (tone_text and not offline_tone):
        _add_section_heading(doc, "How you came across", deep_teal)

        if descriptors:
            dp = doc.add_paragraph()
            dp.paragraph_format.space_after = Pt(6)
            for i, d in enumerate(descriptors):
                dr = dp.add_run(d)
                dr.font.name = "Arial"
                dr.font.size = Pt(12)
                dr.font.bold = True
                if i < len(descriptors) - 1:
                    sep = dp.add_run("  ·  ")
                    sep.font.name  = "Arial"
                    sep.font.size  = Pt(12)
                    sep.font.color.rgb = RGBColor(180, 180, 180)

        if tone_text and not offline_tone:
            _add_body(doc, _to_second_person(tone_text, first_name))
        doc.add_paragraph()

    # ── SECTION 7: QUESTION HANDLING ─────────────────────────────────────────
    qa = narrative.get("question_handling") or {}
    if isinstance(qa, dict) and qa.get("pairs"):
        pairs = qa["pairs"]
        _add_section_heading(doc, "Question by question", deep_teal)

        intro_q = doc.add_paragraph()
        intro_q.paragraph_format.space_after = Pt(6)
        iq = intro_q.add_run(
            f"{len(pairs)} question{'s' if len(pairs) != 1 else ''}. "
            "Here is how each landed."
        )
        iq.font.name   = "Arial"
        iq.font.size   = Pt(11)
        iq.font.italic = True

        _add_question_handling_table(
            doc, pairs, qa.get("weakest_exchange", ""), cyan
        )
        doc.add_paragraph()

    # ── SECTION 8: STORY, CONTROL AND LANGUAGE ───────────────────────────────
    _add_section_heading(doc, "Story, control and language", deep_teal)
    _add_story_control_language(doc, metrics, narrative, deep_teal)
    doc.add_paragraph()

    # ── SECTION 9: PERFORMANCE ANALYTICS ─────────────────────────────────────
    analytics = narrative.get("analytics_section", "")
    if analytics:
        _add_section_heading(doc, "Performance analytics", deep_teal)
        _add_body(doc, analytics)
        doc.add_paragraph()

    # ── SECTION 10: WHAT TO WORK ON ──────────────────────────────────────────
    tips = narrative.get("tips_for_success") or []
    if tips:
        _add_section_heading(doc, "Before your next session", deep_teal)

        intro_t = doc.add_paragraph()
        intro_t.paragraph_format.space_after = Pt(6)
        it = intro_t.add_run("Three areas, ranked by impact.")
        it.font.name   = "Arial"
        it.font.size   = Pt(11)
        it.font.italic = True

        for tip_obj in sorted(tips, key=lambda t: t.get("rank", 99)):
            para = doc.add_paragraph(style="List Number")
            para.paragraph_format.space_after = Pt(2)
            r = para.add_run(tip_obj.get("tip", ""))
            r.font.bold = True
            r.font.name = "Arial"
            r.font.size = Pt(11)
            rationale = tip_obj.get("rationale", "")
            if rationale:
                rat = doc.add_paragraph()
                rat.paragraph_format.left_indent  = Inches(0.4)
                rat.paragraph_format.space_before = Pt(0)
                rat.paragraph_format.space_after  = Pt(8)
                rr = rat.add_run(rationale)
                rr.font.name  = "Arial"
                rr.font.size  = Pt(10)
                rr.font.color.rgb = RGBColor(80, 80, 80)
        doc.add_paragraph()

    # ── SECTION 11: CLOSING ASSESSMENT ───────────────────────────────────────
    final_word = narrative.get("final_word", "")
    if final_word:
        _add_section_heading(doc, "A final word", deep_teal)
        cleaned = _clean_final_word(_to_second_person(final_word, first_name))
        if len(cleaned.split()) >= 20:
            _add_body(doc, cleaned)
        else:
            # Original was mostly filler — fall back to the overview paragraph
            fallback = _clean_final_word(
                _to_second_person(narrative.get("overview", ""), first_name)
            )
            if fallback:
                _add_body(doc, fallback)
        doc.add_paragraph()

    # ── SIGN-OFF ──────────────────────────────────────────────────────────────
    signoff = doc.add_paragraph()
    signoff.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    sr = signoff.add_run(brand.get("signoff", ""))
    sr.font.size   = Pt(10)
    sr.font.italic = True

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)


# ── Shared section primitives ─────────────────────────────────────────────────

def _coerce_verdict(v) -> dict:
    """Normalise a pillar verdict value — unwrap accidental list wrapping."""
    if isinstance(v, list):
        return v[0] if v and isinstance(v[0], dict) else {}
    return v if isinstance(v, dict) else {}


def _derive_verdict(narrative: dict) -> tuple:
    """Return (label, colour_rgb) from pillar verdict statuses."""
    raw = narrative.get("pillar_verdicts", {})
    if not isinstance(raw, dict):
        return "Session complete", (10, 92, 107)
    statuses = [_coerce_verdict(v).get("status", "watch") for v in raw.values()]
    if not statuses:
        return "Session complete", (10, 92, 107)
    if all(s == "green" for s in statuses):
        return "Strong session", (0, 153, 51)
    if any(s == "red" for s in statuses):
        return "Needs significant work", (204, 0, 0)
    return "Mixed session", (204, 140, 0)


def _add_centred_run(doc, text, color_hex, size=14, bold=False, italic=False):
    para = doc.add_paragraph()
    para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = para.add_run(text)
    r.font.size   = Pt(size)
    r.font.bold   = bold
    r.font.italic = italic
    r.font.name   = "Arial"
    r.font.color.rgb = RGBColor(*_hex_to_rgb(color_hex))


def _add_section_heading(doc, text, color_hex):
    heading = doc.add_paragraph()
    heading.style = "Heading 1"
    r = heading.add_run(text)
    r.font.color.rgb = RGBColor(*_hex_to_rgb(color_hex))
    r.font.size  = Pt(14)
    r.font.bold  = True
    r.font.name  = "Arial"


def _add_subsection_heading(doc, text, color_hex):
    """Heading 2 equivalent — used for sub-sections within a section."""
    heading = doc.add_paragraph()
    r = heading.add_run(text)
    r.font.color.rgb = RGBColor(*_hex_to_rgb(color_hex))
    r.font.size  = Pt(12)
    r.font.bold  = True
    r.font.name  = "Arial"
    heading.paragraph_format.space_before = Pt(14)
    heading.paragraph_format.space_after  = Pt(4)


def _add_body(doc, text):
    if not text:
        return None
    para = doc.add_paragraph()
    r = para.add_run(text)
    r.font.name = "Arial"
    r.font.size = Pt(11)
    return para


def _add_bullet(doc, text):
    para = doc.add_paragraph(style="List Bullet")
    r = para.add_run(text)
    r.font.name = "Arial"
    r.font.size = Pt(11)


# ── Tables ────────────────────────────────────────────────────────────────────

def _add_pillar_table(doc, verdicts, cyan_hex):
    """Legacy three-row pillar scorecard — kept for backward compatibility."""
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"

    hdr = table.rows[0].cells
    for i, label in enumerate(["Pillar", "Status", "Verdict"]):
        hdr[i].text = label
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Arial"
                r.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        _shade_cell(hdr[i], cyan_hex)

    for name, key in [("Delivery", "delivery"), ("Story", "story"), ("Control", "control")]:
        v = _coerce_verdict(verdicts.get(key, {}))
        cells = table.add_row().cells

        cells[0].text = name
        for p in cells[0].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Arial"
                r.font.size = Pt(11)

        status = v.get("status", "watch")
        sp = cells[1].paragraphs[0]
        sr = sp.add_run(_STATUS_LABELS.get(status, status.title()))
        sr.font.bold  = True
        sr.font.name  = "Arial"
        sr.font.size  = Pt(11)
        sr.font.color.rgb = RGBColor(*_STATUS_COLORS.get(status, (0, 0, 0)))
        sp.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        cells[2].text = v.get("verdict", "")
        for p in cells[2].paragraphs:
            for r in p.runs:
                r.font.name = "Arial"
                r.font.size = Pt(11)


def _add_metrics_table(doc, metrics, cyan_hex):
    """Hard-numbers delivery metrics table."""
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"

    hdr = table.rows[0].cells
    for i, label in enumerate(["Measure", "Result", "What it tells us"]):
        hdr[i].text = label
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Arial"
                r.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        _shade_cell(hdr[i], cyan_hex)

    rows_data = [
        ("Pace",             _format_pace(metrics.get("pace", {})),
         "Words per minute; gross over total time, net over speaking time.",
         metrics.get("pace", {}).get("status", "")),
        ("Filler words",     _format_fillers(metrics.get("fillers", {})),
         "Um, er, erm, etc. per 100 words; higher is more frequent.",
         metrics.get("fillers", {}).get("status", "")),
        ("Weak words",       _format_weak_words(metrics.get("weak_words", {})),
         "Hedges like 'just', 'really', 'sort of' per 100 words.",
         metrics.get("weak_words", {}).get("status", "")),
        ("Sentence openers", _format_openers(metrics.get("sentence_openers", {})),
         "Percentage of sentences starting with crutch words.",
         metrics.get("sentence_openers", {}).get("status", "")),
        ("Sentence shape",   _format_sentence_shape(metrics.get("sentence_shape", {})),
         "Average words per sentence; longer sentences are harder to follow.",
         metrics.get("sentence_shape", {}).get("status", "")),
        ("Pitch",            _format_pitch(metrics.get("pitch", {})),
         "Mean pitch and variation in semitones; higher variation is more engaging.",
         metrics.get("pitch", {}).get("status", "")),
        ("Pauses",           _format_pauses(metrics.get("pauses", {})),
         "Silent breaks; used well, they add emphasis and authority.",
         metrics.get("pauses", {}).get("status", "")),
        ("Energy",           _format_energy(metrics.get("energy", {})),
         "Dynamic range and trailing-off events; variety holds attention.",
         metrics.get("energy", {}).get("status", "")),
    ]

    for measure, result, explanation, status in rows_data:
        cells = table.add_row().cells
        cells[0].text = measure
        for p in cells[0].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Arial"
                r.font.size = Pt(11)
        cells[1].text = result
        if status in _STATUS_LIGHT_HEX:
            _shade_cell(cells[1], _STATUS_LIGHT_HEX[status])
        cells[2].text = explanation
        for cell in cells[1:]:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.name = "Arial"
                    r.font.size = Pt(11)


def _add_coaching_moments_table(doc, moments, cyan_hex):
    """Timestamped qualitative coaching moments table."""
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"

    hdr = table.rows[0].cells
    for i, label in enumerate(["Time", "Type", "What the coach noticed"]):
        hdr[i].text = label
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Arial"
                r.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        _shade_cell(hdr[i], cyan_hex)

    for m in moments:
        cells = table.add_row().cells
        cells[0].text = m.get("timestamp_approx", "")
        for p in cells[0].paragraphs:
            for r in p.runs:
                r.font.name = "Arial"
                r.font.size = Pt(10)

        mtype = m.get("type", "watch")
        tp = cells[1].paragraphs[0]
        tr = tp.add_run("Strength" if mtype == "strength" else "Watch")
        tr.font.bold = True
        tr.font.name = "Arial"
        tr.font.size = Pt(10)
        tr.font.color.rgb = RGBColor(
            *(0, 153, 51) if mtype == "strength" else (204, 140, 0)
        )
        tp.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        cells[2].text = m.get("observation", "")
        for p in cells[2].paragraphs:
            for r in p.runs:
                r.font.name = "Arial"
                r.font.size = Pt(10)


def _add_question_handling_table(doc, pairs, weakest_exchange, cyan_hex):
    """Structured Q&A table from coaching narrative pairs data.

    Verdict column: Answered = normal; Partial = italic;
    Deflected / Dodged = bold.
    """
    if not pairs:
        return
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"

    hdr = table.rows[0].cells
    for i, label in enumerate(
        ["Question", "Verdict", "Answer length", "Time to substance"]
    ):
        hdr[i].text = label
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Arial"
                r.font.color.rgb = RGBColor(255, 255, 255)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        _shade_cell(hdr[i], cyan_hex)

    for pair in pairs:
        verdict = (pair.get("verdict") or "").lower()
        cells = table.add_row().cells

        cells[0].text = pair.get("question", "")
        for p in cells[0].paragraphs:
            for r in p.runs:
                r.font.name = "Arial"
                r.font.size = Pt(10)

        vp = cells[1].paragraphs[0]
        vr = vp.add_run(verdict.title() if verdict else "—")
        vr.font.name = "Arial"
        vr.font.size = Pt(10)
        if verdict in ("deflected", "dodged"):
            vr.font.bold = True
        elif verdict == "partial":
            vr.font.italic = True

        cells[2].text = str(pair.get("answer_length", "—"))
        cells[3].text = str(pair.get("time_to_substance", "—"))
        for cell in cells[1:]:
            for p in cell.paragraphs:
                for r in p.runs:
                    if not r.font.name:
                        r.font.name = "Arial"
                    if not r.font.size:
                        r.font.size = Pt(10)

    if weakest_exchange:
        weak_para = doc.add_paragraph()
        weak_para.paragraph_format.space_before = Pt(6)
        wr = weak_para.add_run(f"The exchange to focus on: {weakest_exchange}")
        wr.font.name   = "Arial"
        wr.font.size   = Pt(10)
        wr.font.italic = True


def _add_conciseness_example(doc, original, suggested):
    """Render a before/after verbatim pair in a shaded box."""
    if not original and not suggested:
        return
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.rows[0].cells[0]
    _shade_cell(cell, "EAF5F7")

    p1 = cell.paragraphs[0]
    p1.paragraph_format.space_before = Pt(4)
    p1.paragraph_format.space_after  = Pt(2)
    r = p1.add_run("Verbatim: ")
    r.font.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p1.add_run(f"“{original}”")
    r.font.italic = True
    r.font.name   = "Arial"
    r.font.size   = Pt(10)

    p2 = cell.add_paragraph()
    p2.paragraph_format.space_before = Pt(2)
    p2.paragraph_format.space_after  = Pt(4)
    r = p2.add_run("Tighter: ")
    r.font.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p2.add_run(f"“{suggested}”")
    r.font.name = "Arial"
    r.font.size = Pt(10)

    doc.add_paragraph()


# ── Cell shading ──────────────────────────────────────────────────────────────

def _shade_cell(cell, hex_color):
    h = hex_color.lstrip("#")
    shading_elm = parse_xml(
        f'<w:shd w:fill="{h}" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
    )
    cell._element.get_or_add_tcPr().append(shading_elm)


# ── Colour utility ────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i: i + 2], 16) for i in (0, 2, 4))


# ── Metric formatters ─────────────────────────────────────────────────────────

def _format_pace(pace):
    if not pace or pace.get("status") == "not_measured":
        return "Not measured this session"
    return (
        f"Gross {pace['gross_wpm']} wpm, net {pace['net_wpm']} wpm"
        f" (target {pace['target_band']})"
    )


def _format_fillers(fillers):
    if not fillers or fillers.get("status") == "not_measured":
        return "Not measured this session"
    total = fillers["total"]
    per_100 = fillers["per_100_words"]
    by_token = fillers.get("by_token", {})
    itemised = ", ".join(
        f"{count} {token}"
        for token, count in sorted(by_token.items(), key=lambda x: -x[1])
    )
    if itemised:
        return f"{total} ({itemised}), {per_100} per 100 words"
    return f"{total} fillers, {per_100} per 100 words"


def _format_weak_words(weak):
    if not weak or weak.get("status") == "not_measured":
        return "Not measured this session"
    total = weak["total"]
    per_100 = weak["per_100_words"]
    top = list((weak.get("top_offenders") or {}).items())[:3]
    if top:
        top_str = ", ".join(f"{count} '{term}'" for term, count in top)
        return f"{total} ({top_str}), {per_100} per 100 words"
    return f"{total} weak words, {per_100} per 100 words"


def _format_openers(openers):
    if not openers or openers.get("status") == "not_measured":
        return "Not measured this session"
    count = openers["crutch_count"]
    pct = openers["crutch_percentage"]
    total = openers.get("sentence_count", "?")
    by_opener = openers.get("by_opener", {})
    top = next(iter(by_opener), None)
    if top:
        return f"{count} of {total} sentences ({pct}%), top crutch: '{top}'"
    return f"{count} sentences ({pct}%)"


def _format_sentence_shape(shape):
    if not shape:
        return "Not measured this session"
    avg = shape.get("avg_sentence_length_words", "—")
    longest = shape.get("longest_sentence_words", "—")
    return f"Average {avg} words per sentence, longest {longest} words"


def _format_pitch(pitch):
    if not pitch or pitch.get("status") == "not_measured":
        return "Not measured this session"
    mean = pitch.get("mean_hz", "—")
    range_ = pitch.get("range_hz", "—")
    std = pitch.get("std_semitones", "—")
    passages = len(pitch.get("monotone_passages", []))
    result = f"Mean {mean} Hz, range {range_} Hz, std {std} st"
    if passages > 0:
        result += f", {passages} monotone passage(s)"
    return result


def _format_pauses(pauses):
    if not pauses or pauses.get("status") == "not_measured":
        return "Not measured this session"
    count = pauses["count"]
    total = pauses["total_silent_seconds"]
    avg = pauses["avg_seconds"]
    longest = pauses["longest_seconds"]
    boundary = pauses["at_sentence_boundary"]
    return (
        f"{count} pauses, {total}s total ({avg}s avg, {longest}s longest),"
        f" {boundary} at sentence boundary"
    )


def _format_energy(energy):
    if not energy or energy.get("status") == "not_measured":
        return "Not measured this session"
    dynamic = energy.get("dynamic_range_db", "—")
    trailing = energy.get("trailing_off_count", 0)
    result = f"{dynamic} dB dynamic range"
    if trailing > 0:
        result += f", {trailing} trailing-off event(s)"
    return result


# ── Client report renderer ────────────────────────────────────────────────────

def render_client_report(
    client_narrative: dict,
    context: dict,  # candidate, session, date
    config: dict,
    out_path: str,
    coaching_narrative: dict | None = None,
) -> None:
    """Render the 7-section client report Word document.

    Uses CLIENT_REPORT_SCHEMA fields from coach.py. Entirely prose-driven —
    no metrics tables, no pillar scorecards. The quality of the output is
    determined by the client_report.md prompt and the trainer feedback
    transcript, not by the renderer.

    coaching_narrative is the NARRATIVE_SCHEMA dict from the first AI pass.
    When present, its question_handling.pairs are rendered as a structured
    table after the Performance Profile section.
    """
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = config["brand"]["font"]
    style.font.size = Pt(11)

    brand     = config["brand"]
    deep_teal = brand["deep_teal"]
    cyan      = brand["cyan"]

    # ── Page setup (A4) ───────────────────────────────────────────────────────
    from docx.shared import Mm
    section = doc.sections[0]
    section.page_width    = Mm(210)
    section.page_height   = Mm(297)
    section.top_margin    = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin   = Mm(25)
    section.right_margin  = Mm(25)

    # ── Header ────────────────────────────────────────────────────────────────
    header_text = brand.get("header_text", brand.get("title", ""))
    if header_text:
        hdr = section.header.paragraphs[0]
        hdr.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        hr = hdr.add_run(header_text)
        hr.font.name  = brand["font"]
        hr.font.size  = Pt(9)
        hr.font.color.rgb = RGBColor(*_hex_to_rgb(deep_teal))

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_text = brand.get("footer_text", "")
    if footer_text:
        ftr = section.footer.paragraphs[0]
        ftr.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        fr = ftr.add_run(footer_text)
        fr.font.name    = brand["font"]
        fr.font.size    = Pt(9)
        fr.font.italic  = True
        fr.font.color.rgb = RGBColor(120, 120, 120)

    # ── Title block ───────────────────────────────────────────────────────────
    _add_centred_run(doc, brand["title"],    deep_teal, size=24, bold=True)
    _add_centred_run(doc, brand["subtitle"], deep_teal, size=12, italic=True)
    doc.add_paragraph()
    meta = doc.add_paragraph()
    meta.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    mr = meta.add_run(
        f"{context['candidate']}  |  {context['session']}  |  {context['date']}"
    )
    mr.font.size   = Pt(10)
    mr.font.italic = True
    doc.add_paragraph()

    # ── Section 1: Executive Summary ─────────────────────────────────────────
    _add_section_heading(doc, "Executive Summary", deep_teal)
    _add_body(doc, client_narrative.get("executive_summary", ""))
    doc.add_paragraph()

    # ── Section 2: The Standard We Are Working Towards ───────────────────────
    _add_section_heading(doc, "The Standard We Are Working Towards", deep_teal)
    _add_body(doc, client_narrative.get("the_standard", ""))
    doc.add_paragraph()

    # ── Section 3: Performance Profile ───────────────────────────────────────
    _add_section_heading(doc, "Performance Profile", deep_teal)

    _sub_sections = [
        ("Message Architecture",      "message_architecture"),
        ("Presence and Authority",     "presence_and_authority"),
        ("Question Handling",          "question_handling"),
        ("Language and Register",      "language_and_register"),
        ("Composure and Adaptability", "composure_and_adaptability"),
    ]
    for sub_title, key in _sub_sections:
        _add_subsection_heading(doc, sub_title, deep_teal)
        _add_body(doc, client_narrative.get(key, ""))
        if key == "language_and_register":
            for ex in client_narrative.get("language_examples", []):
                _add_conciseness_example(
                    doc,
                    ex.get("original", ""),
                    ex.get("tighter", ""),
                )
        doc.add_paragraph()

    # ── Question handling table (from coaching narrative) ─────────────────────
    if coaching_narrative:
        qa = coaching_narrative.get("question_handling") or {}
        if isinstance(qa, dict):
            pairs = qa.get("pairs") or []
            weakest = qa.get("weakest_exchange", "")
            if pairs:
                _add_subsection_heading(doc, "Question Handling — detail", deep_teal)
                _add_question_handling_table(doc, pairs, weakest, cyan)
                doc.add_paragraph()

    # ── Section 4: Standout Strengths ────────────────────────────────────────
    _add_section_heading(doc, "Standout Strengths", deep_teal)
    _add_body(doc, client_narrative.get("standout_strengths", ""))
    doc.add_paragraph()

    # ── Section 5: Priority Development Areas ────────────────────────────────
    _add_section_heading(doc, "Priority Development Areas", deep_teal)
    _add_body(doc, client_narrative.get("priority_development_areas", ""))
    doc.add_paragraph()

    # ── Section 6: Practice Framework ────────────────────────────────────────
    _add_section_heading(doc, "Practice Framework", deep_teal)
    _add_body(doc, client_narrative.get("practice_framework", ""))
    doc.add_paragraph()

    # ── Section 7: Closing Assessment ────────────────────────────────────────
    _add_section_heading(doc, "Closing Assessment", deep_teal)
    _add_body(doc, client_narrative.get("closing_assessment", ""))
    doc.add_paragraph()

    # ── Sign-off ──────────────────────────────────────────────────────────────
    signoff = doc.add_paragraph()
    signoff.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    sr = signoff.add_run(brand["signoff"])
    sr.font.size   = Pt(10)
    sr.font.italic = True

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)

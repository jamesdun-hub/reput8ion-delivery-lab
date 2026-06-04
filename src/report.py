"""
Report renderer for Reput8ion Delivery Lab.

Generates a branded .docx leave-behind structured around the four-pillar
coaching model: Delivery | Story | Control | Audience.
"""

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import parse_xml


_STATUS_COLORS = {
    "green": (0, 153, 51),
    "watch": (204, 140, 0),
    "red": (204, 0, 0),
}

_STATUS_LABELS = {
    "green": "Green",
    "watch": "Watch",
    "red": "Needs work",
}

# Light-tinted cell backgrounds for the hard-numbers table
_STATUS_LIGHT_HEX = {
    "green": "E8F5EC",
    "watch": "FFF3E0",
    "red":   "FDECEA",
}


def _coerce_verdict(v) -> dict:
    """Normalise a single pillar verdict value.

    The OpenAI model occasionally wraps the verdict object in a one-element
    list rather than returning it as a plain dict. This helper unwraps that
    so the rest of the code can call .get() safely.
    """
    if isinstance(v, list):
        return v[0] if v and isinstance(v[0], dict) else {}
    return v if isinstance(v, dict) else {}


def _derive_verdict(narrative: dict) -> tuple:
    """Return (label, colour_rgb) from pillar verdict statuses.

    All green  → Strong session  (green)
    Any red    → Needs significant work  (red)
    Otherwise  → Mixed session  (amber)
    """
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


def render_report(
    metrics: dict,
    narrative: dict,
    context: dict,  # candidate, session, date
    config: dict,
    out_path: str,
) -> None:
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = config["brand"]["font"]
    style.font.size = Pt(11)

    brand = config["brand"]
    deep_teal = brand["deep_teal"]
    cyan = brand["cyan"]

    # ── Page setup (A4) ───────────────────────────────────────────────────────
    from docx.shared import Mm
    section = doc.sections[0]
    section.page_width  = Mm(210)
    section.page_height = Mm(297)
    section.top_margin    = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin   = Mm(25)
    section.right_margin  = Mm(25)

    # ── Header ────────────────────────────────────────────────────────────────
    header_text = brand.get("header_text", brand.get("title", ""))
    if header_text:
        hdr_para = section.header.paragraphs[0]
        hdr_para.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        hdr_run = hdr_para.add_run(header_text)
        hdr_run.font.name  = brand["font"]
        hdr_run.font.size  = Pt(9)
        hdr_run.font.color.rgb = RGBColor(*_hex_to_rgb(deep_teal))

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_text = brand.get("footer_text", "")
    if footer_text:
        ftr_para = section.footer.paragraphs[0]
        ftr_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        ftr_run = ftr_para.add_run(footer_text)
        ftr_run.font.name  = brand["font"]
        ftr_run.font.size  = Pt(9)
        ftr_run.font.italic = True
        ftr_run.font.color.rgb = RGBColor(120, 120, 120)

    # ── 1. Title block ───────────────────────────────────────────────────────
    _add_centred_run(doc, brand["title"], deep_teal, size=24, bold=True)
    _add_centred_run(doc, brand["subtitle"], deep_teal, size=12, italic=True)
    doc.add_paragraph()

    # ── 1b. Candidate line ───────────────────────────────────────────────────
    # (moved here so the verdict sits directly under the candidate line)

    meta = doc.add_paragraph()
    meta.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = meta.add_run(
        f"{context['candidate']}  |  {context['session']}  |  {context['date']}"
    )
    r.font.size = Pt(10)
    r.font.italic = True

    # ── 1c. Overall verdict badge ─────────────────────────────────────────────
    verdict_label, verdict_rgb = _derive_verdict(narrative)
    verdict_para = doc.add_paragraph()
    verdict_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    verdict_para.paragraph_format.space_before = Pt(8)
    verdict_para.paragraph_format.space_after  = Pt(8)
    vr = verdict_para.add_run(verdict_label.upper())
    vr.font.name  = brand["font"]
    vr.font.size  = Pt(13)
    vr.font.bold  = True
    vr.font.color.rgb = RGBColor(*verdict_rgb)
    doc.add_paragraph()

    # ── 2. Overview ──────────────────────────────────────────────────────────
    _add_section_heading(doc, "Overview", deep_teal)
    _add_body(doc, narrative.get("overview", ""))

    # ── 3. Performance at a glance (pillar scorecard) ────────────────────────
    _add_section_heading(doc, "Performance at a glance", deep_teal)
    verdicts = narrative.get("pillar_verdicts", {})
    if verdicts:
        _add_pillar_table(doc, verdicts, cyan)
    doc.add_paragraph()

    # ── 4. Key messages ──────────────────────────────────────────────────────
    rocks = narrative.get("inferred_rocks", [])
    if rocks:
        _add_section_heading(doc, "Key messages heard in this session", deep_teal)
        _add_body(
            doc,
            "These are the core messages the coach identified from your answers. "
            "If they do not match the messages you intended to land, that is the coaching signal.",
        )
        for rock in rocks:
            _add_bullet(doc, rock)
        doc.add_paragraph()

    # ── 5. Performance Analytics ──────────────────────────────────────────────
    analytics = narrative.get("analytics_section", "")
    if analytics:
        _add_section_heading(doc, "Performance Analytics", deep_teal)
        _add_body(doc, analytics)
        doc.add_paragraph()

    # ── 6. Strengths ─────────────────────────────────────────────────────────
    strengths = narrative.get("strengths", [])
    if strengths:
        _add_section_heading(doc, "What you did well", deep_teal)
        for strength in strengths:
            _add_bullet(doc, strength)
        doc.add_paragraph()

    # 6. Delivery: pace, tone, pauses
    _add_section_heading(doc, "Delivery: pace and tone", deep_teal)
    _add_body(doc, narrative.get("pace_and_tone_narrative", ""))

    tone = narrative.get("tone_assessment", {})
    if tone:
        descriptors = tone.get("descriptors", [])
        if descriptors:
            p = doc.add_paragraph()
            r = p.add_run("Tone: ")
            r.font.bold = True
            r.font.name = "Arial"
            r.font.size = Pt(11)
            r = p.add_run(", ".join(descriptors) + ".")
            r.font.name = "Arial"
            r.font.size = Pt(11)
        if tone.get("narrative"):
            _add_body(doc, tone["narrative"])

    pause_highlights = narrative.get("pause_highlights", [])
    if pause_highlights:
        p = doc.add_paragraph()
        r = p.add_run("Pause moments")
        r.font.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(11)
        for ph in pause_highlights:
            ts = ph.get("timestamp_approx", "")
            quote = ph.get("quote", "")
            obs = ph.get("observation", "")
            _add_bullet(doc, f"[{ts}] “{quote}”. {obs}")

    doc.add_paragraph()

    # 7. Delivery metrics table
    _add_section_heading(doc, "Delivery: the measured detail", deep_teal)
    _add_metrics_table(doc, metrics, cyan)
    doc.add_paragraph()

    # 8. Message discipline: story, control, conciseness
    _add_section_heading(doc, "Message discipline: story and control", deep_teal)
    _add_body(doc, narrative.get("filler_and_weak_words_narrative", ""))
    _add_body(doc, narrative.get("control_and_structure_narrative", ""))

    conciseness = narrative.get("conciseness_analysis", {})
    if conciseness:
        excess_pct = conciseness.get("estimated_excess_pct", 0)
        p = doc.add_paragraph()
        r = p.add_run(
            f"Conciseness (estimated excess: {excess_pct}%, target: below 30%)"
        )
        r.font.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(11)
        if conciseness.get("assessment"):
            _add_body(doc, conciseness["assessment"])
        for ex in conciseness.get("examples", []):
            _add_conciseness_example(
                doc, ex.get("original", ""), ex.get("suggested", "")
            )

    doc.add_paragraph()

    # ── 9. Coaching moments ───────────────────────────────────────────────────
    moments = narrative.get("coaching_moments", [])
    if moments:
        _add_section_heading(doc, "Coaching moments", deep_teal)
        _add_coaching_moments_table(doc, moments, cyan)
        doc.add_paragraph()

    # ── 10. Tips for success ──────────────────────────────────────────────────
    _add_section_heading(doc, "Three tips for success", deep_teal)
    for tip_obj in narrative.get("tips_for_success", []):
        # Tip: bold, numbered
        para = doc.add_paragraph(style="List Number")
        para.paragraph_format.space_after = Pt(2)
        r = para.add_run(tip_obj.get("tip", ""))
        r.font.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(11)
        # Rationale: plain, indented below the tip
        rationale = tip_obj.get("rationale", "")
        if rationale:
            rat = doc.add_paragraph()
            rat.paragraph_format.left_indent  = Inches(0.4)
            rat.paragraph_format.space_before = Pt(0)
            rat.paragraph_format.space_after  = Pt(8)
            r = rat.add_run(rationale)
            r.font.name  = "Arial"
            r.font.size  = Pt(10)
            r.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_paragraph()

    # ── 11. Final word ────────────────────────────────────────────────────────
    _add_section_heading(doc, "A final word", deep_teal)
    _add_body(doc, narrative.get("final_word", ""))
    doc.add_paragraph()

    signoff = doc.add_paragraph()
    signoff.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    r = signoff.add_run(brand["signoff"])
    r.font.size = Pt(10)
    r.font.italic = True

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)


# ── Section primitives ────────────────────────────────────────────────────────

def _add_centred_run(doc, text, color_hex, size=14, bold=False, italic=False):
    para = doc.add_paragraph()
    para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r = para.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = "Arial"
    r.font.color.rgb = RGBColor(*_hex_to_rgb(color_hex))


def _add_section_heading(doc, text, color_hex):
    heading = doc.add_paragraph()
    heading.style = "Heading 1"
    r = heading.add_run(text)
    r.font.color.rgb = RGBColor(*_hex_to_rgb(color_hex))
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.name = "Arial"


def _add_subsection_heading(doc, text, color_hex):
    """Heading 2 equivalent — used for 3.x sub-sections in the client report."""
    heading = doc.add_paragraph()
    r = heading.add_run(text)
    r.font.color.rgb = RGBColor(*_hex_to_rgb(color_hex))
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.name = "Arial"
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
    """Three-row pillar scorecard: Delivery | Story | Control."""
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
        sr.font.bold = True
        sr.font.name = "Arial"
        sr.font.size = Pt(11)
        sr.font.color.rgb = RGBColor(*_STATUS_COLORS.get(status, (0, 0, 0)))
        sp.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        cells[2].text = v.get("verdict", "")
        for p in cells[2].paragraphs:
            for r in p.runs:
                r.font.name = "Arial"
                r.font.size = Pt(11)


def _add_metrics_table(doc, metrics, cyan_hex):
    """Eight-row hard-numbers table."""
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
        (
            "Pace",
            _format_pace(metrics.get("pace", {})),
            "Words per minute; gross over total time, net over speaking time.",
            metrics.get("pace", {}).get("status", ""),
        ),
        (
            "Filler words",
            _format_fillers(metrics.get("fillers", {})),
            "Um, er, erm, etc. per 100 words; higher is more frequent.",
            metrics.get("fillers", {}).get("status", ""),
        ),
        (
            "Weak words",
            _format_weak_words(metrics.get("weak_words", {})),
            "Hedges like 'just', 'really', 'sort of' per 100 words.",
            metrics.get("weak_words", {}).get("status", ""),
        ),
        (
            "Sentence openers",
            _format_openers(metrics.get("sentence_openers", {})),
            "Percentage of sentences starting with crutch words.",
            metrics.get("sentence_openers", {}).get("status", ""),
        ),
        (
            "Sentence shape",
            _format_sentence_shape(metrics.get("sentence_shape", {})),
            "Average words per sentence; longer sentences are harder to follow.",
            metrics.get("sentence_shape", {}).get("status", ""),
        ),
        (
            "Pitch",
            _format_pitch(metrics.get("pitch", {})),
            "Mean pitch and variation in semitones; higher variation is more engaging.",
            metrics.get("pitch", {}).get("status", ""),
        ),
        (
            "Pauses",
            _format_pauses(metrics.get("pauses", {})),
            "Silent breaks; used well, they add emphasis and authority.",
            metrics.get("pauses", {}).get("status", ""),
        ),
        (
            "Energy",
            _format_energy(metrics.get("energy", {})),
            "Dynamic range and trailing-off events; variety holds attention.",
            metrics.get("energy", {}).get("status", ""),
        ),
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
        # Shade the Result cell to signal green / watch / red at a glance
        if status in _STATUS_LIGHT_HEX:
            _shade_cell(cells[1], _STATUS_LIGHT_HEX[status])
        cells[2].text = explanation
        for cell in cells[1:]:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.name = "Arial"
                    r.font.size = Pt(11)


def _add_coaching_moments_table(doc, moments, cyan_hex):
    """Timestamped qualitative coaching moments."""
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

    Verdict column styling: Answered = normal; Partial = italic;
    Deflected / Dodged = bold. If pairs is empty the call is a no-op.
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
        wr = weak_para.add_run(f"Weakest exchange: {weakest_exchange}")
        wr.font.name = "Arial"
        wr.font.size = Pt(10)
        wr.font.italic = True


def _add_conciseness_example(doc, original, suggested):
    # Render one before/after pair inside a lightly shaded single-cell table.
    if not original and not suggested:
        return
    # Wrap both lines in a borderless single-cell table with a light teal tint
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    cell = tbl.rows[0].cells[0]
    _shade_cell(cell, "EAF5F7")  # very light teal tint

    # "Verbatim:" line
    p1 = cell.paragraphs[0]
    p1.paragraph_format.space_before = Pt(4)
    p1.paragraph_format.space_after  = Pt(2)
    r = p1.add_run("Verbatim: ")
    r.font.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r = p1.add_run(f"“{original}”")
    r.font.italic = True
    r.font.name = "Arial"
    r.font.size = Pt(10)

    # "Tighter:" line
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

    doc.add_paragraph()  # breathing room after the box


# ── Cell shading ──────────────────────────────────────────────────────────────

def _shade_cell(cell, hex_color):
    h = hex_color.lstrip("#")
    shading_elm = parse_xml(
        f'<w:shd w:fill="{h}" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
    )
    cell._element.get_or_add_tcPr().append(shading_elm)


# ── Colour utility ────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


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

    brand = config["brand"]
    deep_teal = brand["deep_teal"]
    cyan = brand["cyan"]

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
        # Verbatim/tighter table appears directly under Language and Register
        if key == "language_and_register":
            for ex in client_narrative.get("language_examples", []):
                _add_conciseness_example(
                    doc,
                    ex.get("original", ""),
                    ex.get("tighter", ""),
                )
        doc.add_paragraph()

    # ── Question handling table (from coaching narrative) ─────────────────────
    # Rendered from the structured pairs data produced by the first AI pass,
    # so the table figures always match the coach dashboard exactly.
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

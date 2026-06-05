r"""
Generate the participant delivery report as a standalone HTML file.

Loads metrics.json, narrative.json and (if present) client_report.json
from a saved session folder and renders a complete participant-facing report:
data-driven sections (scorecard, pace chart, pillar assessment, rock strength)
followed by prose sections from the client report (presence and authority,
question handling, language and register, composure, strengths, development
areas, practice framework, closing assessment).

All output is:
- Second person ("you/your") — first names and third-person pronouns replaced
- Trainer-attribution removed — "the trainer recommended X" becomes "X"
- Banned closing phrases stripped from the closing assessment

Usage:
    python regenerate_report_html.py "output\Mark 6-4 June 2026"

Defaults to the most recently modified output folder.
"""

import html
import json
import re
import sys
import webbrowser
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR  = PROJECT_DIR / "output"

DEEP_TEAL = "#0A5C6B"
CYAN      = "#0CC0DF"

# Phrases banned from the closing assessment
_BANNED_CLOSING = {
    "commendable", "well on your way", "significant progress",
    "keep building", "strong foundation", "further enhance",
    "as you refine", "continue to develop", "continuing to develop",
    "your progress is", "perishable skills",
}


# ── Text cleaning ─────────────────────────────────────────────────────────────

def _to_second_person(text: str, first_name: str) -> str:
    """Replace first name and third-person pronouns with second person.

    Handles: possessives (Mark's → your), standalone name (Mark → you),
    and gendered pronouns (his → your, he → you, him → you).
    Applied after trainer-ref removal so pronoun replacements are clean.
    """
    if not text or not first_name:
        return text
    fn = re.escape(first_name)
    text = re.sub(rf"\b{fn}'s\b", "your", text)
    text = re.sub(rf"\b{fn},",    "you,", text)
    text = re.sub(rf"\b{fn}\b",   "you",  text)
    # Gendered pronouns referring to the participant
    text = re.sub(r"\bHis\b", "Your", text)
    text = re.sub(r"\bhis\b", "your", text)
    text = re.sub(r"\bHe\b",  "You",  text)
    text = re.sub(r"\bhe\b",  "you",  text)
    text = re.sub(r"\bHim\b", "You",  text)
    text = re.sub(r"\bhim\b", "you",  text)
    # Fix common grammar artefacts from substitution
    text = re.sub(r"\byou is\b",  "you are", text)
    text = re.sub(r"\byou was\b", "you were", text)
    text = re.sub(r"\byou's\b",   "your", text)
    return text


def _clean_trainer_refs(text: str) -> str:
    """Remove 'the trainer recommended/noted/said...' attribution phrases.

    Keeps the underlying content; removes only the attribution wrapper.
    Remaining 'the trainer' references become 'I' (the report author's voice).
    """
    if not text:
        return text

    # "as noted/mentioned/emphasized by the trainer" → ""
    text = re.sub(
        r",?\s*as (?:noted|mentioned|highlighted|emphasized) by the trainer,?",
        "", text, flags=re.IGNORECASE
    )

    # Remove whole sentences that are purely attribution:
    # "The trainer highlighted the importance of X by referencing Y."
    text = re.sub(
        r"The trainer (?:highlighted|noted) the importance of[^.]+\.",
        "", text, flags=re.IGNORECASE
    )

    # Remove "The trainer [verb] [that/the importance of/...] X" attribution
    text = re.sub(
        r"\bThe trainer (?:suggested|recommended|emphasized|stressed|explained|"
        r"noted|highlighted|pointed out|observed|mentioned|described|expressed|"
        r"advised|said)\s+(?:that\s+)?(?:the importance of\s+)?(?:a need for\s+)?",
        "", text, flags=re.IGNORECASE
    )

    # "the trainer's recommendation/advice/suggestion" → "the recommendation/..."
    text = re.sub(r"\bthe trainer's\s+", "the ", text, flags=re.IGNORECASE)

    # Any remaining "the trainer" → "I"
    text = re.sub(r"\bthe trainer\b", "I", text, flags=re.IGNORECASE)

    # Capitalise first letter of sentences that lost their subject
    text = re.sub(r"(?<=\. )([a-z])", lambda m: m.group(1).upper(), text)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    # Clean whitespace artefacts
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\. \.", ".", text)
    return text.strip()


def _clean_closing(text: str) -> str:
    """Strip sentences containing banned closing phrases."""
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    clean = [s for s in sentences
             if not any(p in s.lower() for p in _BANNED_CLOSING)]
    return " ".join(clean)


def _clean_prose(text: str, first_name: str) -> str:
    """Apply all cleaning passes to a prose section."""
    text = _clean_trainer_refs(text)
    text = _to_second_person(text, first_name)
    return text


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _e(text) -> str:
    return html.escape(str(text) if text is not None else "")


def _badge_cls(raw_status: str) -> tuple:
    label = {
        "ideal": "Good", "green": "Good",
        "watch": "Watch", "amber": "Watch", "edge_fast": "Watch",
        "hard_fast": "Develop", "too_slow": "Develop", "red": "Develop",
        "not_measured": "—",
    }.get(raw_status or "", "—")
    cls = {"Good": "badge-good", "Watch": "badge-watch",
           "Develop": "badge-develop", "—": "badge-na"}.get(label, "badge-na")
    return label, cls


def _pillar_badge(raw_status: str) -> tuple:
    label = {"green": "Good", "watch": "Watch", "red": "Develop"}.get(raw_status or "", "Watch")
    cls = {"Good": "pill-good", "Watch": "pill-watch",
           "Develop": "pill-develop"}.get(label, "pill-watch")
    return label, cls


def _section(title: str, content: str, id_attr: str = "") -> str:
    id_str = f' id="{id_attr}"' if id_attr else ""
    return (
        f'<section class="report-section"{id_str}>'
        f'<h2 class="section-heading">{_e(title)}</h2>'
        f'{content}'
        f'</section>'
    )


def _prose_block(text: str) -> str:
    """Render a prose string as one or more paragraphs."""
    if not text:
        return ""
    # Split on double newlines; fall back to single block
    parts = [p.strip() for p in re.split(r"\n{2,}", text.strip()) if p.strip()]
    if not parts:
        return f'<p class="prose">{_e(text)}</p>'
    return "".join(f'<p class="prose">{_e(p)}</p>' for p in parts)


def _verbatim_box(original: str, tighter: str) -> str:
    return (
        f'<div class="verbatim-box">'
        f'<div class="verb-orig"><span class="verb-label">Verbatim:</span> '
        f'&#8220;{_e(original)}&#8221;</div>'
        f'<div class="verb-arrow">&#8594;</div>'
        f'<div class="verb-tight"><span class="verb-label">Tighter:</span> '
        f'&#8220;{_e(tighter)}&#8221;</div>'
        f'</div>'
    )


# ── Data-driven section builders ──────────────────────────────────────────────

def _delivery_scorecard(metrics: dict) -> str:
    pace   = metrics.get("pace")    or {}
    fill   = metrics.get("fillers") or {}
    pitch  = metrics.get("pitch")   or {}
    pauses = metrics.get("pauses")  or {}

    pitch_val = (
        f"{pitch.get('mean_hz','—')} Hz · {pitch.get('std_semitones','—')} semitone variation"
        if pitch.get("status") != "not_measured" else "Not measured this session"
    )
    pause_val = (
        f"{pauses.get('count','—')} pauses · {pauses.get('avg_seconds','—')}s average"
        if pauses.get("status") != "not_measured" else "Not measured this session"
    )

    rows = [
        ("Pace",         f"{pace.get('net_wpm','—')} wpm  (gross {pace.get('gross_wpm','—')} wpm)", "140–170 wpm",       _badge_cls(pace.get("status",""))),
        ("Filler words", f"{fill.get('total','—')} total · {fill.get('per_100_words','—')} per 100 words", "Under 4.0 per 100", _badge_cls(fill.get("status",""))),
        ("Vocal variety", pitch_val, "Above 4 semitones", _badge_cls(pitch.get("status",""))),
        ("Pauses",        pause_val, "30–60 pauses",      _badge_cls(pauses.get("status",""))),
    ]

    tbody = "".join(
        f"<tr><td class='sc-name'>{_e(n)}</td>"
        f"<td class='sc-result'>{_e(r)}</td>"
        f"<td class='sc-target'>{_e(t)}</td>"
        f"<td><span class='badge {bc}'>{bl}</span></td></tr>"
        for n, r, t, (bl, bc) in rows
    )
    caveat = (
        "<p class='caveat'>Pace, fillers and pauses are measured directly from your audio. "
        "Vocal variety is estimated and should be treated as indicative.</p>"
    )
    return (
        "<table class='sc-table'>"
        "<thead><tr><th>Metric</th><th>Your result</th><th>Target</th><th>Status</th></tr></thead>"
        f"<tbody>{tbody}</tbody></table>{caveat}"
    )


def _pace_chart_html(pace_data: dict) -> str:
    windows = [w for w in (pace_data.get("windows") or []) if w.get("wpm", 0) > 50]
    if not windows:
        return "<p>Pace data not available.</p>"

    labels  = [f"{int(w['start_seconds']//60)}:{int(w['start_seconds']%60):02d}" for w in windows]
    values  = [w["wpm"] for w in windows]
    colours = ["'#EF4444'" if v > 170 else "'#0CC0DF'" if v >= 140 else "'#F59E0B'" for v in values]
    n = len(labels)

    return f"""
<div class="chart-box"><canvas id="paceChart" height="90"></canvas></div>
<script>
new Chart(document.getElementById('paceChart').getContext('2d'), {{
  data: {{
    labels: {json.dumps(labels)},
    datasets: [
      {{ label: 'Min', type: 'line', data: {json.dumps([140]*n)},
         borderColor: 'rgba(34,197,94,0.45)', borderDash: [5,3],
         borderWidth: 1.5, pointRadius: 0, fill: false, yAxisID: 'y', order: 3 }},
      {{ label: 'Max', type: 'line', data: {json.dumps([170]*n)},
         borderColor: 'rgba(245,158,11,0.5)', borderDash: [5,3],
         borderWidth: 1.5, pointRadius: 0,
         fill: '-1', backgroundColor: 'rgba(34,197,94,0.05)', yAxisID: 'y', order: 2 }},
      {{ label: 'Pace (wpm)', type: 'bar', data: {json.dumps(values)},
         backgroundColor: [{','.join(colours)}],
         borderColor: 'rgba(255,255,255,0.3)', borderWidth: 1, borderRadius: 3,
         yAxisID: 'y', order: 1 }},
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx =>
        ctx.dataset.label === 'Pace (wpm)' ? ctx.parsed.y.toFixed(0) + ' wpm' : '' }} }}
    }},
    scales: {{
      y: {{ min: 0, max: {max(max(values)*1.2, 210):.0f},
            title: {{ display: true, text: 'Words per minute', color: '#64748b' }},
            grid: {{ color: 'rgba(0,0,0,0.04)' }},
            ticks: {{ color: '#94a3b8', font: {{ size: 10 }} }} }},
      x: {{ grid: {{ display: false }},
            ticks: {{ color: '#94a3b8', font: {{ size: 10 }}, maxRotation: 45 }} }}
    }}
  }}
}});
</script>
<div class="chart-legend">
  <span class="leg leg-good">▪ 140–170 wpm  ideal</span>
  <span class="leg leg-slow">▪ below 140  below target</span>
  <span class="leg leg-fast">▪ above 170  above target</span>
</div>"""


def _pillar_assessment(verdicts: dict) -> str:
    cols = ""
    for name, key in [("Delivery","delivery"), ("Story","story"), ("Control","control")]:
        v = verdicts.get(key) or {}
        if isinstance(v, list):
            v = v[0] if v and isinstance(v[0], dict) else {}
        status  = v.get("status", "watch")
        verdict = v.get("verdict", "")
        bl, pc  = _pillar_badge(status)
        cols += (
            f'<div class="pillar-col">'
            f'<div class="pillar-hdr"><span class="pillar-name">{_e(name)}</span>'
            f'<span class="pill {pc}">{bl}</span></div>'
            f'<p class="pillar-verdict">{_e(verdict)}</p>'
            f'</div>'
        )
    return f'<div class="pillar-grid">{cols}</div>'


def _rocks_html(rocks: list, rock_strengths: list, delta: str, first_name: str) -> str:
    intro = (
        "<p class='section-intro'>These are the messages a listener would take away "
        "from this session — ranked by how clearly they registered.</p>"
    )
    items = ""
    for i, rock in enumerate(rocks):
        meta     = rock_strengths[i] if i < len(rock_strengths) else {}
        strength = (meta.get("strength") or "").lower()
        note     = meta.get("note", "")
        badge    = "Landed strongly" if strength == "strong" else "Needs reinforcement"
        bclass   = "rock-strong" if strength == "strong" else "rock-weak"
        items += (
            f'<div class="rock-card">'
            f'<p class="rock-text">{_e(rock)}</p>'
            f'<p class="rock-meta"><span class="{bclass}">{badge}</span>'
            + (f'<span class="rock-note"> — {_e(note)}</span>' if note else "")
            + f'</p></div>'
        )
    delta_html = ""
    if delta:
        clean_d = _clean_prose(delta, first_name)
        delta_html = (
            f'<div class="delta-box">'
            f'<strong>The coaching point:</strong> {_e(clean_d)}'
            f'</div>'
        )
    return intro + f'<div class="rocks-list">{items}</div>' + delta_html


def _story_control_data(metrics: dict, narrative: dict) -> str:
    """Data-driven narrative control / sentence openers / language precision."""
    cs          = metrics.get("control_signals")  or {}
    openers     = metrics.get("sentence_openers") or {}
    weak        = metrics.get("weak_words")       or {}
    shape       = metrics.get("sentence_shape")   or {}
    conciseness = narrative.get("conciseness_analysis") or {}
    total_words = shape.get("total_words", 1) or 1

    b  = cs.get("bridge_count", 0)
    f_ = cs.get("flag_count",   0)
    h  = cs.get("hook_count",   0)
    total_sigs = cs.get("total_control_signals", b + f_ + h)

    chips = (
        f'<div class="sig-bar">'
        f'<span class="sig-chip sig-bridge">{b}× bridges</span>'
        f'<span class="sig-chip sig-flag">{f_}× flags</span>'
        f'<span class="sig-chip sig-hook">{h}× hooks</span>'
        f'</div>'
    )
    bridge_note = ""
    if b == 0 and f_ == 0:
        bridge_note = (
            "<p class='sub-note'>Bridging and flagging are the primary techniques "
            "for steering an interview toward your messages. The practice section "
            "below shows how to build these into your answers.</p>"
        )

    crutch_pct = openers.get("crutch_percentage", 0)
    by_opener  = openers.get("by_opener") or {}
    top_opener = next(iter(by_opener), None)
    top_count  = by_opener.get(top_opener, 0) if top_opener else 0

    wk_total = weak.get("total", 0)
    wk_rate  = round(wk_total / total_words * 100, 1)
    top_offs = list((weak.get("top_offenders") or {}).items())[:4]
    offenders = ",  ".join(f"<em>'{_e(t)}'</em> ({c}×)" for t, c in top_offs)

    excess_pct = conciseness.get("estimated_excess_pct", 0)
    ex_html = ""
    for ex in (conciseness.get("examples") or [])[:1]:
        orig = ex.get("original", "")
        sug  = ex.get("suggested", "")
        if orig and sug:
            ex_html = _verbatim_box(orig, sug)

    return (
        '<div class="scl-grid">'
        '<div class="scl-col">'
        '<h3 class="sub-h">Narrative control</h3>'
        f'<p>You used <strong>{total_sigs}</strong> control signal{"s" if total_sigs!=1 else ""} '
        f'across the session.</p>'
        + chips + bridge_note
        + '</div>'
        '<div class="scl-col">'
        '<h3 class="sub-h">Sentence openers</h3>'
        f'<p><strong>{crutch_pct}%</strong> of your sentences opened with a crutch word.'
        + (f"  The dominant opener was <em>'{_e(top_opener)}'</em> ({top_count} times)." if top_opener else "")
        + ' <span class="tgt">Target: under 20%.</span></p>'
        '<h3 class="sub-h" style="margin-top:16px">Language precision</h3>'
        f'<p>Weak and hedging words: <strong>{wk_rate}%</strong> of words — '
        f'<span class="tgt">target under 4%.</span></p>'
        + (f'<p class="offenders">{offenders}</p>' if offenders else "")
        + f'<p style="margin-top:10px">Conciseness: approximately <strong>{excess_pct}%</strong> '
        f'of words were unnecessary — <span class="tgt">target under 30%.</span></p>'
        + ex_html
        + '</div></div>'
    )


def _qa_table_html(qa: dict) -> str:
    """Question handling table from coaching narrative."""
    pairs   = qa.get("pairs") or []
    weakest = qa.get("weakest_exchange", "")
    if not pairs:
        return ""
    verdict_cls = {
        "answered": "", "partial": "vp", "deflected": "vd", "dodged": "vd",
    }
    rows = ""
    for p in pairs:
        v   = (p.get("verdict") or "").lower()
        vc  = verdict_cls.get(v, "")
        rows += (
            f"<tr><td class='qa-q'>{_e(p.get('question',''))}</td>"
            f"<td><span class='qa-v {vc}'>{_e(v.title() or '—')}</span></td>"
            f"<td>{_e(p.get('answer_length','—'))}</td>"
            f"<td>{_e(p.get('time_to_substance','—'))}</td></tr>"
        )
    focus = (
        f'<div class="qa-focus"><strong>The exchange to focus on:</strong> {_e(weakest)}</div>'
        if weakest else ""
    )
    return (
        f"<div class='tbl-scroll'><table class='qa-table'>"
        f"<thead><tr><th>Question</th><th>Verdict</th>"
        f"<th>Answer length</th><th>Time to substance</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>{focus}"
    )


def _tips_html(tips: list) -> str:
    if not tips:
        return ""
    items = ""
    for t in sorted(tips, key=lambda x: x.get("rank", 99)):
        items += (
            f'<li class="tip-item"><strong>{_e(t.get("tip",""))}</strong>'
            + (f'<span class="tip-rat">{_e(t.get("rationale",""))}</span>' if t.get("rationale") else "")
            + '</li>'
        )
    return (
        "<p class='section-intro'>Three areas, ranked by impact.</p>"
        f"<ol class='tips-ol'>{items}</ol>"
    )


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f0f4f8;color:#1e293b;font-size:15px;line-height:1.65}
header{background:#0A5C6B;color:#fff;padding:22px 32px 18px}
header h1{font-size:1.3rem;font-weight:700}
header .sub{opacity:.7;margin-top:5px;font-size:.88rem}
.container{max-width:920px;margin:0 auto;padding:20px 22px 40px}
.report-section{background:#fff;border-radius:10px;padding:22px 26px;
  margin-bottom:18px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.section-heading{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;
  color:#0A5C6B;border-bottom:2px solid #0CC0DF;padding-bottom:7px;
  margin-bottom:18px;font-weight:700}
.section-intro{font-size:.93rem;color:#475569;font-style:italic;margin-bottom:14px}
.prose{font-size:.95rem;color:#374151;line-height:1.7;margin-bottom:10px}
.prose:last-child{margin-bottom:0}

/* Scorecard */
.sc-table{width:100%;border-collapse:collapse;font-size:.9rem}
.sc-table th{text-align:left;font-size:.68rem;text-transform:uppercase;
  letter-spacing:.07em;color:#94a3b8;font-weight:700;padding:7px 10px;
  border-bottom:2px solid #e2e8f0}
.sc-table td{padding:10px;border-bottom:1px solid #f1f5f9;vertical-align:middle}
.sc-name{font-weight:600;color:#1e293b;min-width:130px}
.sc-result{color:#374151}
.sc-target{color:#94a3b8;font-size:.85rem}
.badge{font-size:.68rem;font-weight:700;padding:3px 10px;border-radius:999px;
  text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
.badge-good{background:#dcfce7;color:#166534}
.badge-watch{background:#fef3c7;color:#92400e}
.badge-develop{background:#fee2e2;color:#991b1b}
.badge-na{background:#f1f5f9;color:#94a3b8}
.caveat{font-size:.78rem;color:#94a3b8;font-style:italic;margin-top:10px}

/* Pace chart */
.chart-box{padding:6px 0}
.chart-legend{display:flex;gap:18px;margin-top:8px;flex-wrap:wrap}
.leg{font-size:.75rem;font-weight:600}
.leg-good{color:#0CC0DF}.leg-slow{color:#F59E0B}.leg-fast{color:#EF4444}

/* Pillars */
.pillar-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
@media(max-width:640px){.pillar-grid{grid-template-columns:1fr}}
.pillar-col{border:1px solid #e2e8f0;border-radius:8px;padding:14px 16px;
  border-top:4px solid #0A5C6B}
.pillar-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.pillar-name{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;
  font-weight:700;color:#334155}
.pill{font-size:.65rem;font-weight:700;padding:2px 9px;border-radius:999px}
.pill-good{background:#dcfce7;color:#166534}
.pill-watch{background:#fef3c7;color:#92400e}
.pill-develop{background:#fee2e2;color:#991b1b}
.pillar-verdict{font-size:.9rem;color:#374151;line-height:1.5}

/* Rocks */
.rocks-list{display:flex;flex-direction:column;gap:10px;margin-bottom:14px}
.rock-card{border-left:3px solid #cbd5e1;padding:10px 14px;
  background:#fafbfc;border-radius:0 7px 7px 0}
.rock-text{font-size:.95rem;color:#1e293b;margin-bottom:5px;font-weight:500}
.rock-meta{font-size:.82rem}
.rock-strong{color:#166534;font-weight:700}
.rock-weak{color:#92400e;font-weight:700}
.rock-note{color:#64748b}
.delta-box{background:#f0f9ff;border-left:4px solid #0CC0DF;padding:10px 14px;
  border-radius:0 7px 7px 0;font-size:.9rem;color:#0A5C6B;line-height:1.55}

/* Prose sections (presence, QH, language, composure, strengths, dev, practice) */
.prose-section{}
.verbatim-box{background:#f8fafc;border-radius:7px;padding:12px 14px;
  margin:12px 0;font-size:.85rem;border-left:3px solid #0CC0DF}
.verb-orig{color:#64748b;margin-bottom:5px}
.verb-arrow{color:#0CC0DF;font-weight:700;margin:4px 0}
.verb-tight{color:#0A5C6B;font-weight:600}
.verb-label{font-weight:700;color:#1e293b}
.dev-area{margin-bottom:18px;padding-bottom:18px;border-bottom:1px solid #f1f5f9}
.dev-area:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
.dev-num{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;
  color:#0CC0DF;margin-bottom:4px}
.strength-block{padding:10px 0 10px 16px;border-left:3px solid #22C55E;margin-bottom:12px}
.strength-block:last-child{margin-bottom:0}

/* Question handling */
.tbl-scroll{overflow-x:auto}
.qa-table{width:100%;border-collapse:collapse;font-size:.87rem}
.qa-table th{text-align:left;font-size:.68rem;text-transform:uppercase;letter-spacing:.06em;
  color:#94a3b8;font-weight:700;padding:7px 10px;border-bottom:1px solid #e2e8f0}
.qa-table td{padding:9px 10px;border-bottom:1px solid #f8fafc;vertical-align:top;
  color:#374151;line-height:1.4}
.qa-q{font-weight:500;color:#1e293b}
.qa-v{font-size:.7rem;font-weight:700;padding:2px 8px;border-radius:999px;
  background:#dcfce7;color:#166534;text-transform:capitalize;white-space:nowrap}
.vp{background:#fef3c7;color:#92400e;font-style:italic}
.vd{background:#fee2e2;color:#991b1b;font-weight:900}
.qa-focus{background:#fef3c7;border-left:3px solid #f59e0b;padding:9px 13px;
  border-radius:0 5px 5px 0;font-size:.85rem;color:#92400e;margin-top:12px;line-height:1.4}

/* Story / Control / Language data block */
.scl-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
@media(max-width:640px){.scl-grid{grid-template-columns:1fr}}
.sub-h{font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;
  color:#0A5C6B;font-weight:700;margin:14px 0 6px}
.sub-h:first-child{margin-top:0}
.sub-note{font-size:.83rem;color:#64748b;font-style:italic;margin-top:6px;line-height:1.5}
.tgt{color:#94a3b8;font-size:.87rem}
.sig-bar{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.sig-chip{font-size:.72rem;font-weight:700;padding:3px 10px;border-radius:999px}
.sig-bridge{background:#e0f7fa;color:#0A5C6B}
.sig-flag{background:#e0f2fe;color:#075985}
.sig-hook{background:#dcfce7;color:#166534}
.offenders{font-size:.85rem;color:#64748b;margin-top:4px}

/* Tips */
.tips-ol{list-style:none;padding:0;counter-reset:tip}
.tip-item{counter-increment:tip;position:relative;padding:12px 14px 12px 48px;
  border-bottom:1px solid #f1f5f9;font-size:.93rem;line-height:1.5}
.tip-item:last-child{border-bottom:none}
.tip-item::before{content:counter(tip);position:absolute;left:0;top:12px;
  width:30px;height:30px;background:#0CC0DF;color:#fff;border-radius:50%;
  display:flex;align-items:center;justify-content:center;font-size:.78rem;font-weight:700}
.tip-rat{display:block;color:#64748b;font-size:.85rem;margin-top:4px}

/* Closing */
.closing-text{font-size:.97rem;color:#374151;line-height:1.7}

footer{text-align:center;padding:18px;color:#94a3b8;font-size:.72rem}
"""


# ── Main renderer ─────────────────────────────────────────────────────────────

def render_report_html(
    metrics:       dict,
    narrative:     dict,
    client_report: dict | None,
    context:       dict,
    out_path:      str,
) -> str:
    candidate  = context.get("candidate", "")
    first_name = candidate.split()[0] if candidate else ""
    session    = context.get("session", "")
    date       = context.get("date", "")
    org        = context.get("organisation", "Fáilte Ireland")

    cr = client_report or {}

    def _cp(key: str) -> str:
        """Get and clean a client_report prose field."""
        return _clean_prose(cr.get(key, ""), first_name)

    sections = []

    # ── 1. DELIVERY SCORECARD ─────────────────────────────────────────────────
    sections.append(_section(
        "Your delivery at a glance",
        _delivery_scorecard(metrics),
        "scorecard",
    ))

    # ── 2. PACE CHART ─────────────────────────────────────────────────────────
    pace_text = narrative.get("pace_and_tone_narrative", "")
    if pace_text:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", pace_text.strip()) if s.strip()]
        summary = _to_second_person(_e(". ".join(sents[:2])), first_name)
        chart_note = f'<p class="caveat" style="margin-top:10px">{summary}</p>' if summary else ""
    else:
        chart_note = ""

    sections.append(_section(
        "Pace across the session",
        _pace_chart_html(metrics.get("pace") or {}) + chart_note,
        "pace",
    ))

    # ── 3. PILLAR ASSESSMENT ─────────────────────────────────────────────────
    verdicts = narrative.get("pillar_verdicts")
    if verdicts and isinstance(verdicts, dict):
        sections.append(_section(
            "Session assessment",
            _pillar_assessment(verdicts),
            "pillars",
        ))

    # ── 4. WHAT YOUR AUDIENCE TOOK AWAY ──────────────────────────────────────
    rocks = narrative.get("inferred_rocks") or []
    if rocks:
        sections.append(_section(
            "What your audience took away",
            _rocks_html(
                rocks,
                narrative.get("rock_strength") or [],
                narrative.get("rock_delta_note", ""),
                first_name,
            ),
            "rocks",
        ))

    # ── 5. PRESENCE AND AUTHORITY ─────────────────────────────────────────────
    presence_text = _cp("presence_and_authority")
    if not presence_text:
        # Fallback to coaching narrative tone + pace
        tone_n = narrative.get("tone_assessment", {}).get("narrative", "")
        pace_n = narrative.get("pace_and_tone_narrative", "")
        presence_text = _clean_prose(tone_n or pace_n, first_name)

    if presence_text:
        tone = narrative.get("tone_assessment") or {}
        descriptors = tone.get("descriptors") or []
        chips = "".join(
            f'<span style="background:#e0f7fa;color:#0A5C6B;font-size:.8rem;'
            f'font-weight:700;padding:4px 12px;border-radius:999px;'
            f'margin-right:6px;display:inline-block;margin-bottom:4px">{_e(d)}</span>'
            for d in descriptors
        )
        tone_chips = f'<div style="margin-bottom:12px">{chips}</div>' if chips else ""
        sections.append(_section(
            "Presence and authority",
            tone_chips + _prose_block(presence_text),
            "presence",
        ))

    # ── 6. QUESTION HANDLING ─────────────────────────────────────────────────
    qa = narrative.get("question_handling") or {}
    qa_prose = _cp("question_handling")
    qa_table = _qa_table_html(qa) if isinstance(qa, dict) and qa.get("pairs") else ""

    if qa_table or qa_prose:
        # Count intro
        n_q = len((qa.get("pairs") or []) if isinstance(qa, dict) else [])
        intro = f"<p class='section-intro'>{n_q} question{'s' if n_q != 1 else ''}. Here is how each landed.</p>" if n_q else ""
        sections.append(_section(
            "Question by question",
            intro + qa_table + ('<div style="height:14px"></div>' if qa_table and qa_prose else "") + _prose_block(qa_prose),
            "qa",
        ))

    # ── 7. LANGUAGE AND REGISTER ─────────────────────────────────────────────
    lang_text = _cp("language_and_register")
    lang_examples = cr.get("language_examples") or []
    # Also pull from conciseness_analysis if no client examples
    if not lang_examples:
        for ex in (narrative.get("conciseness_analysis", {}).get("examples") or []):
            lang_examples.append({
                "original": ex.get("original", ""),
                "tighter":  ex.get("suggested", ""),
            })

    if lang_text or lang_examples:
        examples_html = "".join(
            _verbatim_box(ex.get("original",""), ex.get("tighter", ex.get("suggested","")))
            for ex in lang_examples[:3]
            if ex.get("original")
        )
        sections.append(_section(
            "Language and register",
            _prose_block(lang_text) + examples_html,
            "language",
        ))

    # ── 8. COMPOSURE AND ADAPTABILITY ────────────────────────────────────────
    composure_text = _cp("composure_and_adaptability")
    if not composure_text:
        # Fallback: coaching moments as text
        moments = narrative.get("coaching_moments") or []
        if moments:
            lines = [f"[{m.get('timestamp_approx','?')}] {m.get('observation','')}"
                     for m in moments[:4]]
            composure_text = "  ".join(lines)
    if composure_text:
        sections.append(_section(
            "Composure and adaptability",
            _prose_block(composure_text),
            "composure",
        ))

    # ── 9. STORY, CONTROL AND LANGUAGE (data) ────────────────────────────────
    sections.append(_section(
        "Story, control and language — the numbers",
        _story_control_data(metrics, narrative),
        "scl",
    ))

    # ── 10. STANDOUT STRENGTHS ────────────────────────────────────────────────
    strengths_text = _cp("standout_strengths")
    if not strengths_text:
        # Fallback: narrative strengths list
        strengths_list = narrative.get("strengths") or []
        if strengths_list:
            strengths_text = "  ".join(strengths_list)
    if strengths_text:
        sections.append(_section(
            "Standout strengths",
            _prose_block(strengths_text),
            "strengths",
        ))

    # ── 11. PRIORITY DEVELOPMENT AREAS ───────────────────────────────────────
    dev_text = _cp("priority_development_areas")
    if dev_text:
        # Try to split numbered areas for cleaner rendering
        # Pattern: "1. Title: content\n\n2. Title: content" etc.
        numbered = re.split(r'\n{1,2}(?=\d+\.\s)', dev_text.strip())
        if len(numbered) > 1:
            blocks = ""
            for i, block in enumerate(numbered, 1):
                # Split heading from body at first sentence break
                lines = block.split(". ", 1)
                heading = lines[0].lstrip("0123456789. ")
                body = ". ".join(lines[1:]) if len(lines) > 1 else ""
                blocks += (
                    f'<div class="dev-area">'
                    f'<div class="dev-num">Focus area {i}</div>'
                    f'<p class="prose"><strong>{_e(heading)}</strong>'
                    + (f' — {_e(body)}' if body else "")
                    + f'</p></div>'
                )
            dev_html = blocks
        else:
            dev_html = _prose_block(dev_text)
        sections.append(_section(
            "Priority development areas",
            dev_html,
            "devarea",
        ))

    # ── 12. PRACTICE FRAMEWORK ────────────────────────────────────────────────
    practice_text = _cp("practice_framework")
    if practice_text:
        sections.append(_section(
            "Practice framework",
            _prose_block(practice_text),
            "practice",
        ))

    # ── 13. BEFORE YOUR NEXT SESSION (tips data) ──────────────────────────────
    tips = narrative.get("tips_for_success") or []
    if tips:
        sections.append(_section(
            "Before your next session",
            _tips_html(tips),
            "tips",
        ))

    # ── 14. CLOSING ASSESSMENT ────────────────────────────────────────────────
    closing_raw = cr.get("closing_assessment") or narrative.get("final_word", "")
    if closing_raw:
        closing_clean = _clean_closing(_clean_prose(closing_raw, first_name))
        if len(closing_clean.split()) < 15:
            closing_clean = _clean_closing(_clean_prose(
                narrative.get("overview", ""), first_name
            ))
        if closing_clean:
            sections.append(_section(
                "Closing assessment",
                f'<p class="closing-text">{_e(closing_clean)}</p>',
                "closing",
            ))

    # ── Assemble page ─────────────────────────────────────────────────────────
    body = "\n".join(sections)
    org_str = f' · {_e(org)}' if org else ""

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Delivery Feedback Report — {_e(candidate)}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>{CSS}</style>
</head>
<body>
<header>
  <h1>{_e(candidate)} — Delivery Feedback Report</h1>
  <p class="sub">{_e(session)}{org_str} &nbsp;·&nbsp; {_e(date)} &nbsp;·&nbsp; Reput8ion Dynamics</p>
</header>
<div class="container">
{body}
</div>
<footer>Prepared by James Dunny, Reput8ion Dynamics &nbsp;·&nbsp; {_e(date)}</footer>
</body>
</html>"""

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(page, encoding="utf-8")
    return out_path


# ── Entry point ───────────────────────────────────────────────────────────────

def _pick_folder() -> Path:
    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
        if not folder.is_absolute():
            folder = PROJECT_DIR / folder
        return folder
    subdirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir()]
    if not subdirs:
        raise SystemExit("No output folders found.")
    return max(subdirs, key=lambda d: d.stat().st_mtime)


def main() -> None:
    folder = _pick_folder()
    print(f"[HTML] Using {folder}")

    metrics_path   = folder / "metrics.json"
    narrative_path = folder / "narrative.json"
    cr_path        = folder / "client_report.json"

    if not metrics_path.exists():
        raise SystemExit(f"metrics.json not found in {folder}")
    if not narrative_path.exists():
        raise SystemExit(f"narrative.json not found in {folder}")

    metrics   = json.loads(metrics_path.read_text(encoding="utf-8"))
    narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
    cr        = json.loads(cr_path.read_text(encoding="utf-8")) if cr_path.exists() else None

    if cr:
        print(f"[HTML] client_report.json loaded — prose sections active")
    else:
        print(f"[HTML] No client_report.json — falling back to coaching narrative")

    name  = folder.name
    parts = name.rsplit("-", 1)
    candidate = parts[0].strip() if len(parts) == 2 else name
    date      = parts[1].strip() if len(parts) == 2 else ""

    context = {
        "candidate":    candidate,
        "session":      "Mock interview",
        "date":         date,
        "organisation": "",  # populated from session brief when available
    }

    out_path = str(folder / "report.html")
    render_report_html(
        metrics=metrics, narrative=narrative,
        client_report=cr, context=context, out_path=out_path,
    )
    print(f"[HTML] Written: {out_path}")
    webbrowser.open(Path(out_path).resolve().as_uri())
    print("[HTML] Opened in browser.")


if __name__ == "__main__":
    main()

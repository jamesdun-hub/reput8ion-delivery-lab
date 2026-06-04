"""
Coaching narrative generation via the Anthropic API.

Takes the metrics dict produced by metrics.compute_all_metrics(), a small
participant/session context, and optionally a prior-session metrics dict
for comparative framing. Returns a structured narrative the report
renderer drops into the .docx.

Design notes:

- The system prompt encodes James Dunny's coaching model (four quadrants,
  signature vocabulary, content-before-delivery causal logic) and the
  formal register rules for the leave-behind report.
- Output is forced into a tool-call shape, so the report renderer never
  has to parse free-form prose. Keys are stable.
- All numerical claims must originate in the metrics dict. The prompt
  forbids fabricating figures. If a metric is status="not_measured", the
  narrative says so rather than inventing one.
- An offline fallback runs when ANTHROPIC_API_KEY is unset, returning a
  deterministic placeholder so the rest of the pipeline can be exercised
  without burning API tokens.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------- Output contract ----------

NARRATIVE_TOOL_NAME = "submit_delivery_feedback"

# JSON Schema for the structured output the model must return.
# Keep in lockstep with what report.py and dashboard.py read.
# The schema is defined here (not in a config file) because it is a code
# contract between the AI and the renderers — changing it requires updating
# both sides simultaneously.
NARRATIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "inferred_rocks",
        "pillar_verdicts",
        "strengths",
        "overview",
        "pace_and_tone_narrative",
        "filler_and_weak_words_narrative",
        "control_and_structure_narrative",
        "tips_for_success",
        "final_word",
    ],
    "properties": {
        "inferred_rocks": {
            "type": "array",
            "minItems": 1,
            "maxItems": 4,
            "items": {"type": "string"},
            "description": (
                "The 2-3 key messages (rocks) that ACTUALLY LANDED — the messages "
                "a listener would take away, inferred from what the participant "
                "said with most repetition and conviction. This is perception, "
                "not stated intent. Quote or closely paraphrase the actual messages."
            ),
        },
        "rock_strength": {
            "type": "array",
            "description": (
                "Aligned one-to-one with inferred_rocks, same order. For each "
                "rock, how clearly it landed in the listener's ear."
            ),
            "items": {
                "type": "object",
                "required": ["strength", "note"],
                "properties": {
                    "strength": {
                        "type": "string",
                        "enum": ["strong", "weak"],
                        "description": "strong = landed clearly and was reinforced; weak = present but did not stick as a claim.",
                    },
                    "note": {
                        "type": "string",
                        "description": "One short clause on how it landed, e.g. 'reinforced across three answers' or 'said once, never anchored'.",
                    },
                },
            },
        },
        "rock_delta_note": {
            "type": "string",
            "description": (
                "One or two sentences naming the single most important "
                "message-discipline point: which message should have been the "
                "headline but landed weakly, or which unintended message "
                "registered. This is the coaching point for the debrief."
            ),
        },
        "pillar_verdicts": {
            "type": "object",
            "required": ["delivery", "story", "control"],
            "properties": {
                "delivery": {
                    "type": "object",
                    "required": ["status", "verdict"],
                    "properties": {
                        "status": {"type": "string", "enum": ["green", "watch", "red"]},
                        "verdict": {"type": "string", "description": "One sentence verdict on pace, pitch, pausing and energy."},
                    },
                },
                "story": {
                    "type": "object",
                    "required": ["status", "verdict"],
                    "properties": {
                        "status": {"type": "string", "enum": ["green", "watch", "red"]},
                        "verdict": {"type": "string", "description": "One sentence verdict on narrative structure, headline discipline and colour."},
                    },
                },
                "control": {
                    "type": "object",
                    "required": ["status", "verdict"],
                    "properties": {
                        "status": {"type": "string", "enum": ["green", "watch", "red"]},
                        "verdict": {"type": "string", "description": "One sentence verdict on bridging, flagging, hooking and staying on the rocks."},
                    },
                },
            },
        },
        "strengths": {
            "type": "array",
            "minItems": 2,
            "maxItems": 3,
            "items": {"type": "string"},
            "description": (
                "2-3 specific, evidenced strengths grounded in a metric or "
                "transcript moment. Not generic praise."
            ),
        },
        "overview": {
            "type": "string",
            "description": (
                "Two to four sentences. Warm, forward-looking, sets the frame. "
                "Names the participant by first name. No raw critique."
            ),
        },
        "pace_and_tone_narrative": {
            "type": "string",
            "description": (
                "One to two short paragraphs. Cite the measured net wpm and "
                "target band. Name pace spikes or drops by approximate timestamp. "
                "Cover pitch only if status is not 'not_measured'. Apply the "
                "causal logic: flat delivery is most often content insecurity."
            ),
        },
        "filler_and_weak_words_narrative": {
            "type": "string",
            "description": (
                "One to two short paragraphs. Name absolute filler counts by "
                "token, the per-100-words rate, and the top weak-word offenders. "
                "Frame the remedy as the pause, not faster speech."
            ),
        },
        "control_and_structure_narrative": {
            "type": "string",
            "description": (
                "One to two short paragraphs covering Story and Control. "
                "Cite sentence-opener crutch percentage with the main offender. "
                "Reference rocks, colour, bridging, flagging. Name where the "
                "candidate controlled the narrative and where they were pulled "
                "off their rocks."
            ),
        },
        "tone_assessment": {
            "type": "object",
            "required": ["descriptors", "narrative"],
            "properties": {
                "descriptors": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 6,
                    "items": {"type": "string"},
                    "description": "3-6 single-word tone descriptors from the allowed list.",
                },
                "narrative": {
                    "type": "string",
                    "description": (
                        "One paragraph describing tone. Cite specific timestamps and "
                        "short direct quotes. Match the style of the reference example."
                    ),
                },
            },
        },
        "coaching_moments": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {
                "type": "object",
                "required": ["timestamp_approx", "type", "observation"],
                "properties": {
                    "timestamp_approx": {
                        "type": "string",
                        "description": "Approximate timestamp e.g. '1:20' or '4:05'.",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["strength", "watch"],
                    },
                    "observation": {
                        "type": "string",
                        "description": (
                            "Specific qualitative observation about message discipline, "
                            "bridging, hooking, flagging, colour, or answer structure. "
                            "Not about pace or speed."
                        ),
                    },
                },
            },
        },
        "conciseness_analysis": {
            "type": "object",
            "required": ["estimated_excess_pct", "assessment", "examples"],
            "properties": {
                "estimated_excess_pct": {
                    "type": "number",
                    "description": "Estimated percentage of words that are excess. Target < 30.",
                },
                "assessment": {
                    "type": "string",
                    "description": "One paragraph on conciseness with specific examples.",
                },
                "examples": {
                    "type": "array",
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "required": ["original", "suggested"],
                        "properties": {
                            "original": {"type": "string", "description": "Verbose phrase from transcript."},
                            "suggested": {"type": "string", "description": "Tighter version."},
                        },
                    },
                },
            },
        },
        "pause_highlights": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {
                "type": "object",
                "required": ["timestamp_approx", "quote", "observation"],
                "properties": {
                    "timestamp_approx": {"type": "string"},
                    "quote": {
                        "type": "string",
                        "description": "5-10 word quote from the transcript at this moment.",
                    },
                    "observation": {
                        "type": "string",
                        "description": "What the pause achieved, or where one would have helped.",
                    },
                },
            },
        },
        "question_handling": {
            "type": "object",
            "description": (
                "Assessment of how the participant handled each interviewer "
                "question. Only populate if interviewer turns are provided in "
                "the input. The core media-training skill: did the answer meet "
                "the question, was it the right length, did they accept or "
                "challenge a loaded premise."
            ),
            "properties": {
                "pairs": {
                    "type": "array",
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "required": ["question", "verdict", "premise_handling"],
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Short form of the interviewer's question.",
                            },
                            "verdict": {
                                "type": "string",
                                "enum": ["answered", "partial", "deflected", "dodged"],
                                "description": "Did the answer address the actual question?",
                            },
                            "answer_length": {
                                "type": "string",
                                "description": "Approx words and seconds, e.g. '~180 words · 1:10'. Flag if long enough to be cut or misquoted.",
                            },
                            "time_to_substance": {
                                "type": "string",
                                "description": "How long before they reached the point, e.g. '~6s'.",
                            },
                            "premise_handling": {
                                "type": "string",
                                "description": "Whether they accepted or challenged any loaded/hostile premise, and how cleanly.",
                            },
                        },
                    },
                },
                "weakest_exchange": {
                    "type": "string",
                    "description": "One or two sentences naming the weakest exchange and what to drill.",
                },
            },
        },
        "tips_for_success": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": ["rank", "tip", "rationale"],
                "properties": {
                    "rank": {"type": "integer", "minimum": 1, "maximum": 3},
                    "tip": {
                        "type": "string",
                        "description": "Short imperative, one sentence. Concrete and practiceable.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "One or two sentences tied to a measured number or named concept.",
                    },
                },
            },
        },
        "final_word": {
            "type": "string",
            "description": (
                "Two to four sentences. Encouraging, forward-looking. "
                "Ends on practice — skills decay without use."
            ),
        },
    },
}


# ---------- Client report schema ----------
# Separate schema for the 7-section client-facing Word document.
# The coaching dashboard uses NARRATIVE_SCHEMA above; the client report
# uses this one. They are generated by different API calls.

CLIENT_REPORT_TOOL_NAME = "submit_client_report"

CLIENT_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "executive_summary",
        "the_standard",
        "message_architecture",
        "presence_and_authority",
        "question_handling",
        "language_and_register",
        "composure_and_adaptability",
        "standout_strengths",
        "priority_development_areas",
        "practice_framework",
        "closing_assessment",
    ],
    "properties": {
        "executive_summary": {
            "type": "string",
            "description": (
                "Section 1. Half page. Opens with the trainer's overall verdict — "
                "a clear statement of where this participant stands as a media "
                "performer and what the session demonstrated. Two or three sentences "
                "on what this report will help the participant do. No performance "
                "label. No opening with 'Your session showcased...'."
            ),
        },
        "the_standard": {
            "type": "string",
            "description": (
                "Section 2. One page. What world-class media performance looks like "
                "at this participant's level and in their specific role. Reference "
                "the participant's role and sector. Not generic."
            ),
        },
        "message_architecture": {
            "type": "string",
            "description": (
                "Section 3.1. Observation grounded in specific transcript evidence "
                "followed by development insight. Prose only, no bullets. Incorporate "
                "the trainer's rock framework at the weight the trainer gave it."
            ),
        },
        "presence_and_authority": {
            "type": "string",
            "description": (
                "Section 3.2. Delivery confidence, pace, vocal range, warmth. "
                "Lead with observation, not numbers. Cite pace/pause data only where "
                "the trainer cited them. Use the trainer's specific tone descriptors."
            ),
        },
        "question_handling": {
            "type": "string",
            "description": (
                "Section 3.3. How the participant received and responded to each "
                "question. Did they follow the interviewer's framing or bring the "
                "conversation where they wanted it? Include the rhetorical question "
                "technique if the trainer praised it. Prose only."
            ),
        },
        "language_and_register": {
            "type": "string",
            "description": (
                "Section 3.4. Only observations the trainer raised. If filler words "
                "were raised, use the trainer's explanation and technique. Do not add "
                "sentence-opener or hedging-word analysis if the trainer did not raise "
                "it. Reference the language_examples table if populated."
            ),
        },
        "language_examples": {
            "type": "array",
            "description": (
                "Optional. Verbatim-versus-tighter pairs for Section 3.4. Only include "
                "if the trainer raised jargon or clarity. Maximum 3 pairs."
            ),
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": ["original", "tighter"],
                "properties": {
                    "original": {
                        "type": "string",
                        "description": "The verbose phrase from the transcript.",
                    },
                    "tighter": {
                        "type": "string",
                        "description": "The cleaner version.",
                    },
                },
            },
        },
        "composure_and_adaptability": {
            "type": "string",
            "description": (
                "Section 3.5. How performance evolved across the session. Reference "
                "the trainer's observation about development between sessions if "
                "relevant. Include the trainer's note about colour sustaining and "
                "any development note about the second half."
            ),
        },
        "standout_strengths": {
            "type": "string",
            "description": (
                "Section 4. Capabilities the trainer praised — only what the trainer "
                "called out. Specific moments and the trainer's own language. Explain "
                "why each matters in real media contexts. Prose only."
            ),
        },
        "priority_development_areas": {
            "type": "string",
            "description": (
                "Section 5. Only areas the trainer raised, in the trainer's order of "
                "emphasis. For each: what was observed, why it matters at this level "
                "(trainer's explanation), and the technique the trainer prescribed. "
                "Frame as targeted development focus. Never use 'weakness'. Include "
                "the trainer's stories and analogies. Prose only."
            ),
        },
        "practice_framework": {
            "type": "string",
            "description": (
                "Section 6. Draw from the trainer's prescriptions: rocks framework, "
                "simplicity principle, audience-specific message sets, passive "
                "preparation. Everything must trace back to something the trainer "
                "said. Not generic media training advice."
            ),
        },
        "closing_assessment": {
            "type": "string",
            "description": (
                "Section 7. Written directly to the participant. Reflects the "
                "trainer's closing verdict and confidence level. If the trainer "
                "expressed broadcast-readiness or significant progress, say so. "
                "Ground it in something specific. Forward-looking, consistent with "
                "the trainer's tone."
            ),
        },
    },
}


# ---------- System prompt loader ----------
# The prompt lives in prompts/coach.md so James can edit the framework,
# style rules, and assessment criteria without touching Python.

_PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "coach.md"
_CLIENT_REPORT_PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "client_report.md"


def _load_system_prompt(config: dict | None = None) -> str:
    """Load the coaching system prompt from the configured file path.

    Falls back to the default prompts/coach.md if no path is configured.
    Raises a clear FileNotFoundError so a missing prompt is never silent.
    """
    if config:
        rel = config.get("coach", {}).get("prompt_file", "prompts/coach.md")
        prompt_path = Path(__file__).parent.parent / rel
    else:
        prompt_path = _PROMPT_FILE

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Coaching prompt not found at {prompt_path}.\n"
            "Edit config.yaml coach.prompt_file to point to your prompt, "
            "or restore prompts/coach.md."
        )
    return prompt_path.read_text(encoding="utf-8")


# ---------- Coach call ----------

@dataclass
class CoachContext:
    candidate_name: str
    session_label: str
    session_date: str  # e.g. "1 June 2026"


def _build_user_message(
    metrics: dict,
    context: CoachContext,
    prior_metrics: dict | None,
    transcript_text: str | None,
    coach_notes_text: str | None = None,
    qa_transcript_text: str | None = None,
) -> str:
    """Structured payload for the model. Includes transcript text (with
    time markers every 30s) so the AI can cite specific moments."""
    payload = {
        "participant": {
            "first_name": context.candidate_name.split()[0],
            "full_name": context.candidate_name,
            "session_label": context.session_label,
            "session_date": context.session_date,
        },
        "metrics": metrics,
        "prior_metrics": prior_metrics,
    }
    msg = (
        "Here is the measured session data and the timestamped transcript. "
        "Use the metrics object as the single source of every number you cite. "
        "Use the transcript to identify specific moments, timestamps and quotes "
        "for tone_assessment, coaching_moments, conciseness_analysis and "
        "pause_highlights. Call the submit_delivery_feedback tool.\n\n"
        f"```json\n{json.dumps(payload, indent=2)}\n```"
    )
    if transcript_text:
        msg += (
            "\n\n## Timestamped transcript (interviewee only)\n\n"
            + transcript_text
        )
    if qa_transcript_text:
        msg += (
            "\n\n## Interviewer questions paired with answers (both speakers)\n\n"
            "Use this to populate question_handling: for each interviewer "
            "question, judge whether the answer addressed it, its length, time "
            "to substance, and whether a loaded premise was accepted or "
            "challenged. Be a fair but exacting judge — this is for the coach's "
            "review, not the participant.\n\n"
            + qa_transcript_text
        )
    if coach_notes_text:
        msg += (
            "\n\n## Coach's spoken observations\n\n"
            "The following is a transcript of the coach's commentary recorded "
            "during this session. Incorporate these insights into all narrative "
            "sections. Use the coach's own framing and language where it is "
            "natural to do so. Let specific observations shape the coaching_moments, "
            "tips_for_success and final_word in particular.\n\n"
            + coach_notes_text
        )
    return msg


def generate_coaching_narrative(
    metrics: dict,
    context: CoachContext,
    config: dict,
    prior_metrics: dict | None = None,
    transcript_text: str | None = None,
    coach_notes_text: str | None = None,
    qa_transcript_text: str | None = None,
) -> dict:
    """Generate the coaching narrative sections. Returns a dict matching
    NARRATIVE_SCHEMA. Falls back to a deterministic placeholder if no
    OPENAI_API_KEY is set, so the rest of the pipeline can be tested
    without API access."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _offline_placeholder(metrics, context)

    # Import inside the function so the metrics engine and tests don't
    # transitively require the OpenAI SDK.
    from openai import OpenAI  # type: ignore

    coach_cfg = config.get("coach", {})
    model = coach_cfg.get("model", "gpt-4o")
    max_tokens = int(coach_cfg.get("max_tokens", 2400))
    temperature = float(coach_cfg.get("temperature", 0.4))

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        tools=[{
            "type": "function",
            "function": {
                "name": NARRATIVE_TOOL_NAME,
                "description": (
                    "Submit the structured narrative for the delivery feedback report."
                ),
                "parameters": NARRATIVE_SCHEMA,
            }
        }],
        tool_choice={"type": "function", "function": {"name": NARRATIVE_TOOL_NAME}},
        messages=[
            {"role": "system", "content": _load_system_prompt(config)},
            {"role": "user", "content": _build_user_message(metrics, context, prior_metrics, transcript_text, coach_notes_text, qa_transcript_text)},
        ],
    )

    for tool_call in response.choices[0].message.tool_calls:
        if tool_call.function.name == NARRATIVE_TOOL_NAME:
            return json.loads(tool_call.function.arguments)

    raise RuntimeError(
        "OpenAI API did not return a function call for "
        f"{NARRATIVE_TOOL_NAME}. Raw stop reason: {response.stop_reason}"
    )


# ---------- Offline fallback ----------

def _offline_placeholder(metrics: dict, context: CoachContext) -> dict:
    """Deterministic placeholder so the report can render without an API
    key. Surfaces the most important raw numbers so it is obvious which
    sections still need the real coaching narrative."""
    first = context.candidate_name.split()[0]
    pace = metrics["pace"]
    fillers = metrics["fillers"]
    weak = metrics["weak_words"]
    openers = metrics["sentence_openers"]

    filler_summary = ", ".join(
        f"{n} {tok}" for tok, n in fillers["by_token"].items()
    ) or "no filler tokens detected"

    return {
        "inferred_rocks": ["[OFFLINE] Key messages inferred by gpt-4o when OPENAI_API_KEY is set."],
        "tone_assessment": {
            "descriptors": ["[offline]"],
            "narrative": "[OFFLINE] Tone assessment requires gpt-4o.",
        },
        "coaching_moments": [
            {"timestamp_approx": "—", "type": "watch",
             "observation": "[OFFLINE] Coaching moments require gpt-4o — set OPENAI_API_KEY."},
        ],
        "conciseness_analysis": {
            "estimated_excess_pct": 0,
            "assessment": "[OFFLINE] Conciseness analysis requires gpt-4o.",
            "examples": [],
        },
        "pause_highlights": [
            {"timestamp_approx": "—", "quote": "—",
             "observation": "[OFFLINE] Pause highlights require gpt-4o."},
        ],
        "pillar_verdicts": {
            "delivery": {"status": "watch", "verdict": f"Pace {pace['net_wpm']} wpm against target {pace['target_band']}. Status: {pace['status']}."},
            "story": {"status": "watch", "verdict": "Story assessment requires gpt-4o — set OPENAI_API_KEY."},
            "control": {"status": "watch", "verdict": "Control assessment requires gpt-4o — set OPENAI_API_KEY."},
        },
        "strengths": [
            "[OFFLINE] Strengths will be identified by gpt-4o when OPENAI_API_KEY is set.",
        ],
        "overview": (
            f"{first}, this report is a placeholder generated without the "
            "coaching model. The hard metrics in the table are real; the "
            "narrative will be written by gpt-4o when OPENAI_API_KEY is set."
        ),
        "pace_and_tone_narrative": (
            f"You delivered at {pace['net_wpm']} words per minute against a "
            f"target band of {pace['target_band']}. Status: {pace['status']}."
        ),
        "filler_and_weak_words_narrative": (
            f"Filler total: {fillers['total']} ({fillers['per_100_words']} "
            f"per 100 words). Breakdown: {filler_summary}. Weak words total: "
            f"{weak['total']} ({weak['per_100_words']} per 100 words)."
        ),
        "control_and_structure_narrative": (
            f"{openers['crutch_percentage']}% of sentences began with a "
            f"crutch opener. Most frequent: "
            f"{next(iter(openers['by_opener']), 'none')}."
        ),
        "tips_for_success": [
            {"rank": 1, "tip": "Replace the next filler with a half-second pause.",
             "rationale": "A deliberate silence reads as composure. A filler reads as hesitation."},
            {"rank": 2, "tip": "Open with the headline, not a crutch word.",
             "rationale": f"{openers['crutch_percentage']}% of sentences currently start on a crutch."},
            {"rank": 3, "tip": "Practise the three Rocks until they land cold.",
             "rationale": "Skills decay fast without use; content security drives delivery."},
        ],
        "final_word": (
            f"{first}, the trajectory is positive. Keep practising. "
            "Communication is the message received, not the message sent."
        ),
    }


# ---------- Client report generation ----------

def _load_client_report_prompt() -> str:
    """Load the client report system prompt from prompts/client_report.md."""
    if not _CLIENT_REPORT_PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"Client report prompt not found at {_CLIENT_REPORT_PROMPT_FILE}.\n"
            "Restore prompts/client_report.md."
        )
    return _CLIENT_REPORT_PROMPT_FILE.read_text(encoding="utf-8")


def _build_client_report_user_message(
    metrics: dict,
    context: CoachContext,
    coaching_narrative: dict,
    interview_transcript_text: str,
    coach_notes_text: str | None,
) -> str:
    """User-message payload for the client report generation.

    The trainer feedback transcript is the primary input and is placed
    prominently. The coaching narrative and metrics are supporting context.
    """
    payload = {
        "participant": {
            "first_name": context.candidate_name.split()[0],
            "full_name": context.candidate_name,
            "session_label": context.session_label,
            "session_date": context.session_date,
        },
        "metrics": metrics,
        "supporting_narrative": coaching_narrative,
    }

    msg = (
        "The following inputs are provided to produce the client report. "
        "The trainer feedback transcript is the PRIMARY input — read it "
        "first and extract the trainer's feedback framework before writing "
        "anything. Call the submit_client_report tool.\n\n"
        f"```json\n{json.dumps(payload, indent=2)}\n```"
    )

    if coach_notes_text:
        msg += (
            "\n\n## TRAINER FEEDBACK TRANSCRIPT (PRIMARY INPUT)\n\n"
            "Read this in full before writing. Extract praise, development "
            "areas, overall verdict and trainer language as instructed.\n\n"
            + coach_notes_text
        )
    else:
        msg += (
            "\n\n## TRAINER FEEDBACK TRANSCRIPT\n\n"
            "[No trainer commentary provided — generate the report from the "
            "interview transcript and supporting narrative only. Apply the "
            "same alignment rules to the supporting narrative.]"
        )

    if interview_transcript_text:
        msg += (
            "\n\n## MOCK INTERVIEW TRANSCRIPT (both speakers)\n\n"
            + interview_transcript_text
        )

    return msg


def generate_client_report_narrative(
    metrics: dict,
    context: CoachContext,
    config: dict,
    coaching_narrative: dict,
    interview_transcript_text: str,
    coach_notes_text: str | None = None,
) -> dict:
    """Generate the 7-section client report narrative.

    Returns a dict matching CLIENT_REPORT_SCHEMA. This is a separate API
    call from generate_coaching_narrative — the coaching dashboard and the
    client report are produced by different prompts with different schemas.

    Falls back to a placeholder when OPENAI_API_KEY is not set.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _offline_client_report_placeholder(context)

    from openai import OpenAI  # type: ignore

    coach_cfg = config.get("coach", {})
    model = coach_cfg.get("model", "gpt-4o")
    # Client report is substantially longer than the coaching narrative
    max_tokens = int(coach_cfg.get("client_report_max_tokens", 6000))
    temperature = float(coach_cfg.get("temperature", 0.4))

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        tools=[{
            "type": "function",
            "function": {
                "name": CLIENT_REPORT_TOOL_NAME,
                "description": "Submit the structured client report sections.",
                "parameters": CLIENT_REPORT_SCHEMA,
            }
        }],
        tool_choice={"type": "function", "function": {"name": CLIENT_REPORT_TOOL_NAME}},
        messages=[
            {"role": "system", "content": _load_client_report_prompt()},
            {
                "role": "user",
                "content": _build_client_report_user_message(
                    metrics, context, coaching_narrative,
                    interview_transcript_text, coach_notes_text,
                ),
            },
        ],
    )

    for tool_call in response.choices[0].message.tool_calls:
        if tool_call.function.name == CLIENT_REPORT_TOOL_NAME:
            return json.loads(tool_call.function.arguments)

    raise RuntimeError(
        "OpenAI API did not return a function call for "
        f"{CLIENT_REPORT_TOOL_NAME}."
    )


def _offline_client_report_placeholder(context: CoachContext) -> dict:
    """Placeholder returned when OPENAI_API_KEY is not set."""
    first = context.candidate_name.split()[0]
    stub = (
        f"[OFFLINE] Requires OPENAI_API_KEY. "
        f"Session: {context.session_label}, {context.session_date}."
    )
    return {k: (f"{first}, {stub}" if k == "executive_summary" else stub)
            for k in CLIENT_REPORT_SCHEMA["required"]}

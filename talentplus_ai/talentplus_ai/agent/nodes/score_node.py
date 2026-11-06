"""
Node 4 — Score
Sends all gathered evidence to Claude Sonnet 4.5 and gets back a
guaranteed schema-valid evaluation via Anthropic Structured Outputs.

Returns:
  - overall score (0-100)
  - subscores: technical, culture, experience
  - detailed reasoning
  - candidate label (Hidden Gem / Strong Match / Needs Development / Not a Fit)
  - strengths, weaknesses, recommendation

Changes from original:
  - Uses client.beta.messages.create() + betas=["structured-outputs-2025-11-13"]
    → No markdown fence stripping. No json.loads() guesswork.
  - Uses claude-sonnet-4-5 (the only model that supports Structured Outputs)
  - SCORING_SYSTEM_PROMPT moved to core/prompts/scoring_prompt.py
  - Removed unused EvaluationError import

LangGraph contract:
  Input:  AgentState (with resume_text, github_evidence, gap_analysis)
  Output: AgentState (with score, subscores, reasoning, candidate_label)
"""

import json
import logging
from django.conf import settings
from anthropic import Anthropic

from talentplus_ai.agent.state import AgentState
from talentplus_ai.core.prompts.scoring_prompt import SCORING_SYSTEM_PROMPT, SCORING_JSON_SCHEMA

logger = logging.getLogger(__name__)

# Must match the model used in pdf_parser.py — only claude-sonnet-4-5
# and claude-opus-4-1 support the Structured Outputs beta.
_SCORING_MODEL = "claude-sonnet-4-5"


def _build_user_prompt(state: AgentState) -> str:
    """Assembles the evidence payload sent to Claude for scoring."""
    resume_text     = (state.get("resume_text") or "")[:4000]
    github_evidence = json.dumps(state.get("github_evidence") or {}, indent=2)[:3000]
    gap_analysis    = json.dumps(state.get("gap_analysis") or {}, indent=2)[:2000]

    return (
        "## CANDIDATE RESUME\n"
        f"{resume_text}\n\n"
        "## GITHUB EVIDENCE\n"
        f"{github_evidence}\n\n"
        "## GAP ANALYSIS (vs. open roles)\n"
        f"{gap_analysis}\n\n"
        "Please evaluate this candidate now."
    )


def score_node(state: AgentState) -> AgentState:
    """
    Calls Claude Sonnet 4.5 via Anthropic Structured Outputs and
    returns scores + reasoning guaranteed to match SCORING_JSON_SCHEMA.
    """
    logger.info("[score_node] Starting for candidate %s", state["candidate_id"])

    trace = list(state.get("trace_log", []))
    trace.append({
        "step": "Score",
        "message": "Claude is synthesising evidence and generating a score...",
        "status": "running",
    })

    try:
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        message = client.beta.messages.create(
            model=_SCORING_MODEL,
            max_tokens=2000,
            betas=["structured-outputs-2025-11-13"],
            system=SCORING_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": _build_user_prompt(state)}
            ],
            output_format={
                "type": "json_schema",
                "schema": SCORING_JSON_SCHEMA,
            },
        )

        # Structured Outputs guarantees content[0].text is valid JSON
        # matching SCORING_JSON_SCHEMA — no stripping or parsing fallback needed.
        result = json.loads(message.content[0].text)

        overall_score    = int(result["overall_score"])
        technical_score  = int(result["technical_score"])
        culture_score    = int(result["culture_score"])
        experience_score = int(result["experience_score"])
        candidate_label  = result["candidate_label"]
        reasoning        = result["reasoning"]
        strengths        = result.get("strengths", [])
        weaknesses       = result.get("weaknesses", [])
        recommendation   = result.get("recommendation", "")

        # Append strengths/weaknesses inline with the reasoning for the dashboard
        enhanced_reasoning = (
            f"{reasoning}\n\n"
            f"Strengths: {', '.join(strengths)}\n"
            f"Weaknesses: {', '.join(weaknesses)}"
        )

        summary = f"Score: {overall_score}/100. Label: {candidate_label}. {recommendation}"
        trace[-1] = {"step": "Score", "message": summary, "status": "done"}
        logger.info("[score_node] %s", summary)

        return {
            **state,
            "score":            overall_score,
            "technical_score":  technical_score,
            "culture_score":    culture_score,
            "experience_score": experience_score,
            "reasoning":        enhanced_reasoning,
            "candidate_label":  candidate_label,
            "trace_log":        trace,
        }

    except Exception as exc:
        error_msg = f"Score node failed: {exc}"
        logger.error("[score_node] %s", error_msg)
        trace[-1] = {"step": "Score", "message": error_msg, "status": "error"}
        return {
            **state,
            "score":     0,
            "reasoning": error_msg,
            "trace_log": trace,
            "error":     error_msg,
        }
"""
LangGraph Workflow — TalentPulse Screening Pipeline

Screening Score Routing:
  ┌─────────────────────────────────────────────────────────────────┐
  │  score >= 60  →  voice_node schedules AI voice interview        │
  │                  (email_node is NOT invoked at this stage;      │
  │                   the invite email is sent by voice tasks.py)   │
  │                                                                 │
  │  50 <= score < 60  →  borderline / HITL (on hold)              │
  │                        graph ends; human reviews manually       │
  │                                                                 │
  │  score < 50  →  email_node sends rejection email immediately    │
  └─────────────────────────────────────────────────────────────────┘

After the voice interview completes (async, via Celery):
  voice composite score >= VOICE_PASS_THRESHOLD (default 70)
    → tasks.py sends "selected for next round" email

Graph edges:
  parse_node → research_node → contextualize_node → scoring (score_node)
                                                         ↓
                                                      db_node
                                                         ↓
                                                    voice_node
                                                         ↓  (conditional)
                                          score >= 60  →  END
                                                           (voice invite sent async)
                                          50–59        →  END
                                                           (borderline, no action)
                                          score < 50   →  email_node → END
                                                           (rejection email)

Changes from original:
  - Removed VOICE_FOR_STRONG_CANDIDATES logic entirely.
  - score > 70 no longer routes to email_node for a "screening invitation" —
    those candidates are now routed through voice_node just like 60–70.
  - email_node is now ONLY responsible for rejection emails (score < 50).
  - Borderline threshold changed from 60–70 to 50–59.
  - run_screening() signature unchanged.
"""

import logging
from langgraph.graph import StateGraph, END

from talentplus_ai.agent.state import AgentState
from talentplus_ai.agent.nodes.parse_node import parse_node
from talentplus_ai.agent.nodes.research_node import research_node
from talentplus_ai.agent.nodes.contextualize_node import contextualize_node
from talentplus_ai.agent.nodes.score_node import score_node
from talentplus_ai.agent.nodes.db_node import db_node
from talentplus_ai.agent.nodes.voice_node import voice_node
from talentplus_ai.agent.nodes.email_node import email_node

logger = logging.getLogger(__name__)


def route_after_voice(state: AgentState) -> str:
    """
    Conditional edge after voice_node.

    Score routing:
      >= 60  → END  (voice interview already scheduled by voice_node;
                      invite email is sent asynchronously by voice tasks)
      50–59  → END  (borderline — HITL path, currently on hold; no action)
      < 50   → "email"  (immediate rejection email via email_node)

    On pipeline error → END (skip email to avoid confusing the candidate).
    """
    score = state.get("score", 0)
    error = state.get("error")

    if error:
        logger.warning("[graph] Pipeline error detected. Skipping email. Error: %s", error)
        return "end"

    if score < 50:
        logger.info("[graph] Score %d < 50. Routing to rejection email.", score)
        return "email"

    if 50 <= score < 60:
        logger.info(
            "[graph] Score %d is borderline (50–59). Queued for human review (HITL on hold).",
            score,
        )
        return "end"

    # score >= 60 — voice interview scheduled by voice_node
    logger.info(
        "[graph] Score %d >= 60. Voice screening scheduled. Graph ends here; "
        "invite email is sent asynchronously.",
        score,
    )
    return "end"


def build_screening_graph() -> StateGraph:
    """
    Constructs and compiles the TalentPulse LangGraph workflow.
    Returns a compiled graph ready to invoke.
    """
    workflow = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────
    workflow.add_node("parse", parse_node)
    workflow.add_node("research", research_node)
    workflow.add_node("contextualize", contextualize_node)
    workflow.add_node("scoring", score_node)
    workflow.add_node("persist", db_node)
    workflow.add_node("voice", voice_node)
    workflow.add_node("rejection_email", email_node)

    # ── Define edges ───────────────────────────────────────────
    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "research")
    workflow.add_edge("research", "contextualize")
    workflow.add_edge("contextualize", "scoring")
    workflow.add_edge("scoring", "persist")
    workflow.add_edge("persist", "voice")

    # Conditional edge after voice_node
    workflow.add_conditional_edges(
        "voice",
        route_after_voice,
        {
            "email": "rejection_email",
            "end": END,
        },
    )

    workflow.add_edge("rejection_email", END)

    return workflow.compile()


# Module-level compiled graph (singleton — compiled once on import)
screening_graph = build_screening_graph()


def run_screening(candidate_id: str, evaluation_id: str) -> AgentState:
    """
    Entry point called by the Celery task (tasks.py).
    Initialises AgentState and runs the full LangGraph workflow.

    Args:
        candidate_id:  UUID of the Candidate row (used by parse_node to
                       load structured profile data from the DB).
        evaluation_id: UUID of the specific CandidateEvaluation row to
                       update (used by db_node to write results back to
                       the correct row — critical now that a candidate can
                       have multiple evaluations, one per target role).
    """
    logger.info(
        "[graph] Starting screening pipeline — candidate: %s, evaluation: %s",
        candidate_id,
        evaluation_id,
    )

    initial_state: AgentState = {
        "candidate_id":    candidate_id,
        "evaluation_id":   evaluation_id,
        # parse_node will populate these from DB
        "name":            "",
        "email":           "",
        "skills":          [],
        "github_url":      None,
        "github_username": None,
        "portfolio_url":   None,
        "summary":         None,
        "experience":      None,
        "projects":        None,
        "education":       None,
        # downstream nodes populate the rest
        "github_evidence": None,
        "gap_analysis":    None,
        "score":           0,
        "technical_score": 0,
        "culture_score":   0,
        "experience_score": 0,
        "reasoning":       "",
        "candidate_label": "",
        "email_status":    "skipped",
        "trace_log":       [],
        "error":           None,
        "voice_interview_id":        None,
        "voice_interview_scheduled": False,
    }

    final_state = screening_graph.invoke(initial_state)

    logger.info(
        "[graph] Screening complete — candidate: %s, score: %s, label: %s, email: %s",
        candidate_id,
        final_state.get("score"),
        final_state.get("candidate_label"),
        final_state.get("email_status"),
    )

    return final_state
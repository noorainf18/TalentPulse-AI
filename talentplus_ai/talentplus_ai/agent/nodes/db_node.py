"""
Node 5 — Persist
Writes the completed evaluation to the CandidateEvaluation table.

Status determination (aligned with new score routing):
  score >= 60  → "voice_scheduled"   (AI voice interview will be set up asynchronously)
  50–59        → "borderline"        (HITL queue — on hold)
  score < 50   → "rejected"          (rejection email sent by email_node)

Changes from original:
  - _determine_status thresholds updated:
      Old: score > 70 → "screening_sent", score < 60 → "rejected", else "borderline"
      New: score >= 60 → "voice_scheduled", 50–59 → "borderline", < 50 → "rejected"
  - The "screening_sent" status is removed; for accepted candidates the flow
    now goes through the voice pipeline. The evaluation status is updated
    again by voice/tasks.py (to "voice_invited", "voice_completed", etc.)
    as the voice lifecycle progresses.

LangGraph contract:
  Input:  AgentState (evaluation_id, score, subscores, reasoning, evidence, gap)
  Output: AgentState (trace_log updated; evaluation row fully written)
"""

import logging
from talentplus_ai.agent.state import AgentState

logger = logging.getLogger(__name__)


def _determine_status(score: int) -> str:
    """
    Map numeric score to an evaluation status string.

    score >= 60  → "voice_scheduled"
        The candidate meets the threshold for AI voice screening.
        voice_node will enqueue schedule_voice_screen after this node runs.

    50 <= score < 60  → "borderline"
        Insufficient signal for automatic accept or reject.
        Queued for human-in-the-loop review (HITL path — currently on hold).

    score < 50  → "rejected"
        Clear reject; email_node will send a feedback-rich rejection email.
    """
    if score >= 60:
        return "voice_scheduled"
    if score < 50:
        return "rejected"
    return "borderline"


def db_node(state: AgentState) -> AgentState:
    """
    Fetches the pre-created CandidateEvaluation by evaluation_id and
    writes all agent outputs into it.
    """
    candidate_id  = state["candidate_id"]
    evaluation_id = state["evaluation_id"]

    logger.info(
        "[db_node] Persisting evaluation %s for candidate %s",
        evaluation_id,
        candidate_id,
    )

    trace = list(state.get("trace_log", []))
    trace.append({
        "step":    "Save",
        "message": "Saving evaluation to database...",
        "status":  "running",
    })

    try:
        from talentplus_ai.candidates.models import CandidateEvaluation

        # ── Fetch the EXACT evaluation row by PK ───────────────────────
        # views.py created this row before dispatching the Celery task.
        # We must never get_or_create here — doing so would ignore the
        # target_role / resume_hash that were set at upload time.
        try:
            evaluation = CandidateEvaluation.objects.get(id=evaluation_id)
        except CandidateEvaluation.DoesNotExist:
            raise RuntimeError(
                f"CandidateEvaluation {evaluation_id} not found. "
                "This should never happen — views.py must create the row before "
                "dispatching trigger_screening."
            )

        # ── Write all agent outputs ─────────────────────────────────────
        evaluation.score            = state.get("score", 0)
        evaluation.technical_score  = state.get("technical_score", 0)
        evaluation.culture_score    = state.get("culture_score", 0)
        evaluation.experience_score = state.get("experience_score", 0)
        evaluation.reasoning        = state.get("reasoning", "")
        evaluation.github_evidence  = state.get("github_evidence") or {}
        evaluation.gap_analysis     = state.get("gap_analysis") or {}
        evaluation.status           = _determine_status(state.get("score", 0))
        evaluation.candidate_label  = state.get("candidate_label", "")
        evaluation.trace_log        = trace
        evaluation.save()

        # Update trace with final "done" entry and persist it
        trace[-1] = {
            "step":    "Save",
            "message": f"Evaluation saved. Status: {evaluation.status}.",
            "status":  "done",
        }
        evaluation.trace_log = trace
        evaluation.save(update_fields=["trace_log"])

        logger.info(
            "[db_node] Done — evaluation: %s, status: %s, score: %d",
            evaluation_id,
            evaluation.status,
            evaluation.score,
        )

        return {**state, "trace_log": trace}

    except Exception as exc:
        error_msg = f"DB node failed: {exc}"
        logger.error("[db_node] %s", error_msg)
        trace[-1] = {"step": "Save", "message": error_msg, "status": "error"}
        return {**state, "trace_log": trace, "error": error_msg}
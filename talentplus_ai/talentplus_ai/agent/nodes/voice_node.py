"""
Node 6 — Voice
Schedules an AI-powered voice screening interview for candidates who meet
the score threshold.

Trigger rules (VOICE_FOR_STRONG_CANDIDATES removed):
  score >= VOICE_SCORE_THRESHOLD (default 60)
    → enqueues schedule_voice_screen via Celery.
      The Celery task handles: question generation, LiveKit room creation,
      and sending the voice interview invite email to the candidate.

  50 <= score < 60  → borderline (HITL — on hold). No voice scheduled.
  score < 50        → rejected. No voice scheduled.
                       email_node (called by graph.py) sends the rejection.

This node does NOT block the graph. All heavy work (LiveKit, Claude question
generation, Resend invite email) happens asynchronously in Celery.

Changes from original:
  - Removed voice_for_strong / VOICE_FOR_STRONG_CANDIDATES logic entirely.
  - Removed voice_trigger state field (no longer needed without the
    "strong_optional" path distinction).
  - Trigger condition simplified to: score >= settings.VOICE_SCORE_THRESHOLD.
  - Borderline threshold aligned with graph.py: 50–59 (was 60–70).
"""

import logging

from django.conf import settings
from django.db import transaction

from talentplus_ai.agent.state import AgentState

logger = logging.getLogger(__name__)

# Default threshold — can be overridden in settings.
_DEFAULT_VOICE_THRESHOLD = 60


def voice_node(state: AgentState) -> AgentState:
    """
    Evaluates the candidate's score and schedules a voice interview
    asynchronously if the score meets the threshold.

    The invite email is NOT sent here — it is sent by the Celery task
    (schedule_voice_screen) after the LiveKit room and questions are ready.
    """
    if state.get("error"):
        return state

    score = int(state.get("score") or 0)
    candidate_id = state["candidate_id"]
    evaluation_id = state["evaluation_id"]

    trace = list(state.get("trace_log", []))

    voice_threshold = getattr(settings, "VOICE_SCORE_THRESHOLD", _DEFAULT_VOICE_THRESHOLD)

    if score < voice_threshold:
        # Score is either borderline (50–59) or rejected (< 50).
        # In both cases voice_node takes no action:
        #   - Rejected candidates receive an email from email_node.
        #   - Borderline candidates await HITL (on hold).
        logger.info(
            "[voice_node] Score %d < threshold %d. No voice interview scheduled.",
            score,
            voice_threshold,
        )
        return {
            **state,
            "voice_interview_scheduled": False,
            "voice_interview_id": state.get("voice_interview_id"),
            "trace_log": trace,
        }

    # ── Score >= threshold: schedule the voice screening ───────────────
    def _persist_trace(updated: list) -> None:
        """Flush updated trace_log to DB so the UI can reflect it in real time."""
        from talentplus_ai.candidates.models import CandidateEvaluation

        CandidateEvaluation.objects.filter(id=evaluation_id).update(trace_log=updated)

    try:
        from talentplus_ai.voice.tasks import schedule_voice_screen

        cid = str(candidate_id)
        eid = str(evaluation_id)

        # Use on_commit so the schedule only fires after the wrapping
        # DB transaction (ATOMIC_REQUESTS) is fully committed — guarantees
        # the evaluation row exists in the DB when the Celery worker picks it up.
        transaction.on_commit(lambda: schedule_voice_screen.delay(cid, eid))

        trace = [
            *trace,
            {
                "step":    "Voice",
                "message": (
                    f"Score {score} meets the threshold ({voice_threshold}). "
                    "AI voice interview scheduled — questions and invite email "
                    "will be prepared asynchronously."
                ),
                "status":  "done",
            },
        ]
        _persist_trace(trace)

        logger.info(
            "[voice_node] Voice screen enqueued — candidate=%s evaluation=%s score=%d",
            candidate_id,
            evaluation_id,
            score,
        )

        return {
            **state,
            "voice_interview_scheduled": True,
            "voice_interview_id":        None,   # populated later by Celery task
            "trace_log":                 trace,
        }

    except Exception as exc:
        err = f"Voice scheduling failed: {exc}"
        logger.error("[voice_node] %s", err)
        trace = [*trace, {"step": "Voice", "message": err, "status": "error"}]
        _persist_trace(trace)
        return {
            **state,
            "voice_interview_scheduled": False,
            "voice_interview_id":        None,
            "trace_log":                 trace,
        }
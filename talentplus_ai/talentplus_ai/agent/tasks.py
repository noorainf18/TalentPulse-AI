"""
Celery task — trigger_screening

Change from original:
  - Signature changed from trigger_screening(candidate_id) to
    trigger_screening(candidate_id, evaluation_id).
  - run_screening() call updated: removed the stale `resume_text` kwarg,
    added `evaluation_id` kwarg to match the new graph.py signature.
    resume_text is no longer fetched here — parse_node reads from DB.
"""

import logging
from celery import shared_task

from talentplus_ai.agent.graph import run_screening

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def trigger_screening(self, candidate_id: str, evaluation_id: str):
    """
    Celery task that invokes the LangGraph screening pipeline.

    Args:
        candidate_id:  UUID string of the Candidate row.
        evaluation_id: UUID string of the specific CandidateEvaluation row
                       to update. Required because one candidate can now
                       have multiple evaluations (one per target role).
    """
    logger.info(
        "[trigger_screening] Started — candidate: %s, evaluation: %s",
        candidate_id,
        evaluation_id,
    )
    try:
        final_state = run_screening(
            candidate_id=candidate_id,
            evaluation_id=evaluation_id,
        )
        logger.info(
            "[trigger_screening] Completed — candidate: %s, score: %s, label: %s",
            candidate_id,
            final_state.get("score"),
            final_state.get("candidate_label"),
        )
        return {
            "candidate_id": candidate_id,
            "evaluation_id": evaluation_id,
            "score": final_state.get("score"),
            "status": final_state.get("candidate_label"),
        }

    except Exception as exc:
        logger.error(
            "[trigger_screening] Failed for %s: %s",
            candidate_id,
            exc,
        )
        raise self.retry(exc=exc)
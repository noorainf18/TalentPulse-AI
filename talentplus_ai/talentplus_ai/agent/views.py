import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from talentplus_ai.candidates.models import Candidate, CandidateEvaluation

logger = logging.getLogger(__name__)


class AgentStatusView(APIView):
    """
    GET /api/agent/status/<candidate_id>/
    Returns the live trace_log + current score for the Agent Trace Viewer.
    Polled by the Next.js dashboard during screening.
    """

    def get(self, request, candidate_id):
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            return Response({"error": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            evaluation = CandidateEvaluation.objects.get(candidate=candidate)
        except CandidateEvaluation.DoesNotExist:
            return Response(
                {
                    "candidate_id": str(candidate_id),
                    "status": "pending",
                    "trace_log": [],
                    "score": None,
                }
            )

        return Response(
            {
                "candidate_id": str(candidate_id),
                "status": evaluation.status,
                "score": evaluation.score if evaluation.score else None,
                "candidate_label": None,  # Not stored separately; derived from score
                "trace_log": evaluation.trace_log or [],
                "email_sent": evaluation.email_sent,
            }
        )


class AgentRunView(APIView):
    """
    POST /api/agent/run/
    Manually re-triggers the screening agent for an existing candidate.
    Useful for re-evaluation after feedback or if the initial run failed.
    """

    def post(self, request):
        candidate_id = request.data.get("candidate_id")
        if not candidate_id:
            return Response(
                {"error": "candidate_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            return Response({"error": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND)

        # Reset evaluation to pending
        evaluation, _ = CandidateEvaluation.objects.get_or_create(candidate=candidate)
        evaluation.status = "pending"
        evaluation.score = 0
        evaluation.reasoning = "Re-evaluation triggered manually."
        evaluation.trace_log = [
            {"step": "Re-submitted", "message": "Manual re-evaluation triggered.", "status": "done"}
        ]
        evaluation.save()

        from talentplus_ai.agent.tasks import trigger_screening
        trigger_screening.delay(str(candidate_id))

        logger.info(f"[AgentRunView] Re-evaluation triggered for {candidate_id}")

        return Response(
            {"message": "Re-evaluation started.", "candidate_id": str(candidate_id)},
            status=status.HTTP_202_ACCEPTED,
        )

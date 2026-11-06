import logging
from django.db.models import Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from talentplus_ai.candidates.models import Candidate, CandidateEvaluation
from .serializers import (
    EvidenceDashboardSerializer,
    CandidateListItemSerializer,
)

logger = logging.getLogger(__name__)


class DashboardSummaryView(APIView):
    """
    GET /api/dashboard/summary/
    Lightweight homepage summary for dashboard command center.
    """

    def get(self, request):
        total_candidates = Candidate.objects.count()
        evaluations = CandidateEvaluation.objects.select_related("candidate")

        pending_count = (
            Candidate.objects.filter(evaluations__isnull=True).count()
            + evaluations.filter(status="pending").count()
        )
        borderline_count = evaluations.filter(status="borderline").count()
        hired_count = evaluations.filter(status="hired").count()
        rejected_count = evaluations.filter(status="rejected").count()

        score_agg = evaluations.aggregate(avg_score=Avg("score"))
        avg_score = score_agg.get("avg_score")
        avg_score = round(float(avg_score), 1) if avg_score is not None else None

        recent_candidates = Candidate.objects.prefetch_related("evaluations").order_by("-created_at")[:6]
        recent_activity = []
        for c in recent_candidates:
            ev = c.evaluations.order_by("-updated_at").first()
            recent_activity.append(
                {
                    "candidate_id": str(c.id),
                    "name": c.name,
                    "email": c.email,
                    "status": ev.status if ev else "pending",
                    "score": ev.score if ev else None,
                    "created_at": c.created_at,
                }
            )

        return Response(
            {
                "kpis": {
                    "total_candidates": total_candidates,
                    "pending": pending_count,
                    "review_queue": borderline_count,
                    "hired": hired_count,
                    "rejected": rejected_count,
                    "avg_score": avg_score,
                },
                "recent_activity": recent_activity,
            }
        )


class CandidateListView(APIView):
    """
    GET /api/dashboard/candidates/
    Returns paginated list of all candidates with summary scores.
    Supports ?status= and ?min_score= query filters.
    """

    def get(self, request):
        qs = Candidate.objects.prefetch_related("evaluations").order_by("-created_at")

        # Optional filters
        status_filter = request.query_params.get("status")
        min_score = request.query_params.get("min_score")

        if status_filter:
            qs = qs.filter(evaluations__status=status_filter).distinct()

        if min_score:
            try:
                qs = qs.filter(evaluations__score__gte=int(min_score)).distinct()
            except ValueError:
                pass

        serializer = CandidateListItemSerializer(qs, many=True)
        return Response(
            {
                "count": qs.count(),
                "results": serializer.data,
            }
        )


class EvidenceDashboardView(APIView):
    """
    GET /api/dashboard/candidate/<candidate_id>/
    Returns the full evidence panel for one candidate:
    score breakdown, GitHub evidence, gap analysis, reasoning.
    """

    def get(self, request, candidate_id):
        evaluation = (
            CandidateEvaluation.objects.select_related("candidate")
            .prefetch_related("voice_interview__questions__answer")
            .filter(candidate__id=candidate_id)
            .order_by("-updated_at")
            .first()
        )
        if evaluation is None:
            # Candidate exists but evaluation not yet complete
            try:
                candidate = Candidate.objects.get(id=candidate_id)
                return Response(
                    {
                        "candidate_id": str(candidate_id),
                        "candidate_name": candidate.name,
                        "status": "pending",
                        "message": "Evaluation is still in progress. Check back shortly.",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
            except Candidate.DoesNotExist:
                return Response(
                    {"error": "Candidate not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        serializer = EvidenceDashboardSerializer(evaluation)
        return Response(serializer.data)


class AgentTraceView(APIView):
    """
    GET /api/dashboard/candidate/<candidate_id>/trace/
    Returns only the trace_log — used by the Agent Trace Viewer sidebar
    which polls this endpoint every 2 seconds during live evaluation.
    """

    def get(self, request, candidate_id):
        evaluation = (
            CandidateEvaluation.objects.filter(candidate__id=candidate_id)
            .order_by("-updated_at")
            .first()
        )
        if evaluation:
            return Response(
                {
                    "candidate_id": str(candidate_id),
                    "status": evaluation.status,
                    "score": evaluation.score,
                    "trace_log": evaluation.trace_log or [],
                }
            )
        else:
            return Response(
                {
                    "candidate_id": str(candidate_id),
                    "status": "pending",
                    "score": None,
                    "trace_log": [],
                }
            )


class FeedbackView(APIView):
    """
    POST /api/dashboard/feedback/
    Stores recruiter feedback (thumbs up/down + notes) on an evaluation.
    This is the Human-in-the-Loop feedback mechanism.
    Body: { candidate_id, thumbs_up (bool), notes (str, optional) }
    """

    def post(self, request):
        candidate_id = request.data.get("candidate_id")
        thumbs_up = request.data.get("thumbs_up")
        notes = request.data.get("notes", "")

        if candidate_id is None or thumbs_up is None:
            return Response(
                {"error": "candidate_id and thumbs_up are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            evaluation = (
                CandidateEvaluation.objects.select_related("candidate")
                .filter(candidate__id=candidate_id)
                .order_by("-updated_at")
                .first()
            )
            if evaluation is None:
                raise CandidateEvaluation.DoesNotExist
        except CandidateEvaluation.DoesNotExist:
            return Response(
                {"error": "Evaluation not found for this candidate."},
                status=status.HTTP_404_NOT_FOUND,
            )

        evaluation.feedback_thumbs_up = bool(thumbs_up)
        evaluation.feedback_notes = notes
        evaluation.save(update_fields=["feedback_thumbs_up", "feedback_notes", "updated_at"])

        logger.info(
            f"[FeedbackView] Feedback saved for {evaluation.candidate.name}: "
            f"thumbs_up={thumbs_up}, notes='{notes[:50]}'"
        )

        return Response(
            {
                "message": "Feedback saved successfully.",
                "candidate_id": str(candidate_id),
                "thumbs_up": evaluation.feedback_thumbs_up,
            }
        )

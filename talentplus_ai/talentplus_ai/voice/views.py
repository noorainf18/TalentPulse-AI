import logging
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import VoiceInterview, VoiceQuestion
from .serializers import (
    VoiceInterviewSerializer,
    VoiceInterviewSummarySerializer,
    InitiateVoiceScreenSerializer,
    VoiceWebhookSerializer,
)
from .permissions import IsRecruiter, IsCandidateSessionToken
from .choices import VoiceInterviewStatus
from .tasks import schedule_voice_screen, analyze_transcript
from talentplus_ai.candidates.models import CandidateEvaluation

logger = logging.getLogger(__name__)


class InitiateVoiceScreenView(APIView):
    """
    POST /api/voice/initiate/

    Recruiter manually triggers a voice screen for a given evaluation.
    In the automated flow this is called by voice_node via Celery, but
    recruiters can also trigger it manually from the dashboard.
    """
    permission_classes = [IsRecruiter]

    def post(self, request):
        serializer = InitiateVoiceScreenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        evaluation_id = serializer.validated_data["evaluation_id"]
        scheduled_at = serializer.validated_data.get("scheduled_at")

        evaluation = get_object_or_404(CandidateEvaluation, id=evaluation_id)

        # Idempotency: don't create a second interview if one already exists
        existing = VoiceInterview.objects.filter(evaluation=evaluation).first()
        if existing:
            return Response(
                {
                    "message": "Voice interview already exists for this evaluation.",
                    "interview_id": str(existing.id),
                    "status": existing.status,
                },
                status=status.HTTP_200_OK,
            )

        # Defer until HTTP transaction commits (ATOMIC_REQUESTS + eager Celery otherwise
        # runs the task before commit; LiveKit agent then cannot see the VoiceInterview row).
        candidate_id_str = str(evaluation.candidate_id)
        eval_id_str = str(evaluation_id)
        scheduled_iso = scheduled_at.isoformat() if scheduled_at else None

        transaction.on_commit(
            lambda c=candidate_id_str, e=eval_id_str, s=scheduled_iso: schedule_voice_screen.delay(
                c, e, s
            ),
        )

        return Response(
            {"message": "Voice screen scheduled. Candidate will receive an invite email."},
            status=status.HTTP_202_ACCEPTED,
        )


class VoiceInterviewDetailView(APIView):
    """
    GET /api/voice/<interview_id>/

    Returns full interview detail including questions and answers.
    Used by the recruiter dashboard Voice tab.
    """
    permission_classes = [IsRecruiter]

    def get(self, request, interview_id):
        interview = get_object_or_404(VoiceInterview, id=interview_id)
        serializer = VoiceInterviewSerializer(interview)
        return Response(serializer.data)


class VoiceInterviewStatusView(APIView):
    """
    GET /api/voice/<interview_id>/status/

    Lightweight polling endpoint used by the frontend while call is active.
    """
    permission_classes = [IsRecruiter]

    def get(self, request, interview_id):
        interview = get_object_or_404(VoiceInterview, id=interview_id)
        serializer = VoiceInterviewSummarySerializer(interview)
        return Response(serializer.data)


class CandidateJoinView(APIView):
    """
    GET /api/voice/join/?token=<session_token>

    Candidate hits this endpoint (via their invite link) to receive a
    LiveKit access token and room name so their browser can connect to WebRTC.
    No Django auth required — authentication is the session_token UUID.
    """
    permission_classes = [IsCandidateSessionToken]

    def get(self, request):
        token = request.query_params.get("token")
        interview = get_object_or_404(
            VoiceInterview,
            session_token=token,
            status__in=[VoiceInterviewStatus.INVITED, VoiceInterviewStatus.ACTIVE],
        )

        from .services.livekit_client import LiveKitClient
        client = LiveKitClient()

        candidate_name = interview.candidate.name or "Candidate"
        livekit_token = client.create_candidate_token(
            room_name=interview.livekit_room_name,
            participant_name=candidate_name,
        )

        # Mark as active on first join
        if interview.status == VoiceInterviewStatus.INVITED:
            interview.status = VoiceInterviewStatus.ACTIVE
            interview.started_at = timezone.now()
            interview.save(update_fields=["status", "started_at"])

        from django.conf import settings as dj_settings

        return Response({
            # Historical key — value is the room name (not the WebRTC URL). Prefer room_name + livekit_server_url.
            "livekit_url": interview.livekit_room_name,
            "livekit_server_url": dj_settings.LIVEKIT_URL,
            "livekit_token": livekit_token,
            "room_name": interview.livekit_room_name,
            "candidate_name": candidate_name,
            "interview_id": str(interview.id),
        })


class CandidateSessionBriefView(APIView):
    """
    GET /api/voice/session/?token=<session_token>

    Candidate-facing read-only payload for the interview UI (Hirebyte-style
    question list, role title, answer progress). Authenticated by session_token
    only — same contract as CandidateJoinView.
    """

    permission_classes = [IsCandidateSessionToken]

    def get(self, request):
        token = request.query_params.get("token")
        questions_qs = VoiceQuestion.objects.order_by("sequence_order").select_related(
            "answer",
        )
        interview = (
            VoiceInterview.objects.filter(session_token=token)
            .select_related("candidate", "job_description")
            .prefetch_related(Prefetch("questions", queryset=questions_qs))
            .first()
        )
        if not interview:
            return Response({"detail": "Invalid session."}, status=status.HTTP_404_NOT_FOUND)
        if interview.status == VoiceInterviewStatus.FAILED:
            return Response(
                {"detail": "This interview session is no longer available."},
                status=status.HTTP_410_GONE,
            )
        if interview.status == VoiceInterviewStatus.SKIPPED:
            return Response(
                {"detail": "This interview was cancelled."},
                status=status.HTTP_410_GONE,
            )

        role_title = (
            interview.job_description.title
            if interview.job_description
            else "AI voice screening"
        )
        questions_payload = []
        for q in interview.questions.all():
            try:
                ans = q.answer
            except ObjectDoesNotExist:
                ans = None
            text = (ans.answer_text or "").strip() if ans else ""
            answered = bool(text)
            preview = (text[:280] + "…") if len(text) > 280 else text
            questions_payload.append(
                {
                    "id": str(q.id),
                    "sequence_order": q.sequence_order,
                    "question_text": q.question_text,
                    "answered": answered,
                    "answer_preview": preview,
                }
            )

        return Response(
            {
                "interview_id": str(interview.id),
                "status": interview.status,
                "role_title": role_title,
                "candidate_display_name": interview.candidate.name or "Candidate",
                "questions": questions_payload,
            }
        )


class SkipVoiceScreenView(APIView):
    """
    POST /api/voice/<interview_id>/skip/

    Recruiter manually skips the voice screen for a candidate.
    """
    permission_classes = [IsRecruiter]

    def post(self, request, interview_id):
        interview = get_object_or_404(
            VoiceInterview,
            id=interview_id,
            status__in=[VoiceInterviewStatus.PENDING, VoiceInterviewStatus.INVITED],
        )
        interview.status = VoiceInterviewStatus.SKIPPED
        interview.save(update_fields=["status", "updated_at"])
        return Response({"message": "Voice screen skipped."})


class LiveKitWebhookView(APIView):
    """
    POST /api/voice/webhook/livekit/

    Receives LiveKit server webhook events (room_finished, participant_left, etc.)
    Used to detect when a call ends so we can trigger post-call analysis.
    In production, verify the LiveKit webhook signature.
    """
    permission_classes = []  # LiveKit webhook has its own signature auth

    def post(self, request):
        serializer = VoiceWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        event = serializer.validated_data.get("event")
        room_data = serializer.validated_data.get("room", {})
        room_name = room_data.get("name", "")

        if event == "room_finished" and room_name:
            try:
                interview = VoiceInterview.objects.get(livekit_room_name=room_name)
                if interview.status == VoiceInterviewStatus.ACTIVE:
                    interview.status = VoiceInterviewStatus.COMPLETED
                    interview.ended_at = timezone.now()
                    if interview.started_at:
                        delta = interview.ended_at - interview.started_at
                        interview.duration_seconds = int(delta.total_seconds())
                    interview.save(update_fields=["status", "ended_at", "duration_seconds"])

                    # Kick off post-call analysis
                    analyze_transcript.delay(str(interview.id))
                    logger.info(f"Room finished webhook → analysis queued for {interview.id}")

            except VoiceInterview.DoesNotExist:
                logger.warning(f"Webhook: no VoiceInterview found for room {room_name}")

        return Response(status=status.HTTP_200_OK)
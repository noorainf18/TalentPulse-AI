import logging
import uuid
from django.db import models
from django.conf import settings
from talentplus_ai.candidates.models import Candidate, CandidateEvaluation, JobDescription
from .choices import VoiceInterviewStatus, QuestionType

logger = logging.getLogger(__name__)


class VoiceInterview(models.Model):
    """
    One voice screening session per candidate evaluation.
    Created by voice_node after LangGraph screening completes for candidates
    who score >= VOICE_SCORE_THRESHOLD.  Holds the full lifecycle:
    question generation → LiveKit room → live call → transcript →
    post-call analysis → score merge.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="voice_interviews",
    )
    evaluation = models.OneToOneField(
        CandidateEvaluation,
        on_delete=models.CASCADE,
        related_name="voice_interview",
    )
    job_description = models.ForeignKey(
        JobDescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voice_interviews",
    )

    # LiveKit room
    livekit_room_name = models.CharField(max_length=128, unique=True)
    session_token = models.UUIDField(default=uuid.uuid4, unique=True)

    # Lifecycle
    status = models.CharField(
        max_length=20,
        choices=VoiceInterviewStatus.choices,
        default=VoiceInterviewStatus.PENDING,
        db_index=True,
    )
    invite_sent_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Transcript (full merged text from all VoiceAnswer rows)
    transcript_text = models.TextField(blank=True, default="")

    # Scoring
    voice_composite_score = models.FloatField(
        null=True,
        blank=True,
        help_text="0-100 score computed by TranscriptAnalyzer post-call",
    )
    final_merged_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Weighted blend of original evaluation score and voice_composite_score",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="initiated_voice_interviews",
    )
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Voice Interview"
        verbose_name_plural = "Voice Interviews"

    def __str__(self):
        return f"VoiceInterview({self.candidate}, {self.status})"

    @property
    def join_url(self) -> str:
        """
        Candidate-facing interview URL embedded in the invite email.

        IMPORTANT — production checklist
        ---------------------------------
        This URL is sent to real candidates via email. It MUST be a
        publicly reachable HTTPS address, never http://localhost:3000.

        Set one of these in your .env (or environment variables):

            FRONTEND_BASE_URL=https://app.yourcompany.com
            FRONTEND_URL=https://app.yourcompany.com

        If neither is set, the property falls back to the Django
        FRONTEND_URL setting (default: http://localhost:3000) and
        logs a WARNING so the misconfiguration is visible in the
        server logs.

        The URL shape: {base}/interview/{session_token}
        The frontend must handle this route and render the LiveKit
        interview UI for the session_token provided.
        """
        from django.conf import settings as s

        # Preference order:
        #   1. FRONTEND_BASE_URL  (most specific — can override per-environment)
        #   2. FRONTEND_URL       (general frontend root)
        #   3. Hard-coded fallback (development only — will not work for real candidates)
        base = (
            getattr(s, "FRONTEND_BASE_URL", None)
            or getattr(s, "FRONTEND_URL", None)
            or "http://localhost:3000"
        )

        # Warn loudly if the URL is still localhost — this means the env var
        # was never set and the email will contain an unreachable link.
        if "localhost" in base or "127.0.0.1" in base:
            logger.warning(
                "[VoiceInterview.join_url] FRONTEND_BASE_URL resolves to '%s' — "
                "this is a local address and will NOT be reachable by candidates "
                "who receive the interview invite email. "
                "Set FRONTEND_BASE_URL=https://<your-public-domain> in your .env file.",
                base,
            )

        url = f"{base.rstrip('/')}/interview/{self.session_token}"
        return url

    @property
    def is_active(self):
        return self.status == VoiceInterviewStatus.ACTIVE

    @property
    def is_completed(self):
        return self.status == VoiceInterviewStatus.COMPLETED


class VoiceQuestion(models.Model):
    """
    A single interview question generated by VoiceQuestionBuilder for a
    VoiceInterview. Questions are ordered by sequence_order and tied to a
    specific skill gap or role requirement.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(
        VoiceInterview,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
    )
    target_skill = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="The specific skill or gap this question is probing",
    )
    sequence_order = models.PositiveSmallIntegerField(default=0)

    # What a strong answer should include — used by TranscriptAnalyzer for scoring
    expected_answer_signals = models.JSONField(
        default=list,
        help_text="List of 2-3 phrases/concepts a strong answer should mention",
    )
    follow_up_if_vague = models.TextField(
        blank=True,
        default="",
        help_text="Follow-up question if candidate's answer is vague or too short",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence_order"]
        verbose_name = "Voice Question"
        verbose_name_plural = "Voice Questions"

    def __str__(self):
        return f"Q{self.sequence_order}: {self.question_text[:60]}"


class VoiceAnswer(models.Model):
    """
    Candidate's transcribed answer to a single VoiceQuestion, including the
    per-answer score given by TranscriptAnalyzer post-call.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.OneToOneField(
        VoiceQuestion,
        on_delete=models.CASCADE,
        related_name="answer",
    )
    answer_text = models.TextField(blank=True, default="")
    duration_seconds = models.FloatField(null=True, blank=True)

    # Post-call scoring
    answer_score = models.FloatField(
        null=True,
        blank=True,
        help_text="0-10 score for this answer from Claude TranscriptAnalyzer",
    )
    score_reasoning = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Voice Answer"
        verbose_name_plural = "Voice Answers"

    def __str__(self):
        score_str = f"{self.answer_score:.1f}" if self.answer_score is not None else "?"
        return f"Answer to Q{self.question.sequence_order} (score={score_str})"
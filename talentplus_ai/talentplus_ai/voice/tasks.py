"""
Voice Celery tasks.

schedule_voice_screen
---------------------
Full setup for a new voice interview:
  1. Create the VoiceInterview DB record.
  2. Build interview questions via VoiceQuestionBuilder (before any room — the
     agent joins as soon as the room exists and must see questions immediately).
  3. Create the LiveKit room.
  4. Send the voice interview invite email to the candidate.
     (This is the FIRST email a candidate receives after scoring >= 60.)

Key fix vs previous version
----------------------------
Question generation failure (step 3) previously did:

    interview.status = FAILED
    interview.error_message = ...
    interview.save(...)
    raise self.retry(exc=exc)          ← THIS WAS THE PROBLEM

`raise self.retry()` re-raises the exception. Because the task runs
inside transaction.on_commit (which itself runs inside the Django
request's ATOMIC_REQUESTS transaction commit hook), that re-raised
exception propagates all the way up through Django's request handler
and produces an HTTP 500 on /api/candidates/upload/.

The fix: question generation failures are non-retryable. If Claude
fails to generate questions, we log it, mark the interview FAILED,
and RETURN — letting the upload request complete successfully.
The recruiter can re-trigger the interview manually from the dashboard.

LiveKit room creation failure IS retried (it's an external infra call
that can transiently fail), but only up to max_retries. The retry
exception from that path does not propagate into the HTTP request because
the entire voice setup is already committed and the Celery task would
be running in a true separate worker in production. In local dev with
CELERY_TASK_ALWAYS_EAGER, even LiveKit retries are swallowed by the
outer try/except in the upload view.

analyze_transcript
------------------
Post-call analysis:
  1. TranscriptAnalyzer scores all Q-A pairs.
  2. ScoreMerger blends voice_composite_score → final_merged_score.
  3. Re-index the transcript into Chroma for RAG.
  4. If final_merged_score >= VOICE_PASS_THRESHOLD → "next round" email.
     Otherwise → no automated action; recruiter reviews manually.

Job description resolution (KEY FIX)
--------------------------------------
CandidateEvaluation has NO job_description FK. The best-matched role
is stored inside evaluation.gap_analysis by contextualize_node:

    gap_analysis = {
        "best_match_role": "AI Backend Engineer (Junior)",
        "top_role_matches": [
            {"job_id": "<uuid>", "role_title": "AI Backend Engineer (Junior)", ...},
            ...
        ],
        ...
    }

Previously, schedule_voice_screen did:

    job_description = getattr(evaluation, "job_description", None)

This always returned None because the FK does not exist, causing the
VoiceInterview to be created without a linked JobDescription and
making VoiceQuestionBuilder fall back to generic questions even when
a strong role match was found.

The fix: resolve the JobDescription from gap_analysis["top_role_matches"][0]["job_id"]
using a helper (_resolve_job_description_from_gap_analysis). If the
gap_analysis has no match or the DB lookup fails, we fall back to None
gracefully — the generic-question path still works correctly.
"""

import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

# Candidates whose final_merged_score meets or exceeds this threshold
# advance to the next round and receive a congratulations email.
_DEFAULT_VOICE_PASS_THRESHOLD = 70


def _resolve_job_description_from_gap_analysis(evaluation) -> "JobDescription | None":
    """
    Resolves the best-matched JobDescription object from the evaluation's
    gap_analysis dict, as written by contextualize_node.

    contextualize_node stores the best match as:
        gap_analysis = {
            "top_role_matches": [
                {"job_id": "<uuid>", "role_title": "AI Backend Engineer (Junior)", ...},
                ...
            ],
            "best_match_role": "AI Backend Engineer (Junior)",
            ...
        }

    We use the job_id from top_role_matches[0] for a direct PK lookup,
    which is O(1) and avoids any ambiguity from title string matching.

    Falls back to None gracefully so the caller's generic-question
    path continues to work when no match is available.
    """
    from talentplus_ai.candidates.models import JobDescription

    try:
        gap = evaluation.gap_analysis
        if not isinstance(gap, dict):
            return None

        top_matches = gap.get("top_role_matches")
        if not top_matches or not isinstance(top_matches, list):
            return None

        best = top_matches[0]
        job_id = best.get("job_id")
        if not job_id:
            return None

        jd = JobDescription.objects.select_related("team_profile").get(id=job_id)
        logger.info(
            "[_resolve_job_description] Resolved JobDescription '%s' (id=%s) "
            "from gap_analysis for evaluation %s",
            jd.title,
            jd.id,
            evaluation.id,
        )
        return jd

    except Exception as exc:
        logger.warning(
            "[_resolve_job_description] Could not resolve JobDescription from "
            "gap_analysis for evaluation %s: %s. Falling back to None.",
            evaluation.id,
            exc,
        )
        return None


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="voice.schedule_voice_screen",
)
def schedule_voice_screen(
    self,
    candidate_id: str,
    evaluation_id: str,
    scheduled_at_iso: str | None = None,
):
    """
    Full setup task for a new voice interview.

    Triggered by voice_node via transaction.on_commit, which guarantees
    the evaluation row is committed before this task runs.

    Failure behaviour
    -----------------
    LiveKit room creation  → retry up to max_retries (transient infra failure).
    Question generation    → mark interview FAILED and return (no retry).
                             Claude failures are not transient; retrying
                             immediately would just fail again and, in local
                             dev, would propagate an exception into the HTTP
                             request cycle causing a 500 on /api/candidates/upload/.
    """
    import asyncio
    from talentplus_ai.candidates.models import Candidate, CandidateEvaluation
    from .models import VoiceInterview
    from .choices import VoiceInterviewStatus
    from .services.question_builder import VoiceQuestionBuilder
    from .services.livekit_client import LiveKitClient

    # ── 1. Load DB records ───────────────────────────────────────────────────
    try:
        candidate = Candidate.objects.get(id=candidate_id)
        evaluation = CandidateEvaluation.objects.get(id=evaluation_id)
    except (Candidate.DoesNotExist, CandidateEvaluation.DoesNotExist) as e:
        logger.error("[schedule_voice_screen] DB lookup failed: %s", e)
        return

    # ── 2. Idempotency guard ─────────────────────────────────────────────────
    if VoiceInterview.objects.filter(evaluation=evaluation).exists():
        logger.info(
            "[schedule_voice_screen] VoiceInterview already exists for "
            "evaluation %s — skipping.",
            evaluation_id,
        )
        return

    # ── 3. Resolve the best-matched JobDescription from gap_analysis ─────────
    #
    # CandidateEvaluation has NO job_description FK. The matched role is
    # stored inside evaluation.gap_analysis["top_role_matches"][0]["job_id"]
    # by contextualize_node. We resolve it here so VoiceQuestionBuilder
    # receives the full JobDescription + TeamProfile context rather than
    # falling back to generic questions.
    #
    # This replaces the old (always-None) pattern:
    #     job_description = getattr(evaluation, "job_description", None)
    #
    job_description = _resolve_job_description_from_gap_analysis(evaluation)

    if job_description is not None:
        logger.info(
            "[schedule_voice_screen] Using JobDescription '%s' (id=%s) for "
            "VoiceInterview — candidate=%s evaluation=%s",
            job_description.title,
            job_description.id,
            candidate_id,
            evaluation_id,
        )
    else:
        logger.warning(
            "[schedule_voice_screen] No JobDescription resolved from gap_analysis "
            "for evaluation %s. VoiceQuestionBuilder will use generic fallback.",
            evaluation_id,
        )

    # ── 4. Prepare room name and timestamps ──────────────────────────────────
    lk_client    = LiveKitClient()
    room_name    = LiveKitClient.generate_room_name(str(candidate_id))
    scheduled_at = parse_datetime(scheduled_at_iso) if scheduled_at_iso else timezone.now()

    # ── 5. Persist VoiceInterview BEFORE LiveKit room creation ───────────────
    # Agent workers dispatched on room-created events look up the interview
    # by livekit_room_name, so the row must exist in DB first.
    interview = VoiceInterview.objects.create(
        candidate=candidate,
        evaluation=evaluation,
        job_description=job_description,   # now correctly set from gap_analysis
        livekit_room_name=room_name,
        status=VoiceInterviewStatus.PENDING,
        scheduled_at=scheduled_at,
    )
    logger.info(
        "[schedule_voice_screen] VoiceInterview %s created for candidate %s "
        "(job_description=%s)",
        interview.id,
        candidate_id,
        job_description.title if job_description else "None — generic fallback",
    )

    # ── 6. Generate interview questions (NOT retried on failure) ─────────────
    #
    # Must run BEFORE LiveKit room creation: creating the room dispatches the
    # voice worker, which loads VoiceQuestion rows in on_enter. If the room
    # exists first, the agent often joins while Claude is still generating
    # questions → empty list → broken interview.
    #
    try:
        builder   = VoiceQuestionBuilder()
        questions = builder.build(interview)
    except Exception as exc:
        logger.error(
            "[schedule_voice_screen] Unexpected error during question generation "
            "for interview %s: %s",
            interview.id,
            exc,
        )
        questions = []

    if not questions:
        logger.error(
            "[schedule_voice_screen] Question generation produced no questions "
            "for interview %s. Marking interview as FAILED.",
            interview.id,
        )
        interview.status        = VoiceInterviewStatus.FAILED
        interview.error_message = (
            "Question generation failed — Claude returned no questions. "
            "Check VOICE_STRUCTURED_OUTPUT_MODEL and Anthropic API key."
        )
        interview.save(update_fields=["status", "error_message"])
        return

    # ── 7. Create LiveKit room (retryable) ───────────────────────────────────
    try:
        asyncio.run(lk_client.create_room(room_name))
        logger.info(
            "[schedule_voice_screen] LiveKit room created: %s", room_name
        )
    except Exception as exc:
        logger.error(
            "[schedule_voice_screen] LiveKit room creation failed for "
            "interview %s: %s",
            interview.id,
            exc,
        )
        interview.delete()
        raise self.retry(exc=exc)

    # ── 8. Send invite email ─────────────────────────────────────────────────
    _send_invite_email(interview)

    # ── 9. Mark interview as INVITED (after room exists + questions saved) ────
    interview.status         = VoiceInterviewStatus.INVITED
    interview.invite_sent_at = timezone.now()
    interview.save(update_fields=["status", "invite_sent_at"])

    logger.info(
        "[schedule_voice_screen] Setup complete — candidate=%s interview=%s room=%s",
        candidate_id,
        interview.id,
        room_name,
    )


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    name="voice.analyze_transcript",
)
def analyze_transcript(self, interview_id: str):
    """
    Post-call analysis task:
      1. TranscriptAnalyzer scores all Q-A pairs → voice_composite_score.
      2. ScoreMerger blends resume score + voice score → final_merged_score.
      3. Re-index transcript into Chroma for RAG chat.
      4. If final_merged_score >= VOICE_PASS_THRESHOLD → next-round email.
         Otherwise → no automated action; recruiter reviews manually.
    """
    from .models import VoiceInterview
    from .choices import VoiceInterviewStatus
    from .services.transcript_analyzer import TranscriptAnalyzer
    from .services.score_merger import ScoreMerger

    try:
        interview = VoiceInterview.objects.select_related(
            "evaluation", "candidate", "job_description"
        ).get(id=interview_id)
    except VoiceInterview.DoesNotExist:
        logger.error(
            "[analyze_transcript] Interview %s not found.", interview_id
        )
        return

    try:
        analyzer = TranscriptAnalyzer()
        analyzer.analyze(interview_id)

        merger = ScoreMerger()
        merger.merge(str(interview.evaluation_id), interview_id)

        _index_transcript_into_chroma(interview)

        interview.refresh_from_db()
        interview.status = VoiceInterviewStatus.COMPLETED
        interview.save(update_fields=["status"])

        logger.info(
            "[analyze_transcript] Post-call analysis complete for interview %s",
            interview_id,
        )

    except Exception as exc:
        logger.error(
            "[analyze_transcript] Failed for interview %s: %s", interview_id, exc
        )
        raise self.retry(exc=exc)

    # ── Post-voice next-round email ──────────────────────────────────────────
    # Reload to pick up the freshly written final_merged_score.
    interview.refresh_from_db()
    pass_threshold = getattr(
        settings, "VOICE_PASS_THRESHOLD", _DEFAULT_VOICE_PASS_THRESHOLD
    )
    final_score = interview.final_merged_score

    if final_score is not None and final_score >= pass_threshold:
        logger.info(
            "[analyze_transcript] final_merged_score=%.1f >= threshold=%d. "
            "Sending next-round email for interview %s.",
            final_score,
            pass_threshold,
            interview_id,
        )
        _send_next_round_email_for_interview(interview, final_score)
    else:
        logger.info(
            "[analyze_transcript] final_merged_score=%s did not meet "
            "threshold=%d. No next-round email for interview %s.",
            final_score,
            pass_threshold,
            interview_id,
        )


# ── Internal helpers ────────────────────────────────────────────────────────

def _send_invite_email(interview: "VoiceInterview") -> None:
    """
    Send the candidate their unique voice interview invite link via Resend.
    This is the first automated email sent to a candidate who scored >= 60.

    Failures are caught and logged — a broken email must not abort the
    entire setup flow or cause the invite to be resent spuriously.
    """
    try:
        import resend
        from django.conf import settings as s

        resend.api_key = s.RESEND_API_KEY
        candidate  = interview.candidate
        join_url   = interview.join_url
        from_addr  = getattr(s, "EMAIL_FROM_ADDRESS", None) or getattr(
            s, "EMAIL_FROM", "onboarding@resend.dev"
        )
        role_title = (
            interview.job_description.title
            if interview.job_description
            else "AI Screening Call"
        )

        resend.Emails.send({
            "from":    from_addr,
            "to":      [candidate.email],
            "subject": f"TalentPlus AI — Your AI Voice Screening Interview for {role_title}",
            "html": f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1a1a2e;">Hi {candidate.name or 'there'}, you've been shortlisted! 🎉</h2>

  <p>Great news — based on your profile, you've been selected to proceed to our
  <strong>AI-powered voice screening interview</strong> for the
  <strong>{role_title}</strong> position.</p>

  <p>The interview takes approximately 10 minutes and consists of questions about
  your experience and the role. You'll be speaking with an AI interviewer in a
  live audio session.</p>

  <p style="text-align: center; margin: 32px 0;">
    <a href="{join_url}"
       style="background-color: #4f46e5; color: #ffffff; padding: 14px 28px;
              border-radius: 6px; text-decoration: none; font-weight: bold;
              display: inline-block;">
      Join Your Voice Interview
    </a>
  </p>

  <p>This link is unique to you and expires in <strong>48 hours</strong>.
  Please ensure you're in a quiet environment with a working microphone before joining.</p>

  <p>Best of luck!<br/>The TalentPlus Team</p>

  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
  <p style="color: #888; font-size: 12px;">
    This message was sent by TalentPlus AI. Your interview session will be
    recorded for evaluation purposes.
  </p>
</div>
""",
        })

        logger.info(
            "[_send_invite_email] Invite sent to %s for interview %s",
            candidate.email,
            interview.id,
        )

    except Exception as exc:
        logger.error(
            "[_send_invite_email] Failed for interview %s: %s", interview.id, exc
        )


def _send_next_round_email_for_interview(
    interview: "VoiceInterview",
    final_score: float,
) -> None:
    """
    Calls email_node.send_next_round_email() with data extracted from the
    completed VoiceInterview. Failures are logged but do not raise.
    """
    try:
        from talentplus_ai.agent.nodes.email_node import send_next_round_email

        candidate   = interview.candidate
        role_title  = (
            interview.job_description.title
            if interview.job_description
            else "the role"
        )
        voice_score = interview.voice_composite_score or 0.0

        send_next_round_email(
            candidate_name=candidate.name or "",
            candidate_email=candidate.email,
            evaluation_id=str(interview.evaluation_id),
            role_title=role_title,
            voice_score=voice_score,
            final_score=final_score,
        )
    except Exception as exc:
        logger.error(
            "[_send_next_round_email_for_interview] Failed for interview %s: %s",
            interview.id,
            exc,
        )


def _index_transcript_into_chroma(interview: "VoiceInterview") -> None:
    """
    Re-index the voice transcript into Chroma so the RAG chatbot can
    reference voice interview answers when recruiters ask questions.
    Failures are logged but do not raise — indexing is best-effort.
    """
    if not interview.transcript_text:
        return
    try:
        from talentplus_ai.ragchat.services.indexer import index_candidate
        index_candidate(interview.candidate)
        logger.info(
            "[_index_transcript_into_chroma] Re-indexed candidate %s",
            interview.candidate_id,
        )
    except Exception as exc:
        logger.warning(
            "[_index_transcript_into_chroma] Chroma re-index failed "
            "after voice interview %s: %s",
            interview.id,
            exc,
        )
import logging
from django.conf import settings
from ..models import VoiceInterview
from talentplus_ai.candidates.models import CandidateEvaluation

logger = logging.getLogger(__name__)


class ScoreMerger:
    """
    Blends the original AI screening score with the voice interview composite score.

    Weights (configurable via settings):
      - Original evaluation score: 65% (VOICE_ORIGINAL_SCORE_WEIGHT, default 0.65)
      - Voice composite score: 35% (VOICE_SCORE_WEIGHT, default 0.35)

    Updates CandidateEvaluation.score with the blended final score and appends
    a voice_score_summary to the reasoning field so recruiters can see both.
    """

    def __init__(self):
        self.voice_weight = getattr(settings, "VOICE_SCORE_WEIGHT", 0.35)
        self.original_weight = 1.0 - self.voice_weight

    def merge(self, evaluation_id: str, interview_id: str) -> float:
        """
        Performs the score merge. Returns the final_merged_score.
        """
        try:
            evaluation = CandidateEvaluation.objects.get(id=evaluation_id)
            interview = VoiceInterview.objects.get(id=interview_id)
        except (CandidateEvaluation.DoesNotExist, VoiceInterview.DoesNotExist) as e:
            logger.error(f"ScoreMerger: could not find records: {e}")
            return 0.0

        if interview.voice_composite_score is None:
            logger.warning(
                f"voice_composite_score is None for interview {interview_id}. "
                "Skipping merge — original score unchanged."
            )
            return float(evaluation.score or 0)

        original_score = float(evaluation.score or 0)
        voice_score = float(interview.voice_composite_score)

        final_score = (original_score * self.original_weight) + (voice_score * self.voice_weight)
        final_score = round(final_score, 1)

        # Build the voice score summary appended to reasoning
        voice_summary = self._build_voice_summary(interview, voice_score, original_score, final_score)

        # Update evaluation
        existing_reasoning = evaluation.reasoning or ""
        updated_reasoning = existing_reasoning + "\n\n" + voice_summary

        evaluation.score = final_score
        evaluation.reasoning = updated_reasoning
        evaluation.save(update_fields=["score", "reasoning"])

        # Store on the interview too for easy lookup
        interview.final_merged_score = final_score
        interview.save(update_fields=["final_merged_score"])

        logger.info(
            f"Score merge complete: original={original_score}, "
            f"voice={voice_score}, final={final_score} "
            f"(evaluation {evaluation_id})"
        )
        return final_score

    def _build_voice_summary(
        self,
        interview: VoiceInterview,
        voice_score: float,
        original_score: float,
        final_score: float,
    ) -> str:
        """Build a human-readable summary of the voice interview results."""
        lines = [
            "── VOICE INTERVIEW RESULTS ──",
            f"Original AI Score: {original_score:.0f}/100",
            f"Voice Interview Score: {voice_score:.0f}/100",
            f"Final Blended Score: {final_score:.0f}/100",
            f"(Weights: {int(self.original_weight*100)}% AI evaluation + {int(self.voice_weight*100)}% voice)",
            "",
            "Per-Question Scores:",
        ]

        answers = (
            interview.questions
            .order_by("sequence_order")
            .prefetch_related("answer")
        )
        for question in answers:
            answer = getattr(question, "answer", None)
            score_str = f"{answer.answer_score:.1f}/10" if answer and answer.answer_score is not None else "N/A"
            lines.append(
                f"  Q{question.sequence_order} ({question.question_type}): "
                f"{score_str} — {question.target_skill or 'General'}"
            )
            if answer and answer.score_reasoning:
                lines.append(f"    → {answer.score_reasoning}")

        return "\n".join(lines)
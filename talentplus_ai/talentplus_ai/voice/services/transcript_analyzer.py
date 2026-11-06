import json
import logging

from anthropic import Anthropic
from django.conf import settings
from ..models import VoiceInterview, VoiceQuestion, VoiceAnswer
from ..choices import QuestionType
from ..prompts.answer_scoring_prompt import (
    STRUCTURED_OUTPUTS_BETA,
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    VOICE_ANSWER_SCORE_SCHEMA,
)

logger = logging.getLogger(__name__)

_anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Score weights by question type — gap questions matter most
SCORE_WEIGHTS = {
    QuestionType.RESUME_GAP: 0.50,
    QuestionType.ROLE_TECHNICAL: 0.35,
    QuestionType.CULTURE_FIT: 0.15,
    QuestionType.CLARIFICATION: 0.00,
}


class TranscriptAnalyzer:
    """
    Post-call analysis: scores each VoiceAnswer using Claude Structured Outputs,
    then computes a weighted voice_composite_score (0-100) for the VoiceInterview.
    """

    def analyze(self, interview_id: str) -> float:
        """
        Main entry point. Returns the voice_composite_score.
        Called by the analyze_transcript Celery task.
        """
        try:
            interview = VoiceInterview.objects.prefetch_related(
                "questions__answer"
            ).get(id=interview_id)
        except VoiceInterview.DoesNotExist:
            logger.error("VoiceInterview %s not found for analysis", interview_id)
            return 0.0

        questions = list(interview.questions.order_by("sequence_order"))
        scored_results = []

        for question in questions:
            answer = getattr(question, "answer", None)
            if not answer or not answer.answer_text:
                logger.warning("No answer for question %s — skipping scoring", question.id)
                continue

            score, reasoning = self._score_answer_structured(question, answer)
            answer.answer_score = score
            answer.score_reasoning = reasoning
            answer.save(update_fields=["answer_score", "score_reasoning"])

            weight = SCORE_WEIGHTS.get(question.question_type, 0.0)
            scored_results.append((score, weight))

        composite = self._compute_composite(scored_results)

        interview.voice_composite_score = composite
        interview.save(update_fields=["voice_composite_score"])

        logger.info(
            "Transcript analysis complete for %s: voice_composite_score=%.1f",
            interview_id,
            composite,
        )
        return composite

    def _score_answer_structured(
        self, question: VoiceQuestion, answer: VoiceAnswer
    ) -> tuple[float, str]:
        user_message = USER_TEMPLATE.format(
            question_text=question.question_text,
            question_type=question.question_type,
            target_skill=question.target_skill or "General",
            expected_signals=", ".join(question.expected_answer_signals or []),
            answer_text=answer.answer_text,
        )

        model = getattr(settings, "VOICE_STRUCTURED_OUTPUT_MODEL", "claude-sonnet-4-5")

        try:
            message = _anthropic.beta.messages.create(
                model=model,
                max_tokens=512,
                betas=[STRUCTURED_OUTPUTS_BETA],
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
                output_format={
                    "type": "json_schema",
                    "schema": VOICE_ANSWER_SCORE_SCHEMA,
                },
            )
            raw = json.loads(message.content[0].text)
            score = float(raw["score"])
            reasoning = str(raw.get("reasoning", ""))
            return min(max(score, 0.0), 10.0), reasoning
        except TypeError as exc:
            logger.error(
                "Anthropic client too old for structured outputs (voice scoring): %s",
                exc,
            )
            return 5.0, "Scoring unavailable — upgrade anthropic package."
        except (KeyError, ValueError, json.JSONDecodeError, IndexError, AttributeError) as exc:
            logger.error(
                "Failed to parse scoring response for question %s: %s",
                question.id,
                exc,
            )
            return 5.0, "Scoring unavailable due to parsing error."
        except Exception as exc:
            logger.error("Claude API error scoring question %s: %s", question.id, exc)
            return 5.0, "Scoring unavailable due to API error."

    def _compute_composite(self, scored_results: list[tuple[float, float]]) -> float:
        """
        Compute weighted average, normalized to 0-100.
        scored_results: list of (score_0_to_10, weight) tuples.
        """
        if not scored_results:
            return 0.0

        total_weight = sum(w for _, w in scored_results if w > 0)
        if total_weight == 0:
            avg = sum(s for s, _ in scored_results) / len(scored_results)
            return round(avg * 10, 1)

        weighted_sum = sum(s * w for s, w in scored_results if w > 0)
        normalized = (weighted_sum / (10 * total_weight)) * 100
        return round(normalized, 1)

"""
VoiceOrchestrator — LiveKit Agent that conducts the live interview.

Uses **Cartesia** (Sonic-3 model, Robyn voice) for speech synthesis via
`livekit.plugins.cartesia`.

All language/tone/pronunciation concerns live in:
    talentplus_ai/voice/prompts/speech_prompts.py

This file is responsible ONLY for:
  - LiveKit session wiring (VAD, STT, LLM, TTS, turn handling)
  - Async interview flow (on_enter, question sequencing, follow-up logic)
  - Django ORM access via sync_to_async
  - Persisting answers and the final transcript

FIXES APPLIED
─────────────
Fix 1 (2026-04-05 attempt 1): TypeError: expected string or bytes-like object,
  got 'async_generator'
  → Removed normalize_for_tts from tts_text_transforms. Added tts_node override
    and explicit normalize_for_tts() calls before session.say().

Fix 2 (2026-04-05 attempt 2): Agent joins room but never speaks (silent mute).
  → Root cause: tts_normalize_transform was defined as `async def`, so calling
    it returned a coroutine object instead of an AsyncGenerator. Agent.default
    .tts_node received a dead coroutine, produced no audio, and silently failed.
  → Fix: tts_normalize_transform is now a plain `def` that returns _gen(), an
    inner async generator. This gives tts_node a live AsyncGenerator immediately
    without any awaiting, exactly matching the expected signature.

Required settings (Django):
    CARTESIA_API_KEY
    CARTESIA_TTS_VOICE  (defaults to Robyn: f31cc6a7-c1e8-4764-980c-60a361443dd1)
    CARTESIA_TTS_MODEL  (defaults to "sonic-3")
    DEEPGRAM_API_KEY
    ANTHROPIC_API_KEY
    LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET

First-time setup — download turn detector model weights:
    python -m talentplus_ai.voice.services.voice_orchestrator download-files

Run as a standalone process:
    python -m talentplus_ai.voice.services.voice_orchestrator dev
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import AsyncIterable, AsyncGenerator
from typing import Optional

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from asgiref.sync import sync_to_async
from django.conf import settings
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    ModelSettings,
    TurnHandlingOptions,
    cli,
)
from livekit.plugins import cartesia, deepgram, silero
from livekit.plugins import anthropic as lk_anthropic

# ── Optional turn detector import ─────────────────────────────────────────

try:
    from livekit.plugins.turn_detector.multilingual import MultilingualModel
    _TURN_DETECTOR_AVAILABLE = True
except ModuleNotFoundError:
    MultilingualModel = None  # type: ignore[assignment,misc]
    _TURN_DETECTOR_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "livekit-plugins-turn-detector is not installed. "
        "Falling back to VAD-only turn detection. "
        "To enable context-aware turn detection (recommended), run:\n"
        "  pip install livekit-plugins-turn-detector\n"
        "  python -m talentplus_ai.voice.services.voice_orchestrator download-files"
    )

from ..models import VoiceInterview, VoiceQuestion, VoiceAnswer
from ..choices import VoiceInterviewStatus
from ..prompts.speech_prompt import (
    AGENT_SYSTEM_PROMPT,
    normalize_for_tts,
    tts_normalize_transform,
)

logger = logging.getLogger(__name__)

INTERVIEW_DATA_TOPIC = "tp_interview"
_ROBYN_VOICE_ID = "f31cc6a7-c1e8-4764-980c-60a361443dd1"


# ── TTS ───────────────────────────────────────────────────────────────────

def _build_tts() -> cartesia.TTS:
    voice_id = getattr(settings, "CARTESIA_TTS_VOICE", None) or _ROBYN_VOICE_ID
    return cartesia.TTS(
        api_key=settings.CARTESIA_API_KEY,
        model=getattr(settings, "CARTESIA_TTS_MODEL", "sonic-3"),
        voice=voice_id,
        language=getattr(settings, "CARTESIA_TTS_LANGUAGE", "en"),
        speed=getattr(settings, "CARTESIA_SPEED", 0.92),
        emotion=["positivity:low", "curiosity:low"],
    )


# ── DB helpers ────────────────────────────────────────────────────────────

def _fetch_interview(interview_id: str) -> VoiceInterview:
    return (
        VoiceInterview.objects
        .select_related("candidate", "evaluation", "job_description")
        .prefetch_related("questions")
        .get(id=interview_id)
    )


def _fetch_interview_by_room(room_name: str) -> VoiceInterview:
    return VoiceInterview.objects.get(livekit_room_name=room_name)


def _fetch_questions(interview_id: str) -> list[VoiceQuestion]:
    return list(
        VoiceQuestion.objects
        .filter(interview_id=interview_id)
        .order_by("sequence_order")
    )


def _save_answer_sync(
    question: VoiceQuestion,
    answer_text: str,
    duration_seconds: float,
) -> None:
    VoiceAnswer.objects.update_or_create(
        question=question,
        defaults={
            "answer_text":      answer_text,
            "duration_seconds": duration_seconds,
        },
    )


def _build_transcript_sync(interview_id: str) -> str:
    answers = list(
        VoiceAnswer.objects
        .filter(question__interview_id=interview_id)
        .select_related("question")
        .order_by("question__sequence_order")
    )
    parts = [
        f"Q: {a.question.question_text}\nA: {a.answer_text or '[No answer recorded]'}"
        for a in answers
    ]
    return "\n\n".join(parts)


def _update_transcript_sync(interview_id: str, transcript: str) -> None:
    VoiceInterview.objects.filter(id=interview_id).update(
        transcript_text=transcript
    )


# ── Agent ─────────────────────────────────────────────────────────────────

class InterviewAgent(Agent):
    """
    The AI interviewer agent.

    tts_node override:
        Pipes LLM token chunks through tts_normalize_transform — a plain def
        that returns an AsyncGenerator immediately (no await needed). This is
        the ONLY correct way to wrap the async pipeline in LiveKit v1.x.
        Defining the transform as async def would return a coroutine instead,
        causing the agent to sit silently mute with no errors.

    session.say() calls:
        normalize_for_tts() is called explicitly on every string before
        session.say(), since that path bypasses the LLM pipeline entirely
        and never passes through tts_node.
    """

    def __init__(self, interview_id: str) -> None:
        self.interview_id = interview_id
        self._interview: Optional[VoiceInterview] = None
        self._questions: list[VoiceQuestion] = []
        self._current_q_index = 0
        self._current_answer_start: float = 0.0
        self._answer_buffer: list[str] = []
        self._follow_up_used: bool = False

        super().__init__(instructions=AGENT_SYSTEM_PROMPT)

    # ── TTS node override ─────────────────────────────────────────────────
    #
    # tts_normalize_transform is a plain def → returns AsyncGenerator directly.
    # No await, no coroutine, no silent mute.
    # ─────────────────────────────────────────────────────────────────────────

    def tts_node(
        self,
        text: AsyncIterable[str],
        model_settings: ModelSettings,
    ) -> AsyncGenerator[rtc.AudioFrame, None]:
        normalized: AsyncGenerator[str, None] = tts_normalize_transform(text)
        return Agent.default.tts_node(self, normalized, model_settings)

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def on_enter(self) -> None:
        """Called when the agent joins the room and the session starts."""
        try:
            self._interview = await sync_to_async(_fetch_interview)(self.interview_id)
            self._questions = await sync_to_async(_fetch_questions)(self.interview_id)
        except VoiceInterview.DoesNotExist:
            logger.error("VoiceInterview %s not found in DB", self.interview_id)
            await self.session.say(
                "I'm sorry, there was a technical issue. Please contact the recruiter."
            )
            return

        if not self._questions:
            logger.error(
                "VoiceInterview %s has no questions — cannot conduct interview.",
                self.interview_id,
            )
            await self.session.say(
                "I'm sorry, there was a configuration issue with your interview. "
                "Please contact the recruiter."
            )
            return

        candidate_name = (self._interview.candidate.name or "there").title()
        job_title = (
            self._interview.job_description.title
            if self._interview.job_description
            else ""
        )

        await self.session.say(
            normalize_for_tts(
                f"Hello {candidate_name}, welcome! I'm Robyn, your interviewer today."
            ),
            allow_interruptions=False,
        )
        await asyncio.sleep(0.8)

        role_mention = f" for the {job_title} position" if job_title else ""
        await self.session.say(
            normalize_for_tts(
                f"This is your voice screening interview{role_mention}. "
                "It should take around ten minutes."
            ),
            allow_interruptions=False,
        )
        await asyncio.sleep(0.6)

        await self.session.say(
            normalize_for_tts(
                "I'll ask you a few questions — just answer naturally and take your time. "
                "There are no trick questions."
            ),
            allow_interruptions=False,
        )
        await asyncio.sleep(0.8)

        await self.session.say(
            normalize_for_tts("Alright, let's get started."),
            allow_interruptions=False,
        )
        await asyncio.sleep(1.2)
        await self._ask_next_question()

    async def _publish_question_prompted(self, question: VoiceQuestion) -> None:
        """Notify the candidate browser that this main question has been asked."""
        try:
            payload = json.dumps({
                "type": "question_prompted",
                "question_id": str(question.id),
                "sequence_order": question.sequence_order,
            })
            room = self.session.room_io.room
            await room.local_participant.publish_data(
                payload,
                topic=INTERVIEW_DATA_TOPIC,
                reliable=True,
            )
        except Exception:
            logger.warning(
                "Could not publish question_prompted for %s",
                question.id,
                exc_info=True,
            )

    # ── Core interview flow ────────────────────────────────────────────────

    async def _ask_next_question(self) -> None:
        if self._current_q_index >= len(self._questions):
            await self._conclude_interview()
            return

        question = self._questions[self._current_q_index]
        self._answer_buffer = []
        self._follow_up_used = False
        self._current_answer_start = time.time()

        spoken_text = normalize_for_tts(question.question_text)

        await asyncio.sleep(0.5)
        await self.session.say(spoken_text, allow_interruptions=False)
        await self._publish_question_prompted(question)

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        answer_text = new_message.text_content or ""
        self._answer_buffer.append(answer_text)

        if self._current_q_index >= len(self._questions):
            return

        current_question = self._questions[self._current_q_index]
        combined_answer = " ".join(self._answer_buffer).strip()

        should_follow_up = (
            not self._follow_up_used
            and bool(current_question.follow_up_if_vague)
            and await self._should_ask_followup(
                question=current_question,
                answer=combined_answer,
            )
        )

        if should_follow_up:
            self._follow_up_used = True
            await asyncio.sleep(0.4)
            follow_up_text = normalize_for_tts(
                "Thanks for that. " + current_question.follow_up_if_vague
            )
            await self.session.say(follow_up_text, allow_interruptions=False)
            self._answer_buffer = []
        else:
            await self._save_answer(current_question, combined_answer)
            self._current_q_index += 1

            ack = self._next_acknowledgment()
            if ack:
                await asyncio.sleep(0.3)
                await self.session.say(
                    normalize_for_tts(ack), allow_interruptions=False
                )
                await asyncio.sleep(0.6)

            await self._ask_next_question()

    def _next_acknowledgment(self) -> str:
        acks = [
            "Got it, thank you.",
            "That's really helpful.",
            "Great, I appreciate you sharing that.",
            "Understood, thanks.",
            "Thanks for walking me through that.",
        ]
        idx = (self._current_q_index - 1) % len(acks)
        return acks[idx]

    # ── Follow-up decision ────────────────────────────────────────────────

    async def _should_ask_followup(
        self, question: VoiceQuestion, answer: str
    ) -> bool:
        word_count = len(answer.split())

        if word_count >= 20:
            return False
        if word_count < 10:
            return True
        if question.question_type not in ("resume_gap", "role_technical"):
            return False

        signals = ", ".join(question.expected_answer_signals)
        prompt = (
            f"Question: {question.question_text}\n"
            f"Expected signals: {signals}\n"
            f"Candidate answer: {answer}\n\n"
            "Does this answer meaningfully address the question and mention at least "
            "one expected signal? Reply with only: YES or NO"
        )
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        def _call_claude() -> str:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=5,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip().upper()

        verdict = await sync_to_async(_call_claude)()
        return verdict == "NO"

    # ── Persistence ───────────────────────────────────────────────────────

    async def _save_answer(self, question: VoiceQuestion, answer_text: str) -> None:
        duration = round(time.time() - self._current_answer_start, 1)
        try:
            await sync_to_async(_save_answer_sync)(question, answer_text, duration)
        except Exception:
            logger.exception("Failed to save answer for question %s", question.id)

    async def _update_transcript(self) -> None:
        try:
            transcript = await sync_to_async(_build_transcript_sync)(self.interview_id)
            await sync_to_async(_update_transcript_sync)(self.interview_id, transcript)
        except Exception:
            logger.exception(
                "Failed to update transcript for interview %s", self.interview_id
            )

    # ── Closing ───────────────────────────────────────────────────────────

    async def _conclude_interview(self) -> None:
        await asyncio.sleep(0.5)
        await self.session.say(
            normalize_for_tts("That's all the questions I had for you today."),
            allow_interruptions=False,
        )
        await asyncio.sleep(0.7)
        await self.session.say(
            normalize_for_tts("You did really well — thank you so much for your time."),
            allow_interruptions=False,
        )
        await asyncio.sleep(0.6)
        await self.session.say(
            normalize_for_tts(
                "Our recruiting team will review your responses and be in touch soon. "
                "Have a wonderful day!"
            ),
            allow_interruptions=False,
        )
        await asyncio.sleep(2.0)
        await self._update_transcript()
        await self.session.aclose()


# ── Entrypoint ────────────────────────────────────────────────────────────

def _build_turn_handling() -> TurnHandlingOptions | None:
    if _TURN_DETECTOR_AVAILABLE:
        return TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            min_delay=1.5,
            max_delay=4.0,
            interruption={"mode": "adaptive"},
        )

    logger.warning(
        "Using VAD-only turn detection. Install livekit-plugins-turn-detector "
        "and run download-files for context-aware end-of-turn detection."
    )
    return TurnHandlingOptions(
        min_delay=1.5,
        max_delay=4.0,
        interruption={"mode": "vad"},
    )


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()
    room_name = ctx.room.name

    try:
        interview = await sync_to_async(_fetch_interview_by_room)(room_name)
    except VoiceInterview.DoesNotExist:
        logger.error(
            "No VoiceInterview found for room '%s'. Agent exiting.", room_name
        )
        return

    agent = InterviewAgent(interview_id=str(interview.id))

    session = AgentSession(
        vad=silero.VAD.load(
            min_speech_duration=0.1,
            min_silence_duration=0.9,
            prefix_padding_duration=0.5,
            activation_threshold=0.60,
        ),
        stt=deepgram.STT(
            api_key=settings.DEEPGRAM_API_KEY,
            model="nova-3",
            language="en",
            smart_format=True,
            punctuate=True,
        ),
        llm=lk_anthropic.LLM(
            api_key=settings.ANTHROPIC_API_KEY,
            model="claude-haiku-4-5-20251001",
        ),
        tts=_build_tts(),
        # Only built-in string literals — custom callables must NOT go here.
        # Pronunciation normalization is handled via tts_node override instead.
        tts_text_transforms=["filter_markdown", "filter_emoji"],
        turn_handling=_build_turn_handling(),
    )

    await session.start(agent=agent, room=ctx.room)


# ── Server registration ───────────────────────────────────────────────────

server = AgentServer(
    ws_url=settings.LIVEKIT_URL,
    api_key=settings.LIVEKIT_API_KEY,
    api_secret=settings.LIVEKIT_API_SECRET,
)
server.rtc_session(entrypoint)


if __name__ == "__main__":
    cli.run_app(server)
"""
Django Channels WebSocket Consumer
Handles WebSocket connections from the Next.js dashboard.
When a client connects with a candidate_id, this consumer:
  1. Sends the current evaluation state immediately
  2. Polls for updates every 2 seconds and pushes diffs to the client
  3. Closes when the evaluation reaches a terminal state (done/rejected/error)

The Next.js frontend connects to:
  ws://<host>/ws/evaluations/<candidate_id>/
"""

import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {"screening_sent", "rejected", "hired", "borderline"}
POLL_INTERVAL = 2  # seconds


class EvaluationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.candidate_id = self.scope["url_route"]["kwargs"]["candidate_id"]
        self.group_name = f"evaluation_{self.candidate_id}"
        self._running = True

        # Join the channel group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info(f"[WS] Client connected for candidate {self.candidate_id}")

        # Send initial state immediately
        await self._push_current_state()

        # Start polling loop
        asyncio.ensure_future(self._poll_loop())

    async def disconnect(self, close_code):
        self._running = False
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"[WS] Client disconnected for candidate {self.candidate_id} (code={close_code})")

    async def receive(self, text_data):
        """
        Handles messages from the client.
        Currently supports: {"action": "refresh"} to force an immediate push.
        """
        try:
            data = json.loads(text_data)
            if data.get("action") == "refresh":
                await self._push_current_state()
        except json.JSONDecodeError:
            pass

    async def evaluation_update(self, event):
        """
        Called by channel layer group_send from db_node or other sources.
        Broadcasts the update payload directly to the connected client.
        """
        await self.send(text_data=json.dumps(event["data"]))

    async def _push_current_state(self):
        """Fetches current evaluation state from DB and sends it to the client."""
        state = await self._get_evaluation_state()
        await self.send(text_data=json.dumps(state))

    async def _poll_loop(self):
        """
        Polls the DB every POLL_INTERVAL seconds and pushes updates.
        Stops automatically when the evaluation reaches a terminal state.
        """
        while self._running:
            await asyncio.sleep(POLL_INTERVAL)
            if not self._running:
                break

            state = await self._get_evaluation_state()
            await self.send(text_data=json.dumps(state))

            # Stop polling once evaluation is complete
            if state.get("status") in TERMINAL_STATUSES:
                logger.info(
                    f"[WS] Evaluation for {self.candidate_id} reached terminal state: "
                    f"{state.get('status')}. Closing poll loop."
                )
                self._running = False
                break

    @database_sync_to_async
    def _get_evaluation_state(self) -> dict:
        """Fetches the evaluation from DB synchronously (wrapped for async context)."""
        try:
            from talentplus_ai.candidates.models import CandidateEvaluation, Candidate
            candidate = Candidate.objects.get(id=self.candidate_id)
            evaluation = CandidateEvaluation.objects.get(candidate=candidate)

            return {
                "type": "evaluation_update",
                "candidate_id": str(self.candidate_id),
                "status": evaluation.status,
                "score": evaluation.score,
                "technical_score": evaluation.technical_score,
                "culture_score": evaluation.culture_score,
                "experience_score": evaluation.experience_score,
                "reasoning": evaluation.reasoning[:500] if evaluation.reasoning else "",
                "trace_log": evaluation.trace_log or [],
                "email_sent": evaluation.email_sent,
            }
        except Exception as e:
            return {
                "type": "evaluation_update",
                "candidate_id": str(self.candidate_id),
                "status": "pending",
                "score": None,
                "trace_log": [],
                "error": str(e),
            }


class VoiceSessionConsumer(AsyncWebsocketConsumer):
    """
    Recruiter dashboard: subscribe to live voice interview events for one session.
    URL: ws/voice/<session_token>/

    Backend sends via talentplus_ai.voice.services.ws_events.broadcast_voice_session
    with payloads like {"event": "voice.question.started", "sequence_order": 1, ...}.
    """

    async def connect(self):
        self.session_token = self.scope["url_route"]["kwargs"]["session_token"]
        self.group_name = f"voice_session_{self.session_token}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("[WS voice] Client joined session %s", self.session_token)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(
            "[WS voice] Client left session %s (code=%s)",
            self.session_token,
            close_code,
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get("action") == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            pass

    async def voice_event(self, event):
        await self.send(text_data=json.dumps(event.get("data") or {}))

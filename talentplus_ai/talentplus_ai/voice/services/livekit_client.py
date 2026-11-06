import uuid
import logging
from datetime import timedelta
from contextlib import asynccontextmanager
from django.conf import settings
from livekit import api as livekit_api

logger = logging.getLogger(__name__)


class LiveKitClient:
    """
    Thin wrapper around the LiveKit Server API for room and token management.
    Uses livekit-api Python package.

    All room names are namespaced with "talentplus-" to avoid collisions
    with any other LiveKit usage on the same server.

    Note: LiveKitAPI builds an aiohttp ClientSession whose constructor requires
    a running event loop (aiohttp 3.9+). Do not instantiate LiveKitAPI in
    synchronous __init__; async methods open the client inside the coroutine.
    """

    def __init__(self):
        self.url = settings.LIVEKIT_URL
        self.api_key = settings.LIVEKIT_API_KEY
        self.api_secret = settings.LIVEKIT_API_SECRET

    @asynccontextmanager
    async def _api(self):
        async with livekit_api.LiveKitAPI(
            url=self.url,
            api_key=self.api_key,
            api_secret=self.api_secret,
        ) as lkapi:
            yield lkapi

    @staticmethod
    def generate_room_name(candidate_id: str) -> str:
        """Generate a unique, collision-proof room name for one interview."""
        short_uuid = str(uuid.uuid4()).split("-")[0]
        return f"talentplus-{str(candidate_id)[:8]}-{short_uuid}"

    async def create_room(self, room_name: str) -> dict:
        """
        Create a LiveKit room that will host this interview.
        Sets a max duration of VOICE_MAX_DURATION_SECONDS so the room
        automatically closes even if the webhook is missed.
        """
        try:
            async with self._api() as lkapi:
                room = await lkapi.room.create_room(
                    livekit_api.CreateRoomRequest(
                        name=room_name,
                        max_participants=2,       # candidate + AI agent only
                        empty_timeout=180,        # close if nobody joins within 2 min
                        departure_timeout=30,     # close 30s after everyone leaves
                        metadata="talentplus_interview",
                    )
                )
            logger.info(f"LiveKit room created: {room_name}")
            return {"room_name": room.name, "sid": room.sid}
        except Exception as e:
            logger.error(f"Failed to create LiveKit room {room_name}: {e}")
            raise

    def create_candidate_token(self, room_name: str, participant_name: str) -> str:
        """
        Generate a short-lived JWT for the candidate to join the room from browser.
        Candidate can only publish audio (no video, no admin rights).
        Token expires in 2 hours — enough time for them to join when they're ready.
        """
        token = (
            livekit_api.AccessToken(self.api_key, self.api_secret)
            .with_identity(f"candidate-{participant_name.replace(' ', '_').lower()}")
            .with_name(participant_name)
            .with_ttl(timedelta(hours=2))
            .with_grants(
                livekit_api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=False,
                )
            )
            .to_jwt()
        )
        return token

    def create_agent_token(self, room_name: str) -> str:
        """
        Generate a token for the VoiceOrchestrator agent to join the room.
        Agent needs both publish (to speak) and subscribe (to hear candidate).
        """
        token = (
            livekit_api.AccessToken(self.api_key, self.api_secret)
            .with_identity("talentplus-ai-interviewer")
            .with_name("TalentPlus AI Interviewer")
            .with_ttl(timedelta(hours=2))
            .with_grants(
                livekit_api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    agent=True,
                )
            )
            .to_jwt()
        )
        return token

    async def delete_room(self, room_name: str) -> None:
        """Clean up the room after interview ends."""
        try:
            async with self._api() as lkapi:
                await lkapi.room.delete_room(
                    livekit_api.DeleteRoomRequest(room=room_name)
                )
            logger.info(f"LiveKit room deleted: {room_name}")
        except Exception as e:
            logger.warning(f"Failed to delete LiveKit room {room_name}: {e}")

    async def list_participants(self, room_name: str) -> list:
        """Check who is currently in the room."""
        try:
            async with self._api() as lkapi:
                response = await lkapi.room.list_participants(
                    livekit_api.ListParticipantsRequest(room=room_name)
                )
            return list(response.participants)
        except Exception as e:
            logger.warning(f"Could not list participants for {room_name}: {e}")
            return []

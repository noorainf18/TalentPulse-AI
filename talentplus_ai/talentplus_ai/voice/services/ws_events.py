"""
Push voice interview events to recruiters over Channels.

VoiceOrchestrator (or other code) calls broadcast_voice_session when the
question index changes or the session completes. The dashboard connects via
ws/voice/<session_token>/ (VoiceSessionConsumer).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def broadcast_voice_session(session_token: str, payload: dict[str, Any]) -> None:
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            return
        group = f"voice_session_{session_token}"
        async_to_sync(layer.group_send)(
            group,
            {"type": "voice.event", "data": payload},
        )
    except Exception as exc:
        logger.warning("broadcast_voice_session failed: %s", exc)

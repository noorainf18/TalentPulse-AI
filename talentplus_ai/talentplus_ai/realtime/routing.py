from django.urls import re_path
from talentplus_ai.realtime.consumers import EvaluationConsumer, VoiceSessionConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/evaluations/(?P<candidate_id>[0-9a-f-]+)/$",
        EvaluationConsumer.as_asgi(),
    ),
    re_path(
        r"ws/voice/(?P<session_token>[0-9a-f-]+)/$",
        VoiceSessionConsumer.as_asgi(),
    ),
]

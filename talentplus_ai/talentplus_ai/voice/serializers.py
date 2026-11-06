from rest_framework import serializers
from .models import VoiceInterview, VoiceQuestion, VoiceAnswer
from .choices import VoiceInterviewStatus


class VoiceAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceAnswer
        fields = [
            "id",
            "answer_text",
            "duration_seconds",
            "answer_score",
            "score_reasoning",
        ]


class VoiceQuestionSerializer(serializers.ModelSerializer):
    answer = VoiceAnswerSerializer(read_only=True)

    class Meta:
        model = VoiceQuestion
        fields = [
            "id",
            "question_text",
            "question_type",
            "target_skill",
            "sequence_order",
            "expected_answer_signals",
            "answer",
        ]


class VoiceInterviewSerializer(serializers.ModelSerializer):
    """Full detail serializer — used by dashboard candidate detail endpoint."""
    questions = VoiceQuestionSerializer(many=True, read_only=True)
    join_url = serializers.ReadOnlyField()

    class Meta:
        model = VoiceInterview
        fields = [
            "id",
            "status",
            "livekit_room_name",
            "session_token",
            "join_url",
            "invite_sent_at",
            "scheduled_at",
            "started_at",
            "ended_at",
            "duration_seconds",
            "transcript_text",
            "voice_composite_score",
            "final_merged_score",
            "questions",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields


class VoiceInterviewSummarySerializer(serializers.ModelSerializer):
    """Light serializer for list views and status polling."""
    class Meta:
        model = VoiceInterview
        fields = [
            "id",
            "status",
            "voice_composite_score",
            "final_merged_score",
            "duration_seconds",
            "started_at",
            "ended_at",
        ]


class InitiateVoiceScreenSerializer(serializers.Serializer):
    """Request body for POST /api/voice/initiate/."""
    evaluation_id = serializers.UUIDField()
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


class VoiceWebhookSerializer(serializers.Serializer):
    """LiveKit webhook event payload."""
    event = serializers.CharField()
    room = serializers.DictField(required=False)
    participant = serializers.DictField(required=False)
from rest_framework import serializers


class RagIndexSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField(required=False)


class RagAskSerializer(serializers.Serializer):
    question = serializers.CharField()
    session_id = serializers.UUIDField(required=False)
    # FIX: candidate_id was missing entirely from this serializer.
    # Without it, views.py could never read it from validated_data, so
    # every retrieval call silently received candidate_id=None and searched
    # the entire corpus regardless of which candidate was being viewed.
    candidate_id = serializers.UUIDField(required=False)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20, default=6)
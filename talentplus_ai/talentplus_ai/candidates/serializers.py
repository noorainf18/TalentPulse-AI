from rest_framework import serializers
from .models import Candidate, CandidateEvaluation, TeamProfile, JobDescription


class TeamProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamProfile
        fields = "__all__"


class JobDescriptionSerializer(serializers.ModelSerializer):
    team_profile = TeamProfileSerializer(read_only=True)
    team_profile_id = serializers.PrimaryKeyRelatedField(
        queryset=TeamProfile.objects.all(), source="team_profile", write_only=True,
    )

    class Meta:
        model = JobDescription
        fields = "__all__"


class CandidateEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateEvaluation
        fields = [
            "id", "target_role", "score", "technical_score", "culture_score",
            "experience_score", "reasoning", "github_evidence", "gap_analysis",
            "trace_log", "status", "email_sent", "feedback_thumbs_up",
            "feedback_notes", "evaluated_at",
        ]
        read_only_fields = ["id", "evaluated_at"]


class CandidateSerializer(serializers.ModelSerializer):
    evaluations = CandidateEvaluationSerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id", "name", "email", "phone_number", "github_url", "portfolio_url",
            "linkedin_url", "raw_github_username", "summary",
            # skills is now [{category, skills[]}] — JSONField, serialized as-is
            "skills",
            "experience", "projects", "education", "certifications",
            "achievements", "position_of_responsibility", "created_at", "evaluations",
        ]
        read_only_fields = ["id", "created_at"]


class CandidateUploadSerializer(serializers.Serializer):
    """Used for the PDF resume upload endpoint."""
    resume = serializers.FileField()
    target_role = serializers.CharField(
        required=False, allow_blank=True, default="",
        help_text="The role this candidate is applying for, e.g. 'AI Engineer'.",
    )

    def validate_resume(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are accepted.")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must be under 10 MB.")
        return value


class FeedbackSerializer(serializers.Serializer):
    """Used for the human-in-the-loop feedback endpoint."""
    candidate_id = serializers.UUIDField()
    thumbs_up = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
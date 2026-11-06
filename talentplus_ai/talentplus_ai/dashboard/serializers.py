"""
Dashboard Serializers
Shapes the full evidence panel payload for the Next.js HR dashboard.
"""

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from talentplus_ai.candidates.models import Candidate, CandidateEvaluation
from talentplus_ai.voice.serializers import VoiceInterviewSerializer


class ScoreBreakdownSerializer(serializers.Serializer):
    overall = serializers.IntegerField(source="score")
    technical = serializers.IntegerField(source="technical_score")
    culture = serializers.IntegerField(source="culture_score")
    experience = serializers.IntegerField(source="experience_score")


class TraceStepSerializer(serializers.Serializer):
    step = serializers.CharField()
    message = serializers.CharField()
    status = serializers.CharField()


class GitHubEvidenceSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    profile_url = serializers.URLField(required=False, allow_blank=True)
    has_original_work = serializers.BooleanField(required=False, default=False)
    total_recent_commits = serializers.IntegerField(required=False, default=0)
    primary_languages = serializers.DictField(child=serializers.IntegerField(), required=False)
    repos_analysed = serializers.ListField(child=serializers.DictField(), required=False)
    skipped = serializers.BooleanField(required=False, default=False)
    error = serializers.CharField(required=False, allow_blank=True)


class GapAnalysisSerializer(serializers.Serializer):
    best_match_role = serializers.CharField(required=False, allow_blank=True)
    best_match_department = serializers.CharField(required=False, allow_blank=True)
    best_match_fit_score = serializers.FloatField(required=False, default=0)
    critical_gaps = serializers.ListField(child=serializers.CharField(), required=False)
    nice_to_have_gaps = serializers.ListField(child=serializers.CharField(), required=False)
    fills_team_gap = serializers.BooleanField(required=False, default=False)
    top_role_matches = serializers.ListField(child=serializers.DictField(), required=False)


class ParsedResumeSerializer(serializers.Serializer):
    """Structured resume data sourced from flat Candidate model columns."""
    summary = serializers.CharField(source="candidate.summary", allow_blank=True)
    # skills is [{category, skills[]}] — send as-is to the frontend
    skills = serializers.JSONField(source="candidate.skills")
    experience = serializers.JSONField(source="candidate.experience")
    projects = serializers.JSONField(source="candidate.projects")
    education = serializers.JSONField(source="candidate.education")
    certifications = serializers.JSONField(source="candidate.certifications")
    achievements = serializers.JSONField(source="candidate.achievements")
    position_of_responsibility = serializers.JSONField(source="candidate.position_of_responsibility")
    phone_number = serializers.CharField(source="candidate.phone_number", allow_null=True)


class EvidenceDashboardSerializer(serializers.ModelSerializer):
    """Full payload for the evidence dashboard panel. One object per CandidateEvaluation."""
    candidate_name = serializers.CharField(source="candidate.name")
    candidate_email = serializers.CharField(source="candidate.email")
    candidate_github_url = serializers.URLField(source="candidate.github_url", allow_null=True)
    # skills is [{category, skills[]}] — send as-is
    candidate_skills = serializers.JSONField(source="candidate.skills")
    parsed_resume = ParsedResumeSerializer(source="*", read_only=True)
    score_breakdown = ScoreBreakdownSerializer(source="*")
    trace_steps = TraceStepSerializer(source="trace_log", many=True)
    voice_interview = serializers.SerializerMethodField()

    class Meta:
        model = CandidateEvaluation
        fields = [
            "id", "target_role", "candidate_name", "candidate_email",
            "candidate_github_url", "candidate_skills", "parsed_resume",
            "score_breakdown", "reasoning", "github_evidence", "gap_analysis",
            "trace_steps", "status", "email_sent", "feedback_thumbs_up",
            "feedback_notes", "evaluated_at", "voice_interview",
        ]
        read_only_fields = fields

    def get_voice_interview(self, obj):
        try:
            vi = obj.voice_interview
        except ObjectDoesNotExist:
            return None
        return VoiceInterviewSerializer(vi).data


class CandidateListItemSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the candidates list view."""
    best_score = serializers.SerializerMethodField()
    evaluation_status = serializers.SerializerMethodField()
    candidate_label = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            "id", "name", "email", "phone_number", "github_url",
            "skills", "created_at", "best_score", "evaluation_status", "candidate_label",
        ]

    def get_best_score(self, obj):
        evals = obj.evaluations.all()
        return max((e.score for e in evals), default=None)

    def get_evaluation_status(self, obj):
        statuses = {e.status for e in obj.evaluations.all()}
        if not statuses:
            return "pending"
        if "pending" in statuses:
            return "pending"
        if "error" in statuses:
            return "error"
        return "completed"

    def get_candidate_label(self, obj):
        score = self.get_best_score(obj)
        if score is None:
            return "Pending"
        if score >= 85:
            return "Strong Match"
        elif score >= 70:
            return "Hidden Gem"
        elif score >= 60:
            return "Promising"
        elif score >= 45:
            return "Needs Development"
        return "Not a Fit"
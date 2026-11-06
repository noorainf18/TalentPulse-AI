from django.contrib import admin
from .models import Candidate, CandidateEvaluation, TeamProfile, JobDescription


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "github_url", "created_at"]
    search_fields = ["name", "email"]
    readonly_fields = ["id", "created_at"]


@admin.register(CandidateEvaluation)
class CandidateEvaluationAdmin(admin.ModelAdmin):
    list_display = ["candidate", "score", "status", "email_sent", "evaluated_at"]
    list_filter = ["status", "email_sent"]
    search_fields = ["candidate__name", "candidate__email"]
    readonly_fields = ["id", "evaluated_at", "updated_at"]


@admin.register(TeamProfile)
class TeamProfileAdmin(admin.ModelAdmin):
    list_display = ["role", "seniority_level", "department", "hiring_priority", "headcount_needed"]
    list_filter = ["hiring_priority", "seniority_level", "department"]
    search_fields = ["role", "department"]


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ["title", "department", "is_active", "required_experience_years", "salary_range_lpa"]
    list_filter = ["is_active", "department", "employment_type"]
    search_fields = ["title", "description"]

from django.contrib import admin
from .models import VoiceInterview, VoiceQuestion, VoiceAnswer


class VoiceQuestionInline(admin.TabularInline):
    model = VoiceQuestion
    extra = 0
    readonly_fields = ["question_type", "target_skill", "sequence_order", "expected_answer_signals"]
    can_delete = False


class VoiceAnswerInline(admin.TabularInline):
    model = VoiceAnswer
    extra = 0
    readonly_fields = ["answer_text", "answer_score", "score_reasoning", "duration_seconds"]
    can_delete = False


@admin.register(VoiceInterview)
class VoiceInterviewAdmin(admin.ModelAdmin):
    list_display = [
        "id", "candidate", "status", "voice_composite_score",
        "final_merged_score", "duration_seconds", "created_at",
    ]
    list_filter = ["status"]
    search_fields = ["candidate__email", "candidate__name"]
    readonly_fields = [
        "id", "livekit_room_name", "session_token", "join_url",
        "started_at", "ended_at", "duration_seconds",
        "voice_composite_score", "final_merged_score",
        "transcript_text", "created_at", "updated_at",
    ]
    inlines = [VoiceQuestionInline]


@admin.register(VoiceQuestion)
class VoiceQuestionAdmin(admin.ModelAdmin):
    list_display = ["interview", "sequence_order", "question_type", "target_skill"]
    list_filter = ["question_type"]
    inlines = [VoiceAnswerInline]
from django.urls import path
from . import views

app_name = "voice"

urlpatterns = [
    path("initiate/", views.InitiateVoiceScreenView.as_view(), name="initiate"),
    path("session/", views.CandidateSessionBriefView.as_view(), name="session_brief"),
    path("join/", views.CandidateJoinView.as_view(), name="join"),
    path("webhook/livekit/", views.LiveKitWebhookView.as_view(), name="livekit_webhook"),
    path("<uuid:interview_id>/", views.VoiceInterviewDetailView.as_view(), name="detail"),
    path("<uuid:interview_id>/status/", views.VoiceInterviewStatusView.as_view(), name="status"),
    path("<uuid:interview_id>/skip/", views.SkipVoiceScreenView.as_view(), name="skip"),
]
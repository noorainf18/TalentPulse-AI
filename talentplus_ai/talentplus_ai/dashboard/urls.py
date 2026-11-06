from django.urls import path
from .views import (
    DashboardSummaryView,
    CandidateListView,
    EvidenceDashboardView,
    AgentTraceView,
    FeedbackView,
)

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("candidates/", CandidateListView.as_view(), name="dashboard-candidates"),
    path("candidate/<uuid:candidate_id>/", EvidenceDashboardView.as_view(), name="dashboard-evidence"),
    path("candidate/<uuid:candidate_id>/trace/", AgentTraceView.as_view(), name="dashboard-trace"),
    path("feedback/", FeedbackView.as_view(), name="dashboard-feedback"),
]

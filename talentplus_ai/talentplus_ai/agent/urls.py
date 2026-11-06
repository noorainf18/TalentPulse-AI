from django.urls import path
from .views import AgentStatusView, AgentRunView

urlpatterns = [
    path("run/", AgentRunView.as_view(), name="agent-run"),
    path("status/<uuid:candidate_id>/", AgentStatusView.as_view(), name="agent-status"),
]

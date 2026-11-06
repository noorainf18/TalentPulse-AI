from django.urls import path
from .views import ResumeUploadView, CandidateListView, CandidateDetailView

urlpatterns = [
    path("", CandidateListView.as_view(), name="candidate-list"),
    path("upload/", ResumeUploadView.as_view(), name="resume-upload"),
    path("<uuid:candidate_id>/", CandidateDetailView.as_view(), name="candidate-detail"),
]

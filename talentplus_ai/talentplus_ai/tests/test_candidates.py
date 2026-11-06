"""
Tests — Candidates App
Covers: resume upload endpoint, model creation, serializer validation.
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from talentplus_ai.candidates.models import Candidate, CandidateEvaluation, TeamProfile, JobDescription


# ── Fixtures ────────────────────────────────────────────────────

def make_fake_pdf_file(name="test_resume.pdf") -> io.BytesIO:
    """Creates a minimal in-memory fake PDF for upload tests."""
    content = b"%PDF-1.4 fake pdf content for testing"
    f = io.BytesIO(content)
    f.name = name
    return f


def create_candidate(**kwargs) -> Candidate:
    defaults = {
        "name": "Test Candidate",
        "email": "test@example.com",
        "resume_text": "Python developer with FastAPI experience.",
        "skills": ["Python", "FastAPI", "Docker"],
        "github_url": "https://github.com/testuser",
        "raw_github_username": "testuser",
    }
    defaults.update(kwargs)
    return Candidate.objects.create(**defaults)


# ── Model Tests ─────────────────────────────────────────────────

class TestCandidateModel(TestCase):

    def test_candidate_str(self):
        candidate = create_candidate()
        assert str(candidate) == "Test Candidate <test@example.com>"

    def test_candidate_uuid_primary_key(self):
        candidate = create_candidate()
        assert candidate.id is not None
        assert len(str(candidate.id)) == 36  # UUID format

    def test_candidate_skills_default_list(self):
        candidate = Candidate.objects.create(
            name="No Skills",
            email="noskills@example.com",
            resume_text="Empty",
        )
        assert candidate.skills == []

    def test_duplicate_email_raises(self):
        create_candidate(email="dup@example.com")
        with pytest.raises(Exception):
            create_candidate(email="dup@example.com")


class TestCandidateEvaluationModel(TestCase):

    def setUp(self):
        self.candidate = create_candidate()

    def test_evaluation_str(self):
        evaluation = CandidateEvaluation.objects.create(
            candidate=self.candidate,
            score=88,
            status="screening_sent",
            reasoning="Strong candidate.",
        )
        assert "Test Candidate" in str(evaluation)
        assert "88" in str(evaluation)

    def test_evaluation_defaults(self):
        evaluation = CandidateEvaluation.objects.create(
            candidate=self.candidate,
            reasoning="Test",
        )
        assert evaluation.score == 0
        assert evaluation.status == "pending"
        assert evaluation.email_sent is False
        assert evaluation.trace_log == []


class TestTeamProfileModel(TestCase):

    def test_team_profile_creation(self):
        profile = TeamProfile.objects.create(
            role="Senior AI Engineer",
            seniority_level="Senior",
            department="AI Platform",
            current_skills=["Python", "LangGraph"],
            missing_skills=["Rust", "Kubernetes"],
            culture_values=["ownership", "async-first"],
            hiring_priority="High",
        )
        assert "Senior AI Engineer" in str(profile)
        assert profile.headcount_needed == 1


# ── API Endpoint Tests ──────────────────────────────────────────

class TestResumeUploadView(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("resume-upload")

    @patch("candidates.views.extract_text_from_pdf")
    @patch("candidates.views.vectorize_and_store")
    @patch("agent.tasks.trigger_screening.delay")
    def test_successful_upload(self, mock_task, mock_vectorize, mock_parse):
        mock_parse.return_value = {
            "raw_text": "Python developer",
            "name": "Jane Doe",
            "email": "jane@example.com",
            "github_url": "https://github.com/janedoe",
            "github_username": "janedoe",
            "portfolio_url": None,
            "skills": ["Python", "FastAPI"],
        }
        mock_vectorize.return_value = True
        mock_task.return_value = None

        pdf_file = make_fake_pdf_file()
        response = self.client.post(self.url, {"resume": pdf_file}, format="multipart")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "candidate_id" in response.data
        assert Candidate.objects.filter(email="jane@example.com").exists()
        mock_task.assert_called_once()

    def test_upload_non_pdf_rejected(self):
        txt_file = io.BytesIO(b"not a pdf")
        txt_file.name = "resume.txt"
        response = self.client.post(self.url, {"resume": txt_file}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_no_file_rejected(self):
        response = self.client.post(self.url, {}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("candidates.views.extract_text_from_pdf")
    @patch("candidates.views.vectorize_and_store")
    @patch("agent.tasks.trigger_screening.delay")
    def test_duplicate_email_returns_existing(self, mock_task, mock_vectorize, mock_parse):
        existing = create_candidate(email="existing@example.com")
        mock_parse.return_value = {
            "raw_text": "text",
            "name": "Existing User",
            "email": "existing@example.com",
            "github_url": None,
            "github_username": "",
            "portfolio_url": None,
            "skills": [],
        }
        pdf_file = make_fake_pdf_file()
        response = self.client.post(self.url, {"resume": pdf_file}, format="multipart")

        assert response.status_code == status.HTTP_200_OK
        assert str(existing.id) == response.data["candidate_id"]
        mock_task.assert_not_called()


class TestCandidateListView(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("candidate-list")

    def test_returns_all_candidates(self):
        create_candidate(email="a@example.com")
        create_candidate(email="b@example.com", name="Candidate B")
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

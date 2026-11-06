"""
Tests — Dashboard App
Covers: evidence panel, candidate list, agent trace, feedback submission.
"""

import uuid
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from talentplus_ai.candidates.models import Candidate, CandidateEvaluation


# ── Helpers ─────────────────────────────────────────────────────

def make_candidate_with_evaluation(
    email="dash@example.com",
    name="Dashboard User",
    score=88,
    eval_status="borderline",
    **eval_kwargs,
):
    candidate = Candidate.objects.create(
        name=name,
        email=email,
        resume_text="Python LangGraph FastMCP developer.",
        skills=["Python", "LangGraph", "FastMCP"],
        github_url="https://github.com/dashuser",
        raw_github_username="dashuser",
    )
    evaluation = CandidateEvaluation.objects.create(
        candidate=candidate,
        score=score,
        technical_score=score + 2,
        culture_score=score - 3,
        experience_score=score + 1,
        reasoning="Strong technical candidate. GitHub shows original work.",
        status=eval_status,
        github_evidence={
            "username": "dashuser",
            "has_original_work": True,
            "total_recent_commits": 42,
            "primary_languages": {"Python": 8000},
            "repos_analysed": [],
        },
        gap_analysis={
            "best_match_role": "Senior Agentic AI Engineer",
            "best_match_fit_score": 0.88,
            "critical_gaps": [],
            "nice_to_have_gaps": ["Kubernetes"],
            "fills_team_gap": True,
        },
        trace_log=[
            {"step": "Parse", "message": "12 skills extracted.", "status": "done"},
            {"step": "Research", "message": "3 repos analysed.", "status": "done"},
            {"step": "Score", "message": "Score: 88/100.", "status": "done"},
        ],
        **eval_kwargs,
    )
    return candidate, evaluation


# ── Candidate List View ──────────────────────────────────────────

class TestCandidateListView(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("dashboard-candidates")

    def test_returns_all_candidates(self):
        make_candidate_with_evaluation(email="a@example.com", score=90)
        make_candidate_with_evaluation(email="b@example.com", score=55)
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 2

    def test_filter_by_status(self):
        make_candidate_with_evaluation(email="screening@example.com", eval_status="screening_sent", score=92)
        make_candidate_with_evaluation(email="borderline@example.com", eval_status="borderline", score=72)

        response = self.client.get(self.url, {"status": "screening_sent"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["evaluation_status"] == "screening_sent"

    def test_filter_by_min_score(self):
        make_candidate_with_evaluation(email="high@example.com", score=90)
        make_candidate_with_evaluation(email="low@example.com", score=45)

        response = self.client.get(self.url, {"min_score": "80"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_candidate_label_strong_match(self):
        make_candidate_with_evaluation(email="strong@example.com", score=90)
        response = self.client.get(self.url)
        result = response.data["results"][0]
        assert result["candidate_label"] == "Strong Match"

    def test_candidate_label_hidden_gem(self):
        make_candidate_with_evaluation(email="gem@example.com", score=75)
        response = self.client.get(self.url)
        result = response.data["results"][0]
        assert result["candidate_label"] == "Hidden Gem"

    def test_empty_results(self):
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0


# ── Evidence Dashboard View ──────────────────────────────────────

class TestEvidenceDashboardView(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_returns_full_evidence_panel(self):
        candidate, evaluation = make_candidate_with_evaluation(score=88)
        url = reverse("dashboard-evidence", kwargs={"candidate_id": candidate.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Core fields
        assert data["candidate_name"] == "Dashboard User"
        assert data["candidate_email"] == "dash@example.com"

        # Score breakdown
        assert data["score_breakdown"]["overall"] == 88
        assert data["score_breakdown"]["technical"] == 90
        assert data["score_breakdown"]["culture"] == 85

        # GitHub evidence
        assert data["github_evidence"]["has_original_work"] is True
        assert data["github_evidence"]["total_recent_commits"] == 42

        # Gap analysis
        assert data["gap_analysis"]["best_match_role"] == "Senior Agentic AI Engineer"
        assert data["gap_analysis"]["fills_team_gap"] is True

        # Trace log
        assert len(data["trace_steps"]) == 3
        assert data["trace_steps"][0]["step"] == "Parse"

    def test_returns_202_for_pending_evaluation(self):
        candidate = Candidate.objects.create(
            name="Pending User",
            email="pending@example.com",
            resume_text="Some resume.",
        )
        url = reverse("dashboard-evidence", kwargs={"candidate_id": candidate.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["status"] == "pending"

    def test_returns_404_for_unknown_candidate(self):
        unknown_id = uuid.uuid4()
        url = reverse("dashboard-evidence", kwargs={"candidate_id": unknown_id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ── Agent Trace View ─────────────────────────────────────────────

class TestAgentTraceView(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_returns_trace_log_and_score(self):
        candidate, evaluation = make_candidate_with_evaluation(score=88)
        url = reverse("dashboard-trace", kwargs={"candidate_id": candidate.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["score"] == 88
        assert len(response.data["trace_log"]) == 3
        assert response.data["status"] == "borderline"

    def test_returns_empty_trace_for_missing_evaluation(self):
        candidate = Candidate.objects.create(
            name="No Eval",
            email="noeval@example.com",
            resume_text="text",
        )
        url = reverse("dashboard-trace", kwargs={"candidate_id": candidate.id})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "pending"
        assert response.data["trace_log"] == []
        assert response.data["score"] is None


# ── Feedback View ────────────────────────────────────────────────

class TestFeedbackView(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("dashboard-feedback")

    def test_thumbs_up_feedback_saved(self):
        candidate, evaluation = make_candidate_with_evaluation()

        response = self.client.post(
            self.url,
            {
                "candidate_id": str(candidate.id),
                "thumbs_up": True,
                "notes": "Great candidate — TypeScript skills were undervalued.",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["thumbs_up"] is True

        evaluation.refresh_from_db()
        assert evaluation.feedback_thumbs_up is True
        assert "TypeScript" in evaluation.feedback_notes

    def test_thumbs_down_feedback_saved(self):
        candidate, evaluation = make_candidate_with_evaluation()

        response = self.client.post(
            self.url,
            {"candidate_id": str(candidate.id), "thumbs_up": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        evaluation.refresh_from_db()
        assert evaluation.feedback_thumbs_up is False

    def test_feedback_without_notes_defaults_to_empty(self):
        candidate, evaluation = make_candidate_with_evaluation()

        response = self.client.post(
            self.url,
            {"candidate_id": str(candidate.id), "thumbs_up": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        evaluation.refresh_from_db()
        assert evaluation.feedback_notes == ""

    def test_feedback_missing_candidate_id_rejected(self):
        response = self.client.post(
            self.url,
            {"thumbs_up": True},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_feedback_missing_thumbs_up_rejected(self):
        candidate, _ = make_candidate_with_evaluation()
        response = self.client.post(
            self.url,
            {"candidate_id": str(candidate.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_feedback_unknown_candidate_returns_404(self):
        response = self.client.post(
            self.url,
            {"candidate_id": str(uuid.uuid4()), "thumbs_up": True},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

"""
Tests — MCP Tools
Covers: github_researcher, culture_fit_check, email_sender
All external API calls are mocked.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase

from talentplus_ai.mcp_tools.github_researcher import github_researcher
from talentplus_ai.mcp_tools.culture_fit_check import culture_fit_check
from talentplus_ai.mcp_tools.email_sender import email_sender
from talentplus_ai.candidates.models import TeamProfile, JobDescription


# ── Tool 1: github_researcher ────────────────────────────────────

class TestGitHubResearcher(TestCase):

    @patch("mcp_tools.github_researcher.build_github_evidence")
    def test_multi_repo_overview(self, mock_build):
        mock_build.return_value = {
            "username": "iamjr15",
            "has_original_work": True,
            "total_recent_commits": 60,
            "primary_languages": {"TypeScript": 10000, "Python": 8000},
            "repos_analysed": [
                {"name": "cheatcode", "is_fork": False, "stars": 22},
            ],
        }

        result = github_researcher(username="iamjr15")

        assert result["username"] == "iamjr15"
        assert result["has_original_work"] is True
        assert result["total_recent_commits"] == 60
        mock_build.assert_called_once_with("iamjr15")

    @patch("mcp_tools.github_researcher.fetch_repo_readme")
    @patch("mcp_tools.github_researcher.fetch_repo_languages")
    @patch("mcp_tools.github_researcher.fetch_commit_stats")
    def test_single_repo_deep_dive(self, mock_commits, mock_langs, mock_readme):
        mock_readme.return_value = "# Cheatcode\nAI coding assistant built with FastAPI and LangChain."
        mock_langs.return_value = {"TypeScript": 12000, "Python": 8000}
        mock_commits.return_value = {
            "total_commits_fetched": 35,
            "recent_commits_90_days": 18,
            "sample_messages": ["feat: add MCP integration", "fix: reduce latency"],
        }

        result = github_researcher(username="iamjr15", repo_name="cheatcode")

        assert result["username"] == "iamjr15"
        assert result["repo_name"] == "cheatcode"
        assert result["primary_language"] == "TypeScript"
        assert result["recent_commits_90_days"] == 18
        assert "Active contributor" in result["code_quality_signals"]
        assert "Well-documented README" in result["code_quality_signals"]

    def test_empty_username_returns_error(self):
        result = github_researcher(username="")
        assert "error" in result

    @patch("mcp_tools.github_researcher.build_github_evidence")
    def test_github_fetch_error_handled(self, mock_build):
        from talentplus_ai.core.exceptions import GitHubFetchError
        mock_build.side_effect = GitHubFetchError("User not found")

        result = github_researcher(username="nonexistentuser12345")
        assert "error" in result


# ── Tool 2: culture_fit_check ────────────────────────────────────

class TestCultureFitCheck(TestCase):

    def setUp(self):
        self.profile = TeamProfile.objects.create(
            role="Senior Agentic AI Engineer",
            seniority_level="Senior",
            department="AI Platform",
            current_skills=["Python", "FastAPI"],
            missing_skills=["Rust", "Kubernetes"],
            culture_values=["ownership", "open-source contributor", "async-first"],
            hiring_priority="High",
        )
        self.job = JobDescription.objects.create(
            title="Senior Agentic AI Engineer",
            department="AI Platform",
            team_profile=self.profile,
            description="Build agentic systems.",
            required_skills=["LangGraph", "FastMCP", "Python", "FastAPI"],
            preferred_skills=["TypeScript", "Kubernetes", "Terraform"],
            is_active=True,
        )

    def test_perfect_match_candidate(self):
        skills = ["LangGraph", "FastMCP", "Python", "FastAPI", "TypeScript"]
        result = culture_fit_check(candidate_skills=skills)

        assert result["best_match_role"] == "Senior Agentic AI Engineer"
        assert result["best_match_fit_score"] > 0.8
        assert result["critical_gaps"] == []
        assert result["fills_critical_team_gap"] is True  # Has Rust? No — fills something else

    def test_partial_match_shows_gaps(self):
        skills = ["Python", "Django", "REST APIs"]  # Missing LangGraph, FastMCP
        result = culture_fit_check(candidate_skills=skills)

        assert "LangGraph" in result["critical_gaps"] or "FastMCP" in result["critical_gaps"]
        assert result["best_match_fit_score"] < 0.6

    def test_empty_skills_returns_error(self):
        result = culture_fit_check(candidate_skills=[])
        assert "error" in result

    def test_no_active_jobs(self):
        JobDescription.objects.all().update(is_active=False)
        result = culture_fit_check(candidate_skills=["Python", "LangGraph"])
        assert result.get("status") == "no_active_roles"

    def test_returns_top_3_matches(self):
        # Create two more jobs
        for i in range(2):
            JobDescription.objects.create(
                title=f"AI Engineer {i}",
                department="Product AI",
                team_profile=self.profile,
                description="Build AI.",
                required_skills=["Python"],
                preferred_skills=["FastAPI"],
                is_active=True,
            )
        result = culture_fit_check(candidate_skills=["Python", "FastAPI"])
        assert len(result["top_matches"]) <= 3

    def test_fills_team_gap_detection(self):
        # Candidate has Rust — which is in the team's missing_skills
        skills = ["Python", "LangGraph", "FastMCP", "FastAPI", "Rust"]
        result = culture_fit_check(candidate_skills=skills)
        assert result["fills_critical_team_gap"] is True


# ── Tool 3: email_sender ─────────────────────────────────────────

class TestEmailSender(TestCase):

    @patch("mcp_tools.email_sender.resend.Emails.send")
    def test_sends_screening_email(self, mock_send):
        mock_send.return_value = {"id": "res_abc123"}

        result = email_sender(
            to_email="sahil@example.com",
            subject="You've been shortlisted!",
            body="<p>Great work on your GitHub. Let's schedule a call.</p>",
            email_type="screening",
        )

        assert result["status"] == "sent"
        assert result["email_id"] == "res_abc123"
        assert result["email_type"] == "screening"
        mock_send.assert_called_once()

    @patch("mcp_tools.email_sender.resend.Emails.send")
    def test_sends_rejection_email(self, mock_send):
        mock_send.return_value = {"id": "res_rej789"}

        result = email_sender(
            to_email="anuj@example.com",
            subject="Your application update",
            body="Thank you for applying. We won't be moving forward at this time.",
            email_type="rejection",
        )

        assert result["status"] == "sent"
        assert result["email_type"] == "rejection"

    def test_invalid_email_rejected(self):
        result = email_sender(
            to_email="not-an-email",
            subject="Test",
            body="Hello",
        )
        assert result["status"] == "failed"
        assert "Invalid email" in result["message"]

    def test_missing_subject_rejected(self):
        result = email_sender(
            to_email="test@example.com",
            subject="",
            body="Hello",
        )
        assert result["status"] == "failed"

    def test_missing_body_rejected(self):
        result = email_sender(
            to_email="test@example.com",
            subject="Subject",
            body="",
        )
        assert result["status"] == "failed"

    @patch("mcp_tools.email_sender.resend.Emails.send")
    def test_wraps_plain_text_in_html(self, mock_send):
        mock_send.return_value = {"id": "res_plain"}

        email_sender(
            to_email="test@example.com",
            subject="Plain text test",
            body="This is plain text without HTML tags.",
            email_type="custom",
        )

        call_kwargs = mock_send.call_args[0][0]
        assert "<div" in call_kwargs["html"]

    @patch("mcp_tools.email_sender.resend.Emails.send")
    def test_api_failure_returns_failed_status(self, mock_send):
        mock_send.side_effect = Exception("Resend API down")

        result = email_sender(
            to_email="test@example.com",
            subject="Test",
            body="Hello",
        )
        assert result["status"] == "failed"
        assert "Resend API" in result["message"]

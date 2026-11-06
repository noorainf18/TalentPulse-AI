"""
Tests — Agent App
Covers: all 6 LangGraph nodes (with mocked external calls),
        graph routing logic, Celery task behaviour.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase

from talentplus_ai.agent.state import AgentState
from talentplus_ai.agent.nodes.parse_node import parse_node
from talentplus_ai.agent.nodes.research_node import research_node
from talentplus_ai.agent.nodes.contextualize_node import contextualize_node
from talentplus_ai.agent.nodes.score_node import score_node
from talentplus_ai.agent.nodes.db_node import db_node
from talentplus_ai.agent.nodes.email_node import email_node
from talentplus_ai.candidates.models import Candidate, CandidateEvaluation, TeamProfile, JobDescription


# ── Helpers ─────────────────────────────────────────────────────

def make_candidate(**kwargs) -> Candidate:
    defaults = {
        "name": "Gaurav Tripathi",
        "email": "gaurav@example.com",
        "resume_text": "LangGraph FastMCP Python FastAPI Docker Anthropic Claude API",
        "skills": ["LangGraph", "FastMCP", "Python", "FastAPI", "Docker"],
        "github_url": "https://github.com/gauravtripathi",
        "raw_github_username": "gauravtripathi",
    }
    defaults.update(kwargs)
    return Candidate.objects.create(**defaults)


def base_state(candidate_id: str, **overrides) -> AgentState:
    state: AgentState = {
        "candidate_id": candidate_id,
        "resume_text": "LangGraph FastMCP Python FastAPI Docker",
        "name": "",
        "email": "",
        "skills": [],
        "github_url": None,
        "github_username": None,
        "portfolio_url": None,
        "github_evidence": None,
        "gap_analysis": None,
        "score": 0,
        "technical_score": 0,
        "culture_score": 0,
        "experience_score": 0,
        "reasoning": "",
        "candidate_label": "",
        "email_status": "skipped",
        "trace_log": [],
        "error": None,
    }
    state.update(overrides)
    return state


# ── Node 1: Parse ────────────────────────────────────────────────

class TestParseNode(TestCase):

    def setUp(self):
        self.candidate = make_candidate()

    def test_parse_node_populates_fields(self):
        state = base_state(str(self.candidate.id))
        result = parse_node(state)

        assert result["name"] == "Gaurav Tripathi"
        assert result["email"] == "gaurav@example.com"
        assert "LangGraph" in result["skills"]
        assert result["github_username"] == "gauravtripathi"
        assert result["error"] is None

    def test_parse_node_adds_trace_step(self):
        state = base_state(str(self.candidate.id))
        result = parse_node(state)

        trace = result["trace_log"]
        assert len(trace) == 1
        assert trace[0]["step"] == "Parse"
        assert trace[0]["status"] == "done"

    def test_parse_node_handles_missing_candidate(self):
        state = base_state("00000000-0000-0000-0000-000000000000")
        result = parse_node(state)

        assert result["error"] is not None
        trace = result["trace_log"]
        assert trace[-1]["status"] == "error"


# ── Node 2: Research ─────────────────────────────────────────────

class TestResearchNode(TestCase):

    def setUp(self):
        self.candidate = make_candidate()

    @patch("agent.nodes.research_node.build_github_evidence")
    def test_research_node_with_github(self, mock_build):
        mock_build.return_value = {
            "username": "gauravtripathi",
            "has_original_work": True,
            "total_recent_commits": 47,
            "primary_languages": {"Python": 5000, "TypeScript": 2000},
            "repos_analysed": [{"name": "sales-engine", "is_fork": False, "stars": 12}],
        }

        state = base_state(
            str(self.candidate.id),
            github_username="gauravtripathi",
        )
        result = research_node(state)

        assert result["github_evidence"]["has_original_work"] is True
        assert result["github_evidence"]["total_recent_commits"] == 47
        assert result["trace_log"][-1]["status"] == "done"
        mock_build.assert_called_once_with("gauravtripathi")

    def test_research_node_skips_without_github(self):
        state = base_state(str(self.candidate.id), github_username="")
        result = research_node(state)

        assert result["github_evidence"]["skipped"] is True
        assert result["trace_log"][-1]["status"] == "done"

    @patch("agent.nodes.research_node.build_github_evidence")
    def test_research_node_handles_github_fetch_error(self, mock_build):
        from talentplus_ai.core.exceptions import GitHubFetchError
        mock_build.side_effect = GitHubFetchError("Rate limit exceeded")

        state = base_state(
            str(self.candidate.id),
            github_username="someuser",
        )
        result = research_node(state)

        assert "error" in result["github_evidence"]
        assert result["trace_log"][-1]["status"] == "error"
        # Should NOT set state["error"] — pipeline continues without evidence
        assert result.get("error") is None


# ── Node 3: Contextualize ────────────────────────────────────────

class TestContextualizeNode(TestCase):

    def setUp(self):
        self.candidate = make_candidate()
        self.team_profile = TeamProfile.objects.create(
            role="Senior Agentic AI Engineer",
            seniority_level="Senior",
            department="AI Platform",
            current_skills=["Python", "FastAPI"],
            missing_skills=["Rust", "Kubernetes"],
            culture_values=["ownership", "open-source contributor"],
            hiring_priority="High",
        )
        self.job = JobDescription.objects.create(
            title="Senior Agentic AI Engineer",
            department="AI Platform",
            team_profile=self.team_profile,
            description="Build agentic AI systems.",
            required_skills=["LangGraph", "FastMCP", "Python", "FastAPI"],
            preferred_skills=["TypeScript", "Kubernetes"],
            is_active=True,
        )

    def test_contextualize_finds_best_match(self):
        state = base_state(
            str(self.candidate.id),
            skills=["LangGraph", "FastMCP", "Python", "FastAPI", "Docker"],
        )
        result = contextualize_node(state)

        gap = result["gap_analysis"]
        assert gap["best_match_role"] == "Senior Agentic AI Engineer"
        assert "LangGraph" in gap["top_role_matches"][0]["required_skills_matched"]
        assert result["trace_log"][-1]["status"] == "done"

    def test_contextualize_no_active_jobs(self):
        JobDescription.objects.all().update(is_active=False)
        state = base_state(str(self.candidate.id), skills=["Python"])
        result = contextualize_node(state)

        assert result["gap_analysis"].get("no_active_roles") is True

    def test_contextualize_computes_critical_gaps(self):
        state = base_state(
            str(self.candidate.id),
            skills=["Python"],  # Missing LangGraph, FastMCP, FastAPI
        )
        result = contextualize_node(state)
        critical_gaps = result["gap_analysis"]["critical_gaps"]
        assert "LangGraph" in critical_gaps or "FastMCP" in critical_gaps


# ── Node 4: Score ────────────────────────────────────────────────

class TestScoreNode(TestCase):

    def setUp(self):
        self.candidate = make_candidate()

    @patch("agent.nodes.score_node.Anthropic")
    def test_score_node_parses_claude_response(self, mock_anthropic_cls):
        import json
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps({
            "overall_score": 92,
            "technical_score": 95,
            "culture_score": 88,
            "experience_score": 90,
            "candidate_label": "Strong Match",
            "reasoning": "Excellent LangGraph and FastMCP skills verified via GitHub.",
            "strengths": ["LangGraph expertise", "FastMCP real-world usage"],
            "weaknesses": ["No Kubernetes experience"],
            "recommendation": "Proceed to technical screening immediately.",
        })
        mock_client.messages.create.return_value = mock_response

        state = base_state(
            str(self.candidate.id),
            resume_text="LangGraph FastMCP Python FastAPI",
            github_evidence={"has_original_work": True, "total_recent_commits": 47},
            gap_analysis={"best_match_role": "Senior Agentic AI Engineer"},
        )
        result = score_node(state)

        assert result["score"] == 92
        assert result["technical_score"] == 95
        assert result["candidate_label"] == "Strong Match"
        assert "LangGraph" in result["reasoning"]
        assert result["trace_log"][-1]["status"] == "done"

    @patch("agent.nodes.score_node.Anthropic")
    def test_score_node_handles_invalid_json(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "This is not JSON at all."
        mock_client.messages.create.return_value = mock_response

        state = base_state(str(self.candidate.id))
        result = score_node(state)

        assert result["score"] == 0
        assert result["error"] is not None
        assert result["trace_log"][-1]["status"] == "error"

    @patch("agent.nodes.score_node.Anthropic")
    def test_score_node_strips_markdown_fences(self, mock_anthropic_cls):
        import json
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        valid_json = json.dumps({
            "overall_score": 75, "technical_score": 78, "culture_score": 72,
            "experience_score": 74, "candidate_label": "Hidden Gem",
            "reasoning": "Good.", "strengths": [], "weaknesses": [],
            "recommendation": "Consider.",
        })
        mock_response.content[0].text = f"```json\n{valid_json}\n```"
        mock_client.messages.create.return_value = mock_response

        state = base_state(str(self.candidate.id))
        result = score_node(state)

        assert result["score"] == 75
        assert result["candidate_label"] == "Hidden Gem"


# ── Node 5: DB ───────────────────────────────────────────────────

class TestDbNode(TestCase):

    def setUp(self):
        self.candidate = make_candidate()
        CandidateEvaluation.objects.create(
            candidate=self.candidate,
            status="pending",
            reasoning="Pending...",
        )

    def test_db_node_saves_evaluation(self):
        state = base_state(
            str(self.candidate.id),
            score=92,
            technical_score=95,
            culture_score=88,
            experience_score=90,
            reasoning="Strong candidate with verified GitHub.",
            github_evidence={"has_original_work": True},
            gap_analysis={"best_match_role": "Senior AI Engineer"},
            trace_log=[{"step": "Parse", "message": "Done", "status": "done"}],
        )
        result = db_node(state)

        evaluation = CandidateEvaluation.objects.get(candidate=self.candidate)
        assert evaluation.score == 92
        assert evaluation.status == "screening_sent"
        assert evaluation.email_sent is False
        assert result["trace_log"][-1]["status"] == "done"

    def test_db_node_sets_rejected_status_for_low_score(self):
        state = base_state(
            str(self.candidate.id),
            score=45,
            reasoning="Does not meet requirements.",
            trace_log=[],
        )
        db_node(state)

        evaluation = CandidateEvaluation.objects.get(candidate=self.candidate)
        assert evaluation.status == "rejected"

    def test_db_node_sets_borderline_status(self):
        state = base_state(
            str(self.candidate.id),
            score=65,
            reasoning="Good but borderline.",
            trace_log=[],
        )
        db_node(state)

        evaluation = CandidateEvaluation.objects.get(candidate=self.candidate)
        assert evaluation.status == "borderline"


# ── Node 6: Email ────────────────────────────────────────────────

class TestEmailNode(TestCase):

    def setUp(self):
        self.candidate = make_candidate()
        CandidateEvaluation.objects.create(
            candidate=self.candidate,
            status="screening_sent",
            reasoning="Strong.",
            score=92,
        )

    @patch("agent.nodes.email_node.resend.Emails.send")
    def test_email_node_sends_screening_for_high_score(self, mock_send):
        mock_send.return_value = {"id": "email_abc123"}

        state = base_state(
            str(self.candidate.id),
            score=92,
            email="gaurav@example.com",
            name="Gaurav Tripathi",
            github_username="gauravtripathi",
            gap_analysis={"best_match_role": "Senior Agentic AI Engineer"},
            candidate_label="Strong Match",
        )
        result = email_node(state)

        assert result["email_status"] == "sent"
        assert result["trace_log"][-1]["status"] == "done"
        mock_send.assert_called_once()

        call_args = mock_send.call_args[0][0]
        assert "gaurav@example.com" in call_args["to"]
        assert "shortlisted" in call_args["subject"].lower()

    @patch("agent.nodes.email_node.resend.Emails.send")
    def test_email_node_sends_rejection_for_low_score(self, mock_send):
        mock_send.return_value = {"id": "email_rej456"}

        state = base_state(
            str(self.candidate.id),
            score=40,
            email="gaurav@example.com",
            name="Gaurav Tripathi",
            gap_analysis={"best_match_role": "Senior AI Engineer", "critical_gaps": ["LangGraph"]},
        )
        result = email_node(state)

        assert result["email_status"] == "sent"
        call_args = mock_send.call_args[0][0]
        assert "gaurav@example.com" in call_args["to"]

    def test_email_node_skips_borderline_score(self):
        state = base_state(
            str(self.candidate.id),
            score=68,
            email="gaurav@example.com",
        )
        result = email_node(state)

        assert result["email_status"] == "skipped"
        assert "borderline" in result["trace_log"][-1]["message"].lower()

    def test_email_node_skips_missing_email(self):
        state = base_state(str(self.candidate.id), score=95, email="")
        result = email_node(state)
        assert result["email_status"] == "skipped"

    @patch("agent.nodes.email_node.resend.Emails.send")
    def test_email_node_handles_send_failure(self, mock_send):
        mock_send.side_effect = Exception("Resend API unavailable")

        state = base_state(
            str(self.candidate.id),
            score=93,
            email="gaurav@example.com",
            name="Gaurav",
        )
        result = email_node(state)

        assert result["email_status"] == "failed"
        assert result["trace_log"][-1]["status"] == "error"


# ── Graph Routing ────────────────────────────────────────────────

class TestGraphRouting(TestCase):

    def test_should_send_email_high_score(self):
        from talentplus_ai.agent.graph import should_send_email
        state = base_state("fake-id", score=92)
        assert should_send_email(state) == "email"

    def test_should_send_email_low_score(self):
        from talentplus_ai.agent.graph import should_send_email
        state = base_state("fake-id", score=45)
        assert should_send_email(state) == "email"

    def test_should_send_email_borderline(self):
        from talentplus_ai.agent.graph import should_send_email
        state = base_state("fake-id", score=65)
        assert should_send_email(state) == "end"

    def test_should_send_email_above_borderline_band(self):
        from talentplus_ai.agent.graph import should_send_email
        state = base_state("fake-id", score=72)
        assert should_send_email(state) == "email"

    def test_should_send_email_error_skips(self):
        from talentplus_ai.agent.graph import should_send_email
        state = base_state("fake-id", score=95, error="Something broke")
        assert should_send_email(state) == "end"

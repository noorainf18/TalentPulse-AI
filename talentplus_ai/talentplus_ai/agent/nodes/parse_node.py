"""
Node 1 — Parse
Reads the Candidate DB record and populates AgentState with all
structured fields already extracted by Docling + Claude at upload time.

IMPORTANT — skills shape:
  candidate.skills in the DB is [{category, skills[]}] (categorized, for the UI).
  But everything downstream in the agent (contextualize_node, score_node) needs
  a flat list of skill strings for string comparison and gap analysis.
  parse_node flattens it here so all downstream nodes get a plain list[str].

LangGraph contract:
  Input:  AgentState (with candidate_id populated)
  Output: AgentState (with name, email, skills as flat list[str], etc. populated)
"""

import logging
from talentplus_ai.agent.state import AgentState

logger = logging.getLogger(__name__)


def _flatten_skills(skills_field) -> list:
    """
    Accepts either:
      - [{category: str, skills: [str, ...]}]  <- new categorized shape from DB
      - [str, ...]                              <- old flat shape (legacy records)

    Always returns a flat list[str].
    """
    if not skills_field:
        return []

    flat = []
    for item in skills_field:
        if isinstance(item, dict):
            # New categorized shape: extract the skills list from each group
            for skill in (item.get("skills") or []):
                if isinstance(skill, str) and skill.strip():
                    flat.append(skill.strip())
        elif isinstance(item, str) and item.strip():
            # Old flat shape: use as-is
            flat.append(item.strip())

    return flat


def parse_node(state: AgentState) -> AgentState:
    """
    Reads the Candidate record from the database and populates
    all structured fields into AgentState.
    """
    logger.info("[parse_node] Starting for candidate %s", state["candidate_id"])

    trace = list(state.get("trace_log", []))
    trace.append({
        "step": "Parse",
        "message": "Reading candidate profile from database...",
        "status": "running",
    })

    try:
        from talentplus_ai.candidates.models import Candidate

        candidate = Candidate.objects.get(id=state["candidate_id"])

        name            = candidate.name
        email           = candidate.email
        github_url      = candidate.github_url or ""
        github_username = candidate.raw_github_username or ""
        portfolio_url   = candidate.portfolio_url or ""
        linkedin_url    = candidate.linkedin_url or ""
        summary         = candidate.summary or ""
        experience      = candidate.experience or []
        projects        = candidate.projects or []
        education       = candidate.education or []

        # Flatten categorized skills [{category, skills[]}] → plain list[str]
        # The categorized shape lives in the DB for the UI.
        # Agent nodes (contextualize, score) need a flat list for string matching.
        skills = _flatten_skills(candidate.skills)

        trace[-1] = {
            "step": "Parse",
            "message": (
                f"Loaded {len(skills)} skills, "
                f"{len(experience)} experience entries, "
                f"{len(projects)} projects. "
                f"GitHub: {github_username or 'not found'}."
            ),
            "status": "done",
        }

        logger.info(
            "[parse_node] Done — skills=%d (flat), experience=%d, projects=%d, github=%s",
            len(skills), len(experience), len(projects), github_username,
        )

        return {
            **state,
            "name":            name,
            "email":           email,
            "skills":          skills,   # flat list[str] — safe for all downstream nodes
            "github_url":      github_url,
            "github_username": github_username,
            "portfolio_url":   portfolio_url,
            "summary":         summary,
            "experience":      experience,
            "projects":        projects,
            "education":       education,
            "trace_log":       trace,
            "error":           None,
        }

    except Exception as exc:
        error_msg = f"Parse node failed: {exc}"
        logger.error("[parse_node] %s", error_msg)
        trace[-1] = {"step": "Parse", "message": error_msg, "status": "error"}
        return {**state, "trace_log": trace, "error": error_msg}
"""
Node 3 — Contextualize
Queries TeamProfile and JobDescription tables to find:
  1. Which open roles best match the candidate's skills
  2. What the required and preferred skill gaps are
  3. Whether the candidate fills a gap the team explicitly lacks

Returns a structured gap_analysis dict that score_node passes to Claude.

LangGraph contract:
  Input:  AgentState (with skills as flat list[str] populated by parse_node)
  Output: AgentState (with gap_analysis populated)
"""

import logging
from talentplus_ai.agent.state import AgentState

logger = logging.getLogger(__name__)


def _compute_skill_overlap(
    candidate_skills: list, role_skills: list
) -> tuple:
    """
    Returns (matched, missing, coverage_score_0_to_1).
    Case-insensitive. Safely skips any non-string values.
    """
    if not role_skills:
        return [], [], 0.0

    # Guard: only compare string values — skip dicts or anything else
    candidate_lower = {
        s.lower() for s in candidate_skills if isinstance(s, str)
    }

    matched = [s for s in role_skills if isinstance(s, str) and s.lower() in candidate_lower]
    missing = [s for s in role_skills if isinstance(s, str) and s.lower() not in candidate_lower]
    score = len(matched) / len(role_skills) if role_skills else 0.0

    return matched, missing, score


def contextualize_node(state: AgentState) -> AgentState:
    """
    Scores the candidate against every active JobDescription and
    builds a gap_analysis dict ranked by best fit.
    """
    logger.info("[contextualize_node] Starting for candidate %s", state["candidate_id"])

    trace = list(state.get("trace_log", []))
    trace.append({
        "step": "Contextualize",
        "message": "Comparing candidate skills against team profiles and open roles...",
        "status": "running",
    })

    # skills is a flat list[str] — guaranteed by parse_node._flatten_skills()
    candidate_skills = state.get("skills", [])

    try:
        from talentplus_ai.candidates.models import JobDescription

        active_jobs = list(
            JobDescription.objects.filter(is_active=True).select_related("team_profile")
        )

        if not active_jobs:
            trace[-1] = {
                "step": "Contextualize",
                "message": "No active job descriptions found. Using general evaluation.",
                "status": "done",
            }
            return {
                **state,
                "gap_analysis": {"no_active_roles": True},
                "trace_log": trace,
            }

        role_matches = []

        for job in active_jobs:
            required  = job.required_skills or []
            preferred = job.preferred_skills or []
            team      = job.team_profile

            req_matched,  req_missing,  req_score  = _compute_skill_overlap(candidate_skills, required)
            pref_matched, pref_missing, pref_score = _compute_skill_overlap(candidate_skills, preferred)

            # Does this candidate cover a skill the team explicitly lists as missing?
            team_missing = team.missing_skills if team else []
            candidate_lower = {s.lower() for s in candidate_skills if isinstance(s, str)}
            fills_team_gap = any(
                g.lower() in candidate_lower
                for g in team_missing
                if isinstance(g, str)
            )

            # Overall fit: required coverage weighted more heavily than preferred.
            # Culture alignment is handled by Claude in score_node with full evidence.
            overall_fit = round((req_score * 0.70) + (pref_score * 0.30), 2)

            role_matches.append({
                "job_id":                   job.id,
                "role_title":               job.title,
                "department":               job.department,
                "seniority":                team.seniority_level if team else "Unknown",
                "hiring_priority":          team.hiring_priority if team else "Unknown",
                "required_skills_matched":  req_matched,
                "required_skills_missing":  req_missing,
                "preferred_skills_matched": pref_matched,
                "preferred_skills_missing": pref_missing,
                "culture_values":           team.culture_values if team else [],
                "required_skill_coverage":  round(req_score, 2),
                "preferred_skill_coverage": round(pref_score, 2),
                "overall_fit_score":        overall_fit,
                "fills_critical_team_gap":  fills_team_gap,
                "min_experience_years":     team.min_experience_years if team else 0,
                "tech_stack_focus":         team.tech_stack_focus if team else "",
            })

        # Rank by fit score descending, take top 3
        role_matches.sort(key=lambda x: x["overall_fit_score"], reverse=True)
        top_matches = role_matches[:3]
        best = top_matches[0] if top_matches else {}

        gap_analysis = {
            "candidate_skills":      candidate_skills,
            "best_match_role":       best.get("role_title", "N/A"),
            "best_match_department": best.get("department", "N/A"),
            "best_match_fit_score":  best.get("overall_fit_score", 0),
            "top_role_matches":      top_matches,
            "critical_gaps":         best.get("required_skills_missing", []),
            "nice_to_have_gaps":     best.get("preferred_skills_missing", []),
            "fills_team_gap":        best.get("fills_critical_team_gap", False),
        }

        summary = (
            f"Best role match: {best.get('role_title', 'N/A')} "
            f"(fit: {best.get('overall_fit_score', 0):.0%}). "
            f"Critical gaps: {', '.join(best.get('required_skills_missing', [])[:3]) or 'None'}."
        )

        trace[-1] = {"step": "Contextualize", "message": summary, "status": "done"}
        logger.info("[contextualize_node] %s", summary)

        return {
            **state,
            "gap_analysis": gap_analysis,
            "trace_log":    trace,
        }

    except Exception as exc:
        error_msg = f"Contextualize node failed: {exc}"
        logger.error("[contextualize_node] %s", error_msg)
        trace[-1] = {"step": "Contextualize", "message": error_msg, "status": "error"}
        return {**state, "gap_analysis": {}, "trace_log": trace, "error": error_msg}
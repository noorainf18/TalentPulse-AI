"""
MCP Tool 2 — culture_fit_check
File:   mcp_tools/culture_fit_check.py
Folder: mcp_tools/

Queries TeamProfile and JobDescription tables in Supabase to find which
open roles best match a candidate's skills and returns a structured gap analysis.

This tool exposes the same logic as agent/nodes/contextualize_node.py over
the MCP protocol, allowing any external MCP-compatible client to call it
without going through the full agent pipeline.

Input:  candidate_skills — list of technology/framework name strings
Output: gap analysis dict with role matches, critical gaps, fit scores

Fix applied:
  Fit score weights updated from (req * 0.65) + (pref * 0.35)
  to (req * 0.70) + (pref * 0.30) to stay consistent with
  the weights used in agent/nodes/contextualize_node.py.
  Both files compute the same thing and must stay in sync.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def culture_fit_check(candidate_skills: List[str]) -> dict:
    """
    Queries Django ORM (reads from Supabase Postgres) and returns
    gap analysis across all active job descriptions.

    Example:
        culture_fit_check(["LangGraph", "FastMCP", "Python", "FastAPI"])
        → {
            "best_match_role": "Senior Agentic AI Engineer",
            "best_match_fit_score": 0.91,
            "critical_gaps": [],
            "fills_critical_team_gap": True,
            "top_matches": [...]
          }
    """
    logger.info("[culture_fit_check] Checking %d skills against open roles.", len(candidate_skills))

    if not candidate_skills:
        return {"error": "candidate_skills list is empty."}

    try:
        from talentplus_ai.candidates.models import TeamProfile, JobDescription

        active_jobs = list(
            JobDescription.objects.filter(is_active=True).select_related("team_profile")
        )

        if not active_jobs:
            return {
                "status": "no_active_roles",
                "message": "No active job descriptions found in the system.",
            }

        candidate_lower = {s.lower() for s in candidate_skills}
        results = []

        for job in active_jobs:
            team      = job.team_profile
            required  = job.required_skills or []
            preferred = job.preferred_skills or []
            team_missing = team.missing_skills if team else []

            req_matched  = [s for s in required  if s.lower() in candidate_lower]
            req_missing  = [s for s in required  if s.lower() not in candidate_lower]
            pref_matched = [s for s in preferred if s.lower() in candidate_lower]
            pref_missing = [s for s in preferred if s.lower() not in candidate_lower]

            fills_team_gap = any(gap.lower() in candidate_lower for gap in team_missing)

            req_coverage  = len(req_matched)  / len(required)  if required  else 0.0
            pref_coverage = len(pref_matched) / len(preferred) if preferred else 0.0

            # Weights aligned with contextualize_node.py: req=0.70, pref=0.30
            overall_fit = round((req_coverage * 0.70) + (pref_coverage * 0.30), 2)

            results.append({
                "job_id":                    job.id,
                "role_title":                job.title,
                "department":                job.department,
                "seniority":                 team.seniority_level if team else "Unknown",
                "hiring_priority":           team.hiring_priority if team else "Unknown",
                "employment_type":           job.employment_type,
                "location":                  job.location,
                "salary_range_lpa":          job.salary_range_lpa,
                "required_experience_years": job.required_experience_years,
                "tech_stack_focus":          team.tech_stack_focus if team else "",
                "culture_values":            team.culture_values if team else [],
                "required_skills_matched":   req_matched,
                "required_skills_missing":   req_missing,
                "preferred_skills_matched":  pref_matched,
                "preferred_skills_missing":  pref_missing,
                "fills_critical_team_gap":   fills_team_gap,
                "required_skill_coverage":   round(req_coverage, 2),
                "preferred_skill_coverage":  round(pref_coverage, 2),
                "overall_fit_score":         overall_fit,
            })

        results.sort(key=lambda x: x["overall_fit_score"], reverse=True)
        best = results[0] if results else {}

        return {
            "candidate_skills_provided":  candidate_skills,
            "total_roles_checked":        len(results),
            "best_match_role":            best.get("role_title", "N/A"),
            "best_match_department":      best.get("department", "N/A"),
            "best_match_fit_score":       best.get("overall_fit_score", 0),
            "best_match_hiring_priority": best.get("hiring_priority", "N/A"),
            "top_matches":                results[:3],
            "critical_gaps":              best.get("required_skills_missing", []),
            "nice_to_have_gaps":          best.get("preferred_skills_missing", []),
            "fills_critical_team_gap":    best.get("fills_critical_team_gap", False),
            "recommended_role":           best.get("role_title", "N/A"),
        }

    except Exception as exc:
        logger.error("[culture_fit_check] Failed: %s", exc)
        return {"error": f"culture_fit_check failed: {exc}"}
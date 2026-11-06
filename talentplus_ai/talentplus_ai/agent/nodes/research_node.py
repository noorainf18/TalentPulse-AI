"""
Node 2 — Research
Calls the FastMCP github_researcher tool to analyse the candidate's
GitHub repos. Stores structured evidence in AgentState.
"""

import logging
from talentplus_ai.agent.state import AgentState
from talentplus_ai.core.github_utils import build_github_evidence
from talentplus_ai.core.exceptions import GitHubFetchError

logger = logging.getLogger(__name__)


def research_node(state: AgentState) -> AgentState:
    """
    Fetches GitHub evidence for the candidate.
    Gracefully handles missing GitHub profiles — many strong candidates
    may not have a public GitHub username on their resume.
    """
    logger.info(f"[research_node] Starting for candidate {state['candidate_id']}")

    trace = list(state.get("trace_log", []))
    github_username = state.get("github_username", "")

    if not github_username:
        logger.info("[research_node] No GitHub username found. Skipping GitHub research.")
        trace.append({
            "step": "Research",
            "message": "No GitHub profile linked. Skipping repository analysis.",
            "status": "done",
        })
        return {
            **state,
            "github_evidence": {"skipped": True, "reason": "No GitHub username found in resume."},
            "trace_log": trace,
        }

    trace.append({
        "step": "Research",
        "message": f"Analysing GitHub profile: github.com/{github_username}...",
        "status": "running",
    })

    try:
        evidence = build_github_evidence(github_username)

        repos_count = len(evidence.get("repos_analysed", []))
        recent_commits = evidence.get("total_recent_commits", 0)
        has_original = evidence.get("has_original_work", False)
        languages = list(evidence.get("primary_languages", {}).keys())

        summary = (
            f"Analysed {repos_count} repos. "
            f"{recent_commits} commits in last 90 days. "
            f"Original work: {'Yes' if has_original else 'No'}. "
            f"Top languages: {', '.join(languages[:3]) or 'None detected'}."
        )

        trace[-1] = {"step": "Research", "message": summary, "status": "done"}

        logger.info(f"[research_node] Done — {summary}")

        return {
            **state,
            "github_evidence": evidence,
            "trace_log": trace,
        }

    except GitHubFetchError as e:
        logger.warning(f"[research_node] GitHub fetch failed: {e}")
        trace[-1] = {
            "step": "Research",
            "message": f"GitHub analysis failed: {str(e)}. Proceeding without evidence.",
            "status": "error",
        }
        return {
            **state,
            "github_evidence": {"error": str(e), "username": github_username},
            "trace_log": trace,
        }

    except Exception as e:
        error_msg = f"Unexpected error in research_node: {str(e)}"
        logger.error(f"[research_node] {error_msg}")
        trace[-1] = {"step": "Research", "message": error_msg, "status": "error"}
        return {**state, "github_evidence": {}, "trace_log": trace, "error": error_msg}

"""
MCP Tool 1 — github_researcher
Verifies candidate skill claims by analysing their top GitHub repositories.

Input:  username (str), repo_name (str, optional)
Output: README summary, commit history, primary languages, code quality assessment
"""

import logging
from core.github_utils import build_github_evidence, fetch_repo_readme, fetch_repo_languages, fetch_commit_stats
from core.exceptions import GitHubFetchError

logger = logging.getLogger(__name__)


def github_researcher(username: str, repo_name: str = "") -> dict:
    """
    FastMCP tool function.
    If repo_name is provided, analyses that single repo in detail.
    Otherwise analyses the user's top 3 repos.
    """
    logger.info(f"[github_researcher] username={username}, repo_name={repo_name or 'top repos'}")

    if not username:
        return {"error": "username is required."}

    # Single repo deep-dive
    if repo_name:
        try:
            readme = fetch_repo_readme(username, repo_name)
            languages = fetch_repo_languages(username, repo_name)
            commits = fetch_commit_stats(username, repo_name)

            top_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
            primary_language = top_langs[0][0] if top_langs else "Unknown"

            recent = commits.get("recent_commits_90_days", 0)
            total = commits.get("total_commits_fetched", 0)
            messages = commits.get("sample_messages", [])

            quality_signals = []
            if recent > 10:
                quality_signals.append("Active contributor (10+ commits in last 90 days)")
            if readme and len(readme) > 300:
                quality_signals.append("Well-documented README")
            if len(languages) > 2:
                quality_signals.append("Multi-language repository")
            if not quality_signals:
                quality_signals.append("Low recent activity or minimal documentation")

            return {
                "username": username,
                "repo_name": repo_name,
                "primary_language": primary_language,
                "all_languages": dict(top_langs[:5]),
                "readme_summary": readme[:800] if readme else "No README found.",
                "recent_commits_90_days": recent,
                "total_commits_fetched": total,
                "sample_commit_messages": messages,
                "code_quality_signals": quality_signals,
            }
        except GitHubFetchError as e:
            return {"error": str(e), "username": username, "repo_name": repo_name}

    # Multi-repo overview
    return build_github_evidence(username)
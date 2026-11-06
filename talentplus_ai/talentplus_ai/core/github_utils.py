"""
GitHub API Utilities
Shared helpers used by both:
  - mcp_tools/github_researcher.py  (the MCP tool)
  - agent/nodes/research_node.py    (the LangGraph node)

Handles: rate-limiting, auth headers, repo fetching, commit history.
"""

import logging
import time
from typing import Optional
from django.conf import settings
import httpx

from talentplus_ai.core.exceptions import GitHubFetchError

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def _get_headers() -> dict:
    token = getattr(settings, "GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _make_request(url: str) -> dict:
    """
    Makes a GET request to the GitHub API with retry logic
    and rate-limit handling.
    """
    headers = _get_headers()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = httpx.get(url, headers=headers, timeout=15.0)

            if response.status_code == 403:
                reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset_time - int(time.time()), 5)
                logger.warning(f"GitHub rate limit hit. Waiting {wait}s...")
                time.sleep(min(wait, 60))
                continue

            if response.status_code == 404:
                raise GitHubFetchError(f"Resource not found: {url}")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API HTTP error (attempt {attempt}): {e}")
            if attempt == MAX_RETRIES:
                raise GitHubFetchError(f"GitHub API failed after {MAX_RETRIES} attempts: {e}")
            time.sleep(RETRY_DELAY * attempt)

        except httpx.RequestError as e:
            logger.error(f"GitHub API request error (attempt {attempt}): {e}")
            if attempt == MAX_RETRIES:
                raise GitHubFetchError(f"Network error reaching GitHub: {e}")
            time.sleep(RETRY_DELAY * attempt)

    raise GitHubFetchError("GitHub API request exhausted all retries.")


def fetch_user_repos(username: str, max_repos: int = 5) -> list:
    """
    Returns the top N public repos for a user, sorted by stars + recent push.
    Excludes forks to focus on original work.
    """
    url = f"{GITHUB_API_BASE}/users/{username}/repos?sort=pushed&per_page=20&type=public"
    repos = _make_request(url)

    if not isinstance(repos, list):
        raise GitHubFetchError(f"Unexpected response shape for user repos: {username}")

    # Filter out pure forks, prioritise original work
    original = [r for r in repos if not r.get("fork", False)]
    forked = [r for r in repos if r.get("fork", False)]

    # Use original repos first, fill with forks only if needed
    ranked = (original + forked)[:max_repos]
    return ranked


def fetch_repo_readme(username: str, repo_name: str) -> str:
    """Returns decoded README content, or empty string if not found."""
    import base64
    url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/readme"
    try:
        data = _make_request(url)
        content = data.get("content", "")
        encoding = data.get("encoding", "base64")
        if encoding == "base64" and content:
            return base64.b64decode(content).decode("utf-8", errors="replace")[:3000]
    except GitHubFetchError:
        pass
    return ""


def fetch_repo_languages(username: str, repo_name: str) -> dict:
    """Returns {language: bytes_count} dict for a repo."""
    url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/languages"
    try:
        return _make_request(url)
    except GitHubFetchError:
        return {}


def fetch_commit_stats(username: str, repo_name: str, max_commits: int = 30) -> dict:
    """
    Returns:
      total_commits, recent_commit_count (last 90 days),
      unique_authors, sample_messages
    """
    url = f"{GITHUB_API_BASE}/repos/{username}/{repo_name}/commits?per_page={max_commits}"
    try:
        commits = _make_request(url)
    except GitHubFetchError:
        return {"total_commits": 0, "recent_commits": 0, "sample_messages": []}

    if not isinstance(commits, list):
        return {}

    now = time.time()
    ninety_days_ago = now - (90 * 86400)
    recent = 0
    messages = []

    for c in commits:
        commit_data = c.get("commit", {})
        date_str = commit_data.get("author", {}).get("date", "")
        if date_str:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if dt.timestamp() >= ninety_days_ago:
                    recent += 1
            except ValueError:
                pass
        msg = commit_data.get("message", "").split("\n")[0][:100]
        if msg:
            messages.append(msg)

    return {
        "total_commits_fetched": len(commits),
        "recent_commits_90_days": recent,
        "sample_messages": messages[:5],
    }


def build_github_evidence(username: str) -> dict:
    """
    Top-level function called by github_researcher MCP tool.
    Analyses up to 3 repos and returns structured evidence.
    """
    logger.info(f"Building GitHub evidence for: {username}")

    try:
        repos = fetch_user_repos(username, max_repos=3)
    except GitHubFetchError as e:
        return {"error": str(e), "username": username}

    evidence = {
        "username": username,
        "profile_url": f"https://github.com/{username}",
        "repos_analysed": [],
        "primary_languages": {},
        "has_original_work": False,
        "total_recent_commits": 0,
    }

    all_languages: dict = {}

    for repo in repos:
        repo_name = repo.get("name", "")
        is_fork = repo.get("fork", False)
        stars = repo.get("stargazers_count", 0)
        description = repo.get("description", "") or ""

        readme = fetch_repo_readme(username, repo_name)
        languages = fetch_repo_languages(username, repo_name)
        commits = fetch_commit_stats(username, repo_name)

        # Accumulate language totals
        for lang, count in languages.items():
            all_languages[lang] = all_languages.get(lang, 0) + count

        recent = commits.get("recent_commits_90_days", 0)
        evidence["total_recent_commits"] += recent

        if not is_fork:
            evidence["has_original_work"] = True

        evidence["repos_analysed"].append({
            "name": repo_name,
            "is_fork": is_fork,
            "stars": stars,
            "description": description[:200],
            "languages": languages,
            "readme_snippet": readme[:500] if readme else "",
            "commits": commits,
        })

    # Rank languages by byte count
    sorted_langs = sorted(all_languages.items(), key=lambda x: x[1], reverse=True)
    evidence["primary_languages"] = {k: v for k, v in sorted_langs[:5]}

    logger.info(
        f"GitHub evidence built for {username}: "
        f"{len(evidence['repos_analysed'])} repos, "
        f"{evidence['total_recent_commits']} recent commits"
    )

    return evidence

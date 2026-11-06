"""
FastMCP Server — TalentPulse
File:   mcp_tools/server.py
Folder: mcp_tools/

Registers all 3 MCP tools and exposes them over the MCP HTTP transport.
Mounted at /mcp/ via mcp_tools/urls.py → config/urls.py.

Tools registered:
  1. github_researcher  — verify GitHub skill claims via GitHub API
  2. culture_fit_check  — gap analysis against open roles in Supabase
  3. email_sender       — send personalised candidate outreach via Resend

Fix applied:
  The original code called django.setup() unconditionally at module level.
  When Django imports this file (via mcp_tools/urls.py at startup),
  django.setup() would be called a second time, raising AppRegistryNotReady.
  Fixed by guarding the call with django.apps.apps.ready.
"""

import os
import django

# Guard: only call django.setup() if Django has not already been initialised.
# Without this guard, importing server.py during Django startup (via urls.py)
# triggers a double django.setup() call → AppRegistryNotReady error.
if not django.apps.apps.ready:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    django.setup()

from fastmcp import FastMCP
from mcp_tools.github_researcher import github_researcher
from mcp_tools.culture_fit_check import culture_fit_check
from mcp_tools.email_sender import email_sender

# ── Instantiate the MCP server ──────────────────────────────────
mcp = FastMCP(
    name="TalentPulse",
    description=(
        "Autonomous AI recruiting tools for verifying candidate claims, "
        "analysing team skill gaps, and sending personalised outreach emails."
    ),
)


# ── Tool 1: GitHub Researcher ───────────────────────────────────
@mcp.tool(
    name="github_researcher",
    description=(
        "Verifies a candidate's skill claims by analysing their GitHub repositories. "
        "Returns README summaries, commit history, primary languages, and code quality signals. "
        "Pass username only for a multi-repo overview, or include repo_name for a single-repo deep-dive."
    ),
)
def github_researcher_tool(username: str, repo_name: str = "") -> dict:
    return github_researcher(username=username, repo_name=repo_name)


# ── Tool 2: Culture Fit Check ───────────────────────────────────
@mcp.tool(
    name="culture_fit_check",
    description=(
        "Queries the team's open roles and skill gaps in Supabase. "
        "Returns which roles best match the candidate's skills, what the critical gaps are, "
        "and whether the candidate fills a skill the team is currently missing."
    ),
)
def culture_fit_check_tool(candidate_skills: list) -> dict:
    return culture_fit_check(candidate_skills=candidate_skills)


# ── Tool 3: Email Sender ────────────────────────────────────────
@mcp.tool(
    name="email_sender",
    description=(
        "Sends a personalised email to a candidate via Resend. "
        "Use email_type='screening' for interview invitations or 'rejection' for feedback-rich rejections. "
        "Returns a confirmation status and Resend email ID."
    ),
)
def email_sender_tool(
    to_email: str,
    subject: str,
    body: str,
    email_type: str = "custom",
) -> dict:
    return email_sender(
        to_email=to_email,
        subject=subject,
        body=body,
        email_type=email_type,
    )
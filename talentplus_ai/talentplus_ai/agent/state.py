"""
AgentState — the shared state dict that flows through every
LangGraph node in the screening pipeline.

Change from original:
  - Replaced `resume_text: str` with `evaluation_id: str`
    Resume text is no longer passed through the graph. parse_node reads
    from the Candidate DB record directly. evaluation_id is needed so
    db_node can update the *correct* CandidateEvaluation row (since the
    model changed from OneToOneField → ForeignKey, a candidate can now
    have multiple evaluations for different roles).

  - Removed `voice_for_strong` and `voice_trigger` fields.
    The VOICE_FOR_STRONG_CANDIDATES flag has been removed. Voice screening
    is now triggered for all candidates with score >= VOICE_SCORE_THRESHOLD
    (default 60). There is no longer a "strong optional" path.
"""

from typing import TypedDict, Optional, Any


class TraceStep(TypedDict):
    step: str        # e.g. "Parse", "Research", "Score"
    message: str     # Human-readable status message
    status: str      # "done" | "running" | "error"


class AgentState(TypedDict):
    # ── Input ──────────────────────────────────────────────────
    candidate_id: str
    evaluation_id: str          # replaces resume_text — targets the specific evaluation row

    # ── Extracted by parse_node ────────────────────────────────
    name: str
    email: str
    skills: list[str]
    github_url: Optional[str]
    github_username: Optional[str]
    portfolio_url: Optional[str]

    # ── Extra fields read from flat model columns ───────────────
    summary: Optional[str]
    experience: Optional[list]
    projects: Optional[list]
    education: Optional[list]

    # ── Populated by research_node ─────────────────────────────
    github_evidence: Optional[dict[str, Any]]

    # ── Populated by contextualize_node ────────────────────────
    gap_analysis: Optional[dict[str, Any]]

    # ── Populated by score_node ────────────────────────────────
    score: int
    technical_score: int
    culture_score: int
    experience_score: int
    reasoning: str
    candidate_label: str   # e.g. "Hidden Gem", "Strong Match", "Not a Fit"

    # ── Populated by email_node ────────────────────────────────
    email_status: str      # "sent" | "failed" | "skipped"

    # ── Voice screening (voice_node + async Celery) ─────────────
    # Scores >= VOICE_SCORE_THRESHOLD (default 60) are routed to voice screening.
    # Scores 50–59 are borderline (HITL — on hold).
    # Scores < 50 are rejected immediately via email_node.
    voice_interview_id: Optional[str]        # set when interview row exists (usually async)
    voice_interview_scheduled: bool          # True if schedule_voice_screen was enqueued

    # ── Audit trail ────────────────────────────────────────────
    trace_log: list[TraceStep]
    error: Optional[str]
import json
import logging

from anthropic import Anthropic
from django.conf import settings
from talentplus_ai.candidates.models import Candidate, CandidateEvaluation, JobDescription
from talentplus_ai.candidates.models import TeamProfile
from ..models import VoiceInterview, VoiceQuestion
from ..prompts.question_generation_prompt import (
    STRUCTURED_OUTPUTS_BETA,
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    VOICE_QUESTIONS_RESPONSE_SCHEMA,
)

logger = logging.getLogger(__name__)

_anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


class VoiceQuestionBuilder:
    """
    Generates a structured set of interview questions for a VoiceInterview
    using Claude. Questions are grounded in:
      - The candidate's gap_analysis from their CandidateEvaluation
      - The matched JobDescription and TeamProfile (BOTH OPTIONAL — null-safe)
      - The candidate's parsed resume fields (structured JSONFields only;
        the Candidate model has NO resume_text column)

    Null-safety contract
    --------------------
    job_description is None when the candidate was submitted against the
    "General" role (no specific JD selected in the UI). This is a normal,
    expected scenario — NOT an error. Likewise, team_profile can be None
    even when a JD exists if no TeamProfile FK is set on it.

    Both cases have full fallback logic so Claude always receives a
    complete, well-formed prompt and question generation always succeeds.

    Output: VoiceQuestion rows persisted to the DB, ready for VoiceOrchestrator.
    Uses Anthropic Structured Outputs (same pattern as score_node / pdf_parser).
    """

    def build(self, interview: VoiceInterview) -> list[VoiceQuestion]:
        """
        Main entry point. Fetches all context, calls Claude, persists questions.
        Returns the list of created VoiceQuestion objects (may be empty on
        Claude failure — caller should check and handle accordingly).
        """
        evaluation      = interview.evaluation
        candidate       = interview.candidate
        job_description = interview.job_description  # JobDescription | None

        # Resolve team_profile only when a JD is present.
        team_profile = None
        if job_description is not None and hasattr(job_description, "team_profile"):
            team_profile = job_description.team_profile  # TeamProfile | None

        if job_description is None:
            logger.warning(
                "[VoiceQuestionBuilder] No JobDescription linked to VoiceInterview %s. "
                "Falling back to candidate-derived generic questions.",
                interview.id,
            )
        if team_profile is None:
            logger.warning(
                "[VoiceQuestionBuilder] No TeamProfile available for VoiceInterview %s. "
                "Falling back to generic team context.",
                interview.id,
            )

        user_message = self._build_user_message(
            candidate=candidate,
            evaluation=evaluation,
            job_description=job_description,
            team_profile=team_profile,
        )

        logger.info(
            "[VoiceQuestionBuilder] Calling Claude to generate questions for interview %s",
            interview.id,
        )
        questions_data = self._call_claude_structured(user_message)

        if not questions_data:
            logger.error(
                "[VoiceQuestionBuilder] No questions returned by Claude for interview %s. "
                "Returning empty list — tasks.py will mark interview as FAILED.",
                interview.id,
            )
            return []

        created_questions = []
        for q_data in questions_data:
            question = VoiceQuestion.objects.create(
                interview=interview,
                question_text=q_data.get("question_text", ""),
                question_type=q_data.get("question_type", "role_technical"),
                target_skill=q_data.get("target_skill", ""),
                sequence_order=q_data.get("sequence_order", 0),
                expected_answer_signals=q_data.get("expected_answer_signals", []),
                follow_up_if_vague=q_data.get("follow_up_if_vague", ""),
            )
            created_questions.append(question)

        logger.info(
            "[VoiceQuestionBuilder] Created %d questions for interview %s",
            len(created_questions),
            interview.id,
        )
        return created_questions

    # ── Resume synthesis ────────────────────────────────────────────────────

    @staticmethod
    def _synthesize_resume_text(candidate: Candidate) -> str:
        """
        Reconstruct a complete plain-text resume from the Candidate model's
        structured JSONFields. The Candidate model has NO `resume_text` column —
        raw PDF text is never persisted. We compose all stored fields into a
        rich block so Claude has equivalent (actually better-structured) context.
        """
        parts: list[str] = []

        # ── Summary ──────────────────────────────────────────────────────────
        if candidate.summary:
            parts.append(f"Summary:\n{candidate.summary.strip()}")

        # ── Skills ───────────────────────────────────────────────────────────
        skills_raw = candidate.skills or []
        if skills_raw:
            skill_lines = ["Skills:"]
            for g in skills_raw:
                if isinstance(g, dict):
                    cat   = g.get("category") or ""
                    slist = g.get("skills") or []
                    if slist:
                        skill_lines.append(f"  {cat}: {', '.join(str(s) for s in slist)}")
                else:
                    skill_lines.append(f"  {g}")
            parts.append("\n".join(skill_lines))

        # ── Experience ───────────────────────────────────────────────────────
        experience = candidate.experience or []
        if experience:
            exp_lines = ["Experience:"]
            for exp in experience:
                if isinstance(exp, dict):
                    title    = exp.get("title") or exp.get("role") or ""
                    company  = exp.get("company") or exp.get("organization") or ""
                    duration = exp.get("duration") or exp.get("period") or ""
                    desc     = exp.get("description") or exp.get("summary") or ""
                    if isinstance(desc, list):
                        desc = " ".join(str(d) for d in desc[:3])
                    header = " | ".join(filter(None, [title, company, duration]))
                    if header:
                        exp_lines.append(f"  • {header}")
                    if desc:
                        exp_lines.append(f"    {str(desc).strip()[:400]}")
                else:
                    exp_lines.append(f"  • {str(exp)}")
            parts.append("\n".join(exp_lines))

        # ── Projects ─────────────────────────────────────────────────────────
        projects = candidate.projects or []
        if projects:
            proj_lines = ["Projects:"]
            for proj in projects:
                if isinstance(proj, dict):
                    name = proj.get("name") or proj.get("title") or ""
                    tech = proj.get("tech_stack") or proj.get("technologies") or []
                    if isinstance(tech, list):
                        tech = ", ".join(str(t) for t in tech)
                    desc = proj.get("description") or proj.get("summary") or ""
                    if isinstance(desc, list):
                        desc = " ".join(str(d) for d in desc[:2])
                    header = f"{name} ({tech})" if name and tech else name or tech
                    if header:
                        proj_lines.append(f"  • {header}")
                    if desc:
                        proj_lines.append(f"    {str(desc).strip()[:300]}")
                else:
                    proj_lines.append(f"  • {str(proj)}")
            parts.append("\n".join(proj_lines))

        # ── Education ────────────────────────────────────────────────────────
        education = candidate.education or []
        if education:
            edu_lines = ["Education:"]
            for edu in education:
                if isinstance(edu, dict):
                    degree      = edu.get("degree") or ""
                    institution = edu.get("institution") or edu.get("college") or ""
                    year        = edu.get("year") or edu.get("graduation_year") or ""
                    line        = " | ".join(filter(None, [degree, institution, str(year)]))
                    if line:
                        edu_lines.append(f"  • {line}")
                else:
                    edu_lines.append(f"  • {str(edu)}")
            parts.append("\n".join(edu_lines))

        # ── Certifications ───────────────────────────────────────────────────
        certs = candidate.certifications or []
        if certs:
            cert_lines = ["Certifications:"]
            for c in certs:
                cert_lines.append(
                    f"  • {c if isinstance(c, str) else str(c.get('name', c))}"
                )
            parts.append("\n".join(cert_lines))

        # ── Achievements ─────────────────────────────────────────────────────
        achievements = candidate.achievements or []
        if achievements:
            ach_lines = ["Achievements:"]
            for a in achievements:
                ach_lines.append(f"  • {a if isinstance(a, str) else str(a)}")
            parts.append("\n".join(ach_lines))

        # ── Positions of Responsibility ──────────────────────────────────────
        positions = candidate.position_of_responsibility or []
        if positions:
            pos_lines = ["Positions of Responsibility:"]
            for p in positions:
                pos_lines.append(f"  • {p if isinstance(p, str) else str(p)}")
            parts.append("\n".join(pos_lines))

        return "\n\n".join(parts) if parts else "No resume content available."

    # ── Skills formatting helper ────────────────────────────────────────────

    @staticmethod
    def _format_skills_flat(skills_raw: list) -> str:
        """
        Compact semicolon-separated skills string for the prompt header.
        Handles both [{category, skills[]}] dicts and flat string lists.
        """
        if not skills_raw:
            return "Not specified"
        if isinstance(skills_raw[0], dict):
            parts = []
            for g in skills_raw:
                if isinstance(g, dict):
                    cat   = g.get("category") or ""
                    slist = g.get("skills") or []
                    if slist:
                        parts.append(f"{cat}: {', '.join(str(s) for s in slist)}")
            return "; ".join(parts) if parts else "Not specified"
        return ", ".join(str(s) for s in skills_raw)

    # ── Prompt assembly ─────────────────────────────────────────────────────

    def _build_user_message(
        self,
        candidate: Candidate,
        evaluation: CandidateEvaluation,
        job_description,   # JobDescription | None
        team_profile,      # TeamProfile    | None
    ) -> str:
        # ── Candidate section ────────────────────────────────────────────────
        skills_str    = self._format_skills_flat(candidate.skills or [])
        resume_text   = self._synthesize_resume_text(candidate)
        resume_summary = (
            f"Name:   {candidate.name or 'Unknown'}\n"
            f"Email:  {candidate.email or 'Unknown'}\n"
            f"GitHub: {candidate.raw_github_username or candidate.github_url or 'N/A'}\n"
            f"Skills: {skills_str}\n\n"
            f"Full Resume:\n{resume_text}"
        )

        # ── Evaluation context ───────────────────────────────────────────────
        gap_analysis = evaluation.gap_analysis or "No gap analysis available."
        reasoning    = evaluation.reasoning    or "No reasoning available."

        # ── Job description — ALWAYS guarded against None ────────────────────
        #
        # job_description is None when the candidate is submitted against
        # the "General" role (no JD selected in the UI). This is expected.
        # We fall back to values derived from the gap_analysis (already
        # computed by the LangGraph pipeline) so questions remain role-relevant.
        #
        if job_description is not None:
            job_title        = job_description.title
            department       = job_description.department
            required_skills  = ", ".join(job_description.required_skills or [])
            preferred_skills = ", ".join(job_description.preferred_skills or [])
            required_years   = str(job_description.required_experience_years)
            responsibilities = "\n".join(
                f"- {r}" for r in (job_description.responsibilities or [])
            ) or "- Build and maintain AI-powered systems"
        else:
            # Derive best-effort role context from what the pipeline already computed.
            gap_dict        = evaluation.gap_analysis or {}
            best_role       = (
                gap_dict.get("best_match_role")
                if isinstance(gap_dict, dict) else None
            ) or "General AI Engineer"
            flat_skills     = candidate.flat_skills()
            job_title       = best_role
            department      = "Engineering"
            required_skills = ", ".join(flat_skills[:20]) if flat_skills else "Not specified"
            preferred_skills = ""
            required_years  = "1"
            responsibilities = (
                "- Contribute to AI/ML systems\n"
                "- Write clean, maintainable code\n"
                "- Collaborate with the engineering team"
            )

        # ── Team profile — ALWAYS guarded against None ───────────────────────
        #
        # team_profile is None when job_description is None, or when the
        # linked JobDescription has no TeamProfile FK set.
        #
        if team_profile is not None:
            team_role      = team_profile.role
            seniority      = team_profile.seniority_level
            current_skills = ", ".join(team_profile.current_skills or [])
            missing_skills = ", ".join(team_profile.missing_skills or [])
            culture_values = ", ".join(team_profile.culture_values or [])
        else:
            team_role      = job_title
            seniority      = "Junior"
            current_skills = required_skills
            missing_skills = ""
            culture_values = "ownership, curiosity, clear communication, bias-for-action"

        return USER_TEMPLATE.format(
            resume_summary=resume_summary,
            gap_analysis=gap_analysis,
            reasoning=reasoning,
            job_title=job_title,
            department=department,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            required_experience_years=required_years,
            responsibilities=responsibilities,
            team_role=team_role,
            seniority_level=seniority,
            current_skills=current_skills,
            missing_skills=missing_skills,
            culture_values=culture_values,
        )

    # ── Claude call ─────────────────────────────────────────────────────────

    def _call_claude_structured(self, user_message: str) -> list[dict]:
        """
        Calls Claude with structured output (json_schema beta).
        Returns a list of question dicts, or [] on ANY failure.

        Errors are always caught and logged here — never re-raised.
        This guarantees that build() can return [] cleanly and tasks.py
        can decide how to handle it without an unexpected exception propagating
        up through Celery and into the Django request cycle.
        """
        model = getattr(settings, "VOICE_STRUCTURED_OUTPUT_MODEL", "claude-sonnet-4-5")

        try:
            message = _anthropic.beta.messages.create(
                model=model,
                max_tokens=2048,
                betas=[STRUCTURED_OUTPUTS_BETA],
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
                output_format={
                    "type": "json_schema",
                    "schema": VOICE_QUESTIONS_RESPONSE_SCHEMA,
                },
            )
        except TypeError as exc:
            # Anthropic SDK too old to support the structured-outputs beta parameter.
            logger.error(
                "[VoiceQuestionBuilder] Anthropic client does not support structured "
                "outputs — upgrade the SDK: %s",
                exc,
            )
            return []
        except Exception as exc:
            logger.error(
                "[VoiceQuestionBuilder] Claude API call failed: %s", exc
            )
            return []

        try:
            data      = json.loads(message.content[0].text)
            questions = data.get("questions")
            if not isinstance(questions, list):
                logger.error(
                    "[VoiceQuestionBuilder] Structured output missing 'questions' list. "
                    "Raw response snippet: %s",
                    message.content[0].text[:500],
                )
                return []
            return questions
        except (IndexError, AttributeError, json.JSONDecodeError) as exc:
            logger.error(
                "[VoiceQuestionBuilder] Could not parse Claude response: %s", exc
            )
            return []
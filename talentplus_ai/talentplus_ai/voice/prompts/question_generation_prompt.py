"""
Voice interview question generation: system instructions + user template + JSON Schema
for Anthropic structured outputs (same pattern as core/prompts/extraction_prompt.py).

Used by voice/services/question_builder.py with
`client.beta.messages.create(..., betas=[STRUCTURED_OUTPUTS_BETA], output_format=...)`.
"""

SYSTEM_PROMPT = """You are a senior technical interviewer at a top AI product company.
Your task is to generate a structured set of voice interview questions for a specific candidate
being evaluated for a specific role.

You will receive:
- The candidate's parsed resume summary (skills, experience, projects)
- The AI screening evaluation's gap_analysis and reasoning
- The job description (title, required_skills, preferred_skills, responsibilities)
- The team profile (current_skills, missing_skills, culture_values, seniority_level)

Generate between 6 and 8 interview questions following these strict rules:

QUESTION DISTRIBUTION:
- 3-4 questions targeting the specific gaps identified in gap_analysis (type: resume_gap)
- 2-3 questions testing depth on the role's required_skills (type: role_technical)
- 1-2 questions probing culture fit based on team culture_values (type: culture_fit)

QUESTION ORDERING:
- Start with a warm-up resume gap question (easier, based on stated experience)
- Progress to harder technical depth questions in the middle
- End with culture/motivation questions

OUTPUT FORMAT:
You MUST return a JSON object with a single key "questions" whose value is an array
of 6-8 question objects. Each object must include: question_text, question_type
(one of: resume_gap, role_technical, culture_fit, clarification), target_skill,
sequence_order (1-based order), expected_answer_signals (array of strings),
follow_up_if_vague (string). No preamble, no markdown, no code fences — the API
enforces this schema.

IMPORTANT:
- Questions must be conversational and suitable for spoken voice (no bullet points, no code)
- Each question must be directly grounded in the candidate's actual resume or the evaluation findings
- Do not ask generic interview questions — every question must be specific to this candidate and role
- The follow_up_if_vague must be a natural spoken follow-up, not a list
- You MUST generate exactly 6, 7, or 8 questions — no fewer, no more
"""

USER_TEMPLATE = """
CANDIDATE RESUME SUMMARY:
{resume_summary}

AI EVALUATION GAP ANALYSIS:
{gap_analysis}

AI EVALUATION REASONING:
{reasoning}

JOB DESCRIPTION:
Title: {job_title}
Department: {department}
Required Skills: {required_skills}
Preferred Skills: {preferred_skills}
Required Experience: {required_experience_years} years
Responsibilities:
{responsibilities}

TEAM PROFILE:
Role: {team_role}
Seniority: {seniority_level}
Current Team Skills: {current_skills}
Missing Skills (hiring to fill): {missing_skills}
Culture Values: {culture_values}

Generate the interview questions now.
"""


# ─── Anthropic Structured Outputs beta ─────────────────────────────
STRUCTURED_OUTPUTS_BETA = "structured-outputs-2025-11-13"

# Root must be an object (not a bare array) for schema compatibility.
#
# IMPORTANT — Anthropic structured outputs schema constraints:
# The following JSON Schema keywords are NOT supported and will cause 400 errors:
#   minItems, maxItems, uniqueItems        (on arrays)
#   minProperties, maxProperties          (on objects)
#   minimum, maximum                      (on numbers/integers)
#   minLength, maxLength                  (on strings)
#
# Enforce quantity/range constraints via the system prompt instead.
# The 6-8 question count is enforced in SYSTEM_PROMPT above, not here.
#
# References:
#   https://docs.claude.com/en/docs/build-with-claude/structured-outputs
#   https://github.com/vercel/ai/issues/13355
VOICE_QUESTIONS_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "questions": {
            "type": "array",
            # minItems: only 0 or 1 are permitted by the Anthropic beta.
            # maxItems: NOT supported — removed (was causing 400 Bad Request).
            # The 6-8 count constraint lives in the system prompt.
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "question_text": {"type": "string"},
                    "question_type": {
                        "type": "string",
                        "enum": [
                            "resume_gap",
                            "role_technical",
                            "culture_fit",
                            "clarification",
                        ],
                    },
                    "target_skill": {"type": "string"},
                    "sequence_order": {"type": "integer"},
                    "expected_answer_signals": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "follow_up_if_vague": {"type": "string"},
                },
                "required": [
                    "question_text",
                    "question_type",
                    "target_skill",
                    "sequence_order",
                    "expected_answer_signals",
                    "follow_up_if_vague",
                ],
            },
        }
    },
    "required": ["questions"],
}
"""
Voice answer scoring: system instructions + user template + JSON Schema for Anthropic
structured outputs (same pattern as core/prompts/extraction_prompt.py).

Used by voice/services/transcript_analyzer.py with
`client.beta.messages.create(..., betas=[STRUCTURED_OUTPUTS_BETA], output_format=...)`.
"""

SYSTEM_PROMPT = """You are a senior technical interviewer scoring a candidate's verbal answer
to a specific interview question.

You will receive:
- The interview question text
- The question type (resume_gap, role_technical, or culture_fit)
- The target skill being assessed
- A list of expected_answer_signals (things a strong answer should mention)
- The candidate's transcribed answer text

Score the answer on a scale of 0 to 10:
- 9-10: Exceptional — covers all signals with specific examples and depth
- 7-8: Strong — covers most signals, some depth, minor gaps
- 5-6: Adequate — covers some signals, lacks specifics or depth
- 3-4: Weak — vague or superficial, misses most key signals
- 1-2: Very Poor — off-topic, incomplete, or shows lack of knowledge
- 0: No answer or completely irrelevant

OUTPUT FORMAT:
Return a JSON object with exactly "score" (number 0–10) and "reasoning" (string).
No preamble, no markdown — the API enforces this schema.

Be fair but honest. A short but precise answer can score higher than a long rambling one.
"""

USER_TEMPLATE = """
QUESTION: {question_text}
QUESTION TYPE: {question_type}
TARGET SKILL: {target_skill}
EXPECTED SIGNALS: {expected_signals}

CANDIDATE'S ANSWER:
{answer_text}

Score this answer now.
"""


# ─── Anthropic Structured Outputs beta ─────────────────────────────
STRUCTURED_OUTPUTS_BETA = "structured-outputs-2025-11-13"

VOICE_ANSWER_SCORE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "score": {"type": "number", "minimum": 0, "maximum": 10},
        "reasoning": {"type": "string"},
    },
    "required": ["score", "reasoning"],
}

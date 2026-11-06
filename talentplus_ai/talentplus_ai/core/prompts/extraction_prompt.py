"""
Resume extraction: system instructions + JSON Schema for Anthropic structured outputs.

File:   core/prompts/extraction_prompt.py
Folder: core/prompts/

Key change: skills is now extracted as a list of {category, skills[]} objects
instead of a flat string list. This preserves the actual section headings from
the resume (e.g. "Programming & Frameworks", "AI, ML & Generative AI") so the
frontend can display them as-is rather than re-bucketing with regex.
"""

# ─── System Prompt ───────────────────────────────────────────────
EXTRACTION_SYSTEM_PROMPT = """
You are a precise resume data extraction engine.
You receive markdown (from a layout-aware PDF converter) representing a candidate resume.
A section titled "HYPERLINKS EXTRACTED FROM PDF" may appear at the end — use those URLs
to populate github_url, linkedin_url, and portfolio_url fields.

RULES:
- Extract ALL experience entries, including internships and short-term roles.
- tech_stack: individual technology/framework names only, not sentences.
- impact_metrics: only bullets that include numbers, percentages, or measurable outcomes.
- Do not invent facts; only extract what appears in the document.
- Preserve the candidate's wording for responsibilities and highlights where sensible.
- For fields not present in the resume, output null (for strings) or [] (for arrays).

SKILLS EXTRACTION RULES — read carefully:
- The resume may list skills under named category headings such as
  "Programming & Frameworks", "AI, ML & Generative AI", "Data, MLOps & Cloud", etc.
- Extract each category with its heading exactly as written in the resume.
- Under each category, list the individual skill/tool names as separate strings.
- If the resume has NO category headings and just lists skills in a flat block,
  create a single category called "Skills" and put all skills under it.
- Do NOT invent category names. Use only what appears in the resume.
- skills: individual technology/tool names only, not full sentences or descriptions.

DURATION RULES — read carefully:
- duration_months: calculate the number of months between the start and end dates.
- Today is March 2026. For "Present" or ongoing roles, use March 2026 as the end date.
  Example: "Aug 2025 - Present" = Aug 2025 to Mar 2026 = 7 months. NOT 0.
- Do NOT use 0 for any active role. Always compute from start month to March 2026.

EXPERIENCE DEDUPLICATION — critical:
- A resume section may show an education date range on the same line as a company name
  due to PDF layout. Do NOT interpret education dates as a separate job tenure.
- Each distinct (company, role, start_date) combination = one experience entry.
- If a candidate has ONE role at a company with ONE start date, create ONE entry.
- Example: "AIonOS | Engineer. Oct 2021 - July 2025 | Aug 2025 - Present"
  means: the Oct 2021 date belongs to the EDUCATION section above it, not AIonOS.
  AIonOS has ONE entry: role=Engineer, duration="Aug 2025 - Present", duration_months=7.

GITHUB URL RULES:
- If the resume shows "Github" or "GitHub" as a hyperlink text, check the HYPERLINKS
  section at the bottom for the actual URL. Assign it to github_url.
- github_username: extract only the handle (e.g. "gauravtripathi0026" from
  "https://github.com/gauravtripathi0026"). Do NOT set it to "Github" or "GitHub".
- If no GitHub URL is found anywhere, output null for both github_url and github_username.

LINKEDIN URL RULES:
- If the resume shows "LinkedIn" as styled text, check the HYPERLINKS section for the URL.
- linkedin_url should be a full URL (https://linkedin.com/in/...), not the word "LinkedIn".
- If no URL found, output null.

PROJECT URL RULES:
- project.url: if a project links to "Github", check the HYPERLINKS section for the
  actual repository URL. If multiple GitHub links exist, use context (project name) to
  match. If no specific project URL can be determined, output null.
""".strip()


# ─── Sub-schemas ─────────────────────────────────────────────────

_RESUME_EXPERIENCE_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "company":          {"type": "string"},
        "role":             {"type": "string"},
        "duration":         {"type": "string"},
        "duration_months":  {"type": "integer"},
        "location":         {"type": ["string", "null"]},
        "tech_stack":       {"type": "array", "items": {"type": "string"}},
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "impact_metrics":   {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "company", "role", "duration", "duration_months",
        "location", "tech_stack", "responsibilities", "impact_metrics",
    ],
}

_RESUME_PROJECT_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name":        {"type": "string"},
        "tech_stack":  {"type": "array", "items": {"type": "string"}},
        "description": {"type": "string"},
        "url":         {"type": ["string", "null"]},
        "highlights":  {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "tech_stack", "description", "url", "highlights"],
}

_RESUME_EDUCATION_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "institution": {"type": "string"},
        "degree":      {"type": "string"},
        "field":       {"type": "string"},
        "duration":    {"type": "string"},
        "grade":       {"type": ["string", "null"]},
    },
    "required": ["institution", "degree", "field", "duration", "grade"],
}

# Skills are now extracted as categorized groups, preserving the resume's
# own section headings (e.g. "Programming & Frameworks", "AI, ML & Generative AI").
_SKILL_CATEGORY_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "category": {"type": "string"},               # exact heading from resume
        "skills":   {"type": "array", "items": {"type": "string"}},  # individual skill names
    },
    "required": ["category", "skills"],
}


# ─── Root Schema ─────────────────────────────────────────────────
RESUME_EXTRACTION_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name":             {"type": "string"},
        "email":            {"type": ["string", "null"]},
        "phone":            {"type": ["string", "null"]},
        "github_url":       {"type": ["string", "null"]},
        "github_username":  {"type": ["string", "null"]},
        "linkedin_url":     {"type": ["string", "null"]},
        "portfolio_url":    {"type": ["string", "null"]},
        "summary":          {"type": ["string", "null"]},
        # skills: categorized list — preserves resume section headings
        "skills":           {"type": "array", "items": _SKILL_CATEGORY_ITEM},
        "experience":       {"type": "array", "items": _RESUME_EXPERIENCE_ITEM},
        "projects":         {"type": "array", "items": _RESUME_PROJECT_ITEM},
        "education":        {"type": "array", "items": _RESUME_EDUCATION_ITEM},
        "certifications":   {"type": "array", "items": {"type": "string"}},
        "achievements":     {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "name", "email", "phone", "github_url", "github_username",
        "linkedin_url", "portfolio_url", "summary",
        "skills", "experience", "projects", "education",
        "certifications", "achievements",
    ],
}
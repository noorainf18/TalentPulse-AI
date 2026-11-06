import json
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from talentplus_ai.candidates.models import Candidate


def _json_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=True, indent=2)
    except Exception:
        return str(value)


def build_candidate_document(candidate: Candidate) -> str:
    """
    Builds a single text document from all structured candidate fields.
    This is what gets chunked and stored in the vector store.

    Skills are stored as [{category, skills[]}] — we flatten them here
    so the vector store sees plain skill text.
    """
    # Flatten categorized skills into readable text
    skills_text_parts = []
    for group in (candidate.skills or []):
        if isinstance(group, dict):
            category = group.get("category", "")
            skill_list = ", ".join(group.get("skills") or [])
            if category and skill_list:
                skills_text_parts.append(f"{category}: {skill_list}")
    skills_text = "\n".join(skills_text_parts)

    parts = [
        f"Name: {candidate.name}",
        f"Email: {candidate.email}",
        f"Phone: {candidate.phone_number or ''}",
        f"LinkedIn: {candidate.linkedin_url or ''}",
        f"GitHub: {candidate.github_url or ''}",
        f"Portfolio: {candidate.portfolio_url or ''}",
        "",
        f"Summary:\n{candidate.summary}" if candidate.summary else "",
        "",
        f"Skills:\n{skills_text}" if skills_text else "",
        "",
        "Experience:\n" + _json_to_text(candidate.experience),
        "",
        "Projects:\n" + _json_to_text(candidate.projects),
        "",
        "Education:\n" + _json_to_text(candidate.education),
        "",
        "Certifications:\n" + _json_to_text(candidate.certifications),
        "",
        "Achievements:\n" + _json_to_text(candidate.achievements),
        "",
        "Position of Responsibility:\n" + _json_to_text(candidate.position_of_responsibility),
    ]
    return "\n".join(p for p in parts if p.strip()).strip()


def chunk_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        separators=[
            "\n## ", "\n# ", "\nExperience", "\nEducation", "\nSkills",
            "\nProjects", "\nCertifications", "\nAchievements", "\n\n", "\n", ". ", " ",
        ],
        chunk_size=600,
        chunk_overlap=80,
        length_function=len,
    )
    docs = splitter.create_documents([text])
    return [d.page_content.strip() for d in docs if d.page_content.strip()]
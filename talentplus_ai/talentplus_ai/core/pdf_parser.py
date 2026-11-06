"""
PDF Parser — Docling + Anthropic Structured Outputs
=====================================================
File:   core/pdf_parser.py

Two-stage pipeline:
  Stage 1 — Docling: PDF bytes → plain text + structured markdown.
  Stage 2 — Claude Sonnet 4.5 via Anthropic Structured Outputs beta:
             guaranteed schema-compliant JSON.

Skills change: Claude now returns skills as [{category, skills[]}] objects,
preserving the resume's own section headings instead of a flat list.
"""

import logging
from io import BytesIO
from typing import Any, BinaryIO, Dict

from django.conf import settings
from anthropic import Anthropic

from talentplus_ai.core.exceptions import PDFParseError
from talentplus_ai.core.prompts.extraction_prompt import (
    EXTRACTION_SYSTEM_PROMPT,
    RESUME_EXTRACTION_JSON_SCHEMA,
)

logger = logging.getLogger(__name__)

_EXTRACTION_MODEL = "claude-sonnet-4-5"


# ─────────────────────────────────────────────────────────────────
# HYPERLINK EXTRACTOR
# ─────────────────────────────────────────────────────────────────

def _extract_hyperlinks(file_bytes: bytes) -> list[str]:
    """Extracts clickable hyperlink URLs from the PDF annotation layer via pdfplumber."""
    urls = []
    try:
        import pdfplumber
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                annots = page.hyperlinks if hasattr(page, "hyperlinks") else []
                for annot in annots:
                    uri = annot.get("uri") or annot.get("url") or ""
                    if uri and uri not in urls:
                        urls.append(uri)
    except Exception as exc:
        logger.debug("Hyperlink extraction skipped: %s", exc)
    return urls


# ─────────────────────────────────────────────────────────────────
# STAGE 1: Docling — PDF → (plain text, markdown)
# ─────────────────────────────────────────────────────────────────

def _docling_extract(file_bytes: bytes) -> tuple[str, str, list[str]]:
    """Converts PDF bytes to (raw_text, structured_markdown, hyperlinks) using Docling."""
    try:
        from docling.datamodel.base_models import DocumentStream
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
    except ImportError as exc:
        raise PDFParseError("Docling is required. Install with: pip install docling") from exc

    try:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        source = DocumentStream(name="resume.pdf", stream=BytesIO(file_bytes))
        result = converter.convert(source)
        doc = result.document

        structured_md = doc.export_to_markdown()
        raw_text = doc.export_to_text()

        if not raw_text.strip():
            raise PDFParseError(
                "Docling returned empty text. The PDF may be image-only or scanned."
            )

        hyperlinks = _extract_hyperlinks(file_bytes)
        logger.info(
            "[Docling] Parsed PDF: %d chars plain text, %d chars markdown, %d hyperlinks.",
            len(raw_text), len(structured_md), len(hyperlinks),
        )
        return raw_text.strip(), structured_md.strip(), hyperlinks

    except PDFParseError:
        raise
    except Exception as exc:
        raise PDFParseError(f"Docling failed to parse the PDF: {exc}") from exc


# ─────────────────────────────────────────────────────────────────
# STAGE 2: Claude Structured Outputs — Markdown → Structured JSON
# ─────────────────────────────────────────────────────────────────

def _claude_extract(structured_md: str, raw_text: str, hyperlinks: list[str] | None = None) -> dict[str, Any]:
    """Sends Docling's markdown to Claude Sonnet 4.5 via Anthropic Structured Outputs beta."""
    api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
    if not api_key:
        raise PDFParseError("ANTHROPIC_API_KEY is not set in Django settings.")

    content = structured_md if len(structured_md) > 300 else raw_text
    content = content[:12000]

    if hyperlinks:
        link_block = (
            "\n\n## HYPERLINKS EXTRACTED FROM PDF (assign to correct fields)\n"
            + "\n".join(f"- {url}" for url in hyperlinks)
        )
        content += link_block

    client = Anthropic(api_key=api_key)

    try:
        message = client.beta.messages.create(
            model=_EXTRACTION_MODEL,
            max_tokens=4096,
            betas=["structured-outputs-2025-11-13"],
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "Extract all structured data from this resume:\n\n" + content,
                }
            ],
            output_format={
                "type": "json_schema",
                "schema": RESUME_EXTRACTION_JSON_SCHEMA,
            },
        )
    except TypeError as exc:
        raise PDFParseError(
            "Your anthropic package is too old for structured outputs. "
            "Upgrade with: pip install 'anthropic>=0.49.0'"
        ) from exc
    except Exception as exc:
        raise PDFParseError(f"Anthropic structured output call failed: {exc}") from exc

    import json
    try:
        extracted: dict = json.loads(message.content[0].text)
    except (IndexError, AttributeError, json.JSONDecodeError) as exc:
        raise PDFParseError(f"Could not parse structured output from Claude: {exc}") from exc

    skill_groups = extracted.get("skills") or []
    total_skills = sum(len(g.get("skills", [])) for g in skill_groups if isinstance(g, dict))
    logger.info(
        "[Claude Extraction] name=%s | email=%s | skill_categories=%d | total_skills=%d | "
        "experience=%d | projects=%d",
        extracted.get("name"),
        extracted.get("email"),
        len(skill_groups),
        total_skills,
        len(extracted.get("experience") or []),
        len(extracted.get("projects") or []),
    )
    return extracted


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def _pdfplumber_extract(file_bytes: bytes) -> tuple[str, str, list[str]]:
    """Text fallback when Docling's layout model cannot load."""
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    raw_text = "\n\n".join(pages).strip()
    if not raw_text:
        raise PDFParseError(
            "Could not read text from this PDF. It may be a scanned image."
        )
    return raw_text, raw_text, _extract_hyperlinks(file_bytes)


def extract_text_from_pdf(file: BinaryIO) -> Dict[str, Any]:
    """
    Full pipeline: PDF file → structured dict ready for the Candidate model.

    skills field shape: [{"category": "Programming & Frameworks", "skills": ["Python", ...]}, ...]
    """
    file_bytes = file.read()

    try:
        raw_text, structured_md, hyperlinks = _docling_extract(file_bytes)
    except PDFParseError as exc:
        logger.warning("Docling parse failed, using pdfplumber: %s", exc)
        raw_text, structured_md, hyperlinks = _pdfplumber_extract(file_bytes)
    extracted = _claude_extract(structured_md, raw_text, hyperlinks)

    github_username = extracted.get("github_username") or ""
    if github_username and "/" in github_username:
        github_username = github_username.split("/")[0]

    result: Dict[str, Any] = {
        "raw_text":       raw_text,
        "name":           extracted.get("name") or "Unknown",
        "email":          (extracted.get("email") or "").strip().lower(),
        "github_url":     extracted.get("github_url") or None,
        "github_username": github_username,
        "portfolio_url":  extracted.get("portfolio_url") or None,
        "linkedin_url":   extracted.get("linkedin_url") or None,
        "phone":          extracted.get("phone") or None,
        "summary":        extracted.get("summary") or "",
        # Categorized skills: [{category, skills[]}] — preserves resume headings
        "skills":         extracted.get("skills") or [],
        "experience":     extracted.get("experience") or [],
        "projects":       extracted.get("projects") or [],
        "education":      extracted.get("education") or [],
        "certifications": extracted.get("certifications") or [],
        "achievements":   extracted.get("achievements") or [],
    }

    skill_groups = result["skills"]
    total_skills = sum(len(g.get("skills", [])) for g in skill_groups if isinstance(g, dict))
    logger.info(
        "[pdf_parser] Complete | name=%s | email=%s | skill_categories=%d | "
        "total_skills=%d | experience=%d | projects=%d",
        result["name"], result["email"],
        len(skill_groups), total_skills,
        len(result["experience"]), len(result["projects"]),
    )
    return result
"""
Django Management Command — extract_resume_pdf
===============================================
File:   candidates/management/commands/extract_resume_pdf.py

Auto-scans the `data/` directory for PDF resume files, runs each through
the Docling + Claude Structured Outputs pipeline, and writes one JSON
output file per resume into the `outputs/` directory.

Usage:
  # Parse all PDFs in data/
  python manage.py extract_resume_pdf

  # Parse a single specific PDF
  python manage.py extract_resume_pdf --file data/Gaurav_Tripathi.pdf

  # Parse for a specific role
  python manage.py extract_resume_pdf --role "AI Engineer"

  # Dry run — output JSON only, skip DB
  python manage.py extract_resume_pdf --no-db
"""

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from talentplus_ai.core.exceptions import PDFParseError
from talentplus_ai.core.pdf_parser import extract_text_from_pdf

BASE_DIR = Path(settings.BASE_DIR)
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"


def _compute_resume_hash(raw_text: str) -> str:
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


class Command(BaseCommand):
    help = (
        "Parse PDF resumes from data/ using Docling + Claude. "
        "Writes structured JSON to outputs/. "
        "Optionally saves each candidate to the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", "-f",
            type=str,
            default="",
            help="Parse a single PDF instead of scanning data/. Example: --file data/resume.pdf",
        )
        parser.add_argument(
            "--role", "-r",
            type=str,
            default="",
            help="Target role for this submission, e.g. --role 'AI Engineer'",
        )
        parser.add_argument(
            "--no-db",
            action="store_true",
            default=False,
            help="Skip saving to the database. Only write JSON output files.",
        )

    def handle(self, *args, **options):
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        single_file = options.get("file", "").strip()
        target_role = options.get("role", "").strip()

        if single_file:
            pdf_paths = self._resolve_single(single_file)
        else:
            pdf_paths = self._scan_data_dir()

        if not pdf_paths:
            self.stdout.write(self.style.WARNING("No PDF files found. Nothing to process."))
            return

        save_to_db = not options["no_db"]
        success_count = 0
        error_count = 0

        for pdf_path in pdf_paths:
            self.stdout.write(f"\n→ Processing: {pdf_path.name}")
            try:
                result = self._parse(pdf_path)
                self._write_output(pdf_path, result)
                if save_to_db:
                    self._save_to_db(pdf_path, result, target_role)
                success_count += 1
            except (PDFParseError, CommandError) as exc:
                self.stderr.write(self.style.ERROR(f"  ✗ Failed: {exc}"))
                error_count += 1

        self.stdout.write("\n" + "─" * 50)
        self.stdout.write(
            self.style.SUCCESS(f"✓ {success_count} parsed successfully") +
            (f"   ✗ {error_count} failed" if error_count else "")
        )
        self.stdout.write(f"  Output directory: {OUTPUTS_DIR}")

    # ── Private helpers ──────────────────────────────────────────

    def _resolve_single(self, file_str: str) -> list[Path]:
        path = Path(file_str).expanduser().resolve()
        if not path.is_file():
            raise CommandError(f"File not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise CommandError(f"Not a PDF file: {path}")
        return [path]

    def _scan_data_dir(self) -> list[Path]:
        if not DATA_DIR.is_dir():
            raise CommandError(
                f"data/ directory not found at {DATA_DIR}. "
                "Create it and place your PDF resume files inside."
            )
        pdfs = sorted(DATA_DIR.glob("*.pdf"))
        self.stdout.write(f"Found {len(pdfs)} PDF(s) in {DATA_DIR}")
        return pdfs

    def _parse(self, pdf_path: Path) -> dict:
        with pdf_path.open("rb") as f:
            return extract_text_from_pdf(f)

    def _write_output(self, pdf_path: Path, result: dict) -> None:
        out_path = OUTPUTS_DIR / f"{pdf_path.stem}.json"
        out_path.write_text(
            json.dumps(result, indent=2, default=str),
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(f"  ✓ Saved: outputs/{out_path.name}"))

    def _save_to_db(self, pdf_path: Path, parsed: dict, target_role: str) -> None:
        """
        Creates or updates the Candidate record, then creates a new
        CandidateEvaluation for the given role — unless the same resume
        hash already exists for that role (cache hit).
        """
        from talentplus_ai.candidates.models import Candidate, CandidateEvaluation
        from talentplus_ai.core.resume_vectorizer import vectorize_and_store
        from talentplus_ai.agent.tasks import trigger_screening

        email = (parsed.get("email") or "").strip().lower()
        if not email:
            self.stderr.write(self.style.WARNING(
                f"  ⚠ No email extracted from {pdf_path.name}. Skipping DB save."
            ))
            return

        raw_text = parsed.get("raw_text", "")
        resume_hash = _compute_resume_hash(raw_text)

        # Get or create the Candidate (keyed on email)
        candidate_fields = {
            "name": parsed.get("name") or "Unknown",
            "phone_number": parsed.get("phone") or None,
            "github_url": parsed.get("github_url") or None,
            "portfolio_url": parsed.get("portfolio_url") or None,
            "linkedin_url": parsed.get("linkedin_url") or None,
            "raw_github_username": parsed.get("github_username", ""),
            "summary": parsed.get("summary", ""),
            "skills": parsed.get("skills") or [],
            "experience": parsed.get("experience") or [],
            "projects": parsed.get("projects") or [],
            "education": parsed.get("education") or [],
            "certifications": parsed.get("certifications") or [],
            "achievements": parsed.get("achievements") or [],
            "position_of_responsibility": parsed.get("position_of_responsibility") or [],
        }

        candidate, created = Candidate.objects.get_or_create(
            email=email,
            defaults=candidate_fields,
        )

        if not created:
            # Refresh candidate profile with latest parsed data
            for field, value in candidate_fields.items():
                setattr(candidate, field, value)
            candidate.save()
            self.stdout.write(f"  → Updated existing candidate: {candidate.name} ({candidate.id})")
        else:
            self.stdout.write(self.style.SUCCESS(f"  ✓ New candidate created: {candidate.name} ({candidate.id})"))

        # Check cache: same role + same resume hash?
        existing_eval = CandidateEvaluation.objects.filter(
            candidate=candidate,
            target_role=target_role,
        ).first()

        if existing_eval and existing_eval.resume_hash == resume_hash:
            self.stdout.write(
                f"  → Cache hit: same resume already evaluated for role '{target_role or 'General'}'. Skipping."
            )
            return

        # Create a new evaluation for this role
        evaluation = CandidateEvaluation.objects.create(
            candidate=candidate,
            target_role=target_role,
            resume_hash=resume_hash,
            status="pending",
            reasoning="Evaluation in progress...",
            trace_log=[{
                "step": "Submitted",
                "message": f"Resume ingested via extract_resume_pdf command ({pdf_path.name}) for role '{target_role or 'General'}'.",
                "status": "done",
            }],
        )

        # Vectorize for semantic search
        try:
            vectorize_and_store(candidate.id, raw_text)
        except Exception as exc:
            self.stderr.write(self.style.WARNING(f"  ⚠ Vectorization skipped: {exc}"))

        # Queue the LangGraph screening agent
        trigger_screening.delay(str(candidate.id), str(evaluation.id))

        self.stdout.write(self.style.SUCCESS(
            f"  ✓ Evaluation created ({evaluation.id}) for role '{target_role or 'General'}' — screening queued"
        ))
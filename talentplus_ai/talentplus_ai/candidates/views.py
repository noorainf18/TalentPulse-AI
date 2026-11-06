import hashlib
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema

from .models import Candidate, CandidateEvaluation
from .serializers import CandidateSerializer, CandidateUploadSerializer
from talentplus_ai.core.exceptions import PDFParseError
from talentplus_ai.core.pdf_parser import extract_text_from_pdf
from talentplus_ai.core.resume_vectorizer import vectorize_and_store

logger = logging.getLogger(__name__)


def _compute_resume_hash(raw_text: str) -> str:
    """SHA-256 fingerprint of the resume text. Used for cache checks."""
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


class ResumeUploadView(APIView):
    """
    POST /api/candidates/upload/

    Accepts a PDF resume + optional target_role, extracts structured data,
    creates or reuses a Candidate record, then creates a new CandidateEvaluation
    for the given role.

    Logic summary:
      - New email → create Candidate + Evaluation, queue screening.
      - Existing email + new role → reuse Candidate, create new Evaluation, queue screening.
      - Existing email + same role + same resume hash → cached, return existing evaluation.
      - Existing email + same role + different resume hash → new Evaluation (updated resume).
    """

    permission_classes = [AllowAny]  # Lock down in production with IsRecruiter
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "resume": {
                        "type": "string",
                        "format": "binary",
                        "description": "PDF file to upload",
                    },
                    "target_role": {
                        "type": "string",
                        "description": "Role the candidate is applying for (e.g. 'AI Engineer')",
                    },
                },
                "required": ["resume"],
            }
        },
        responses={
            202: {"type": "object", "properties": {"message": {"type": "string"}, "candidate_id": {"type": "string"}, "evaluation_id": {"type": "string"}}},
            200: {"type": "object", "properties": {"message": {"type": "string"}, "candidate_id": {"type": "string"}, "evaluation_id": {"type": "string"}}},
            400: {"type": "object"},
            422: {"type": "object"},
        },
        description=(
            "Upload a PDF resume using multipart/form-data with field name `resume`. "
            "Optionally pass `target_role` to scope the evaluation to a specific role."
        ),
    )
    def post(self, request):
        serializer = CandidateUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        pdf_file = serializer.validated_data["resume"]
        target_role = serializer.validated_data.get("target_role", "").strip()

        # 1. Parse PDF → structured dict
        try:
            parsed = extract_text_from_pdf(pdf_file)
        except PDFParseError as e:
            logger.error("PDF parsing failed: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as e:
            logger.exception("PDF parsing failed: %s", e)
            return Response(
                {"error": "Could not parse the PDF. Ensure it is text-readable, not scanned."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # 2. Email is required — it's the candidate identity key
        email = parsed.get("email", "").strip().lower()
        if not email:
            return Response(
                {"error": "Could not extract a valid email address from the resume."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # 3. Compute resume fingerprint for cache check
        raw_text = parsed.get("raw_text", "")
        resume_hash = _compute_resume_hash(raw_text)

        # 4. Get or create the Candidate record (keyed on email)
        candidate, candidate_created = Candidate.objects.get_or_create(
            email=email,
            defaults=self._candidate_fields(parsed),
        )

        if not candidate_created:
            # Update candidate profile with latest parsed data (resume may have been updated)
            for field, value in self._candidate_fields(parsed).items():
                setattr(candidate, field, value)
            candidate.save()

        # 4b. RAG indexing (Strategy A): index this candidate immediately so TalentPlus GPT
        # can answer questions about the newly uploaded/updated resume without a manual
        # /api/ragchat/index/ call.
        #
        # Best-effort: if the embedding service or Chroma is unavailable, we log and continue
        # (screening pipeline should not be blocked).
        try:
            from talentplus_ai.ragchat.services.indexer import index_candidate

            chunks_indexed = index_candidate(candidate)
            logger.info("[upload] RAG indexed candidate %s with %s chunks", candidate.id, chunks_indexed)
        except Exception as exc:
            logger.warning("[upload] RAG indexing skipped/failed for %s: %s", candidate.id, exc)

        # 5. Handle evaluation: check cache (same role + same hash)
        existing_eval = CandidateEvaluation.objects.filter(
            candidate=candidate,
            target_role=target_role,
        ).first()

        if existing_eval and existing_eval.resume_hash == resume_hash:
            # Same resume, same role — return cached result
            logger.info(
                "Cached evaluation returned for %s (%s) — role: %s",
                candidate.name, candidate.id, target_role or "General",
            )
            return Response(
                {
                    "message": "Same resume already evaluated for this role. Returning cached result.",
                    "candidate_id": str(candidate.id),
                    "evaluation_id": str(existing_eval.id),
                },
                status=status.HTTP_200_OK,
            )

        # 6. Create a fresh evaluation record (new role OR updated resume)
        evaluation = CandidateEvaluation.objects.create(
            candidate=candidate,
            target_role=target_role,
            resume_hash=resume_hash,
            status="pending",
            reasoning="Evaluation in progress...",
            trace_log=[{
                "step": "Submitted",
                "message": f"Resume received for role '{target_role or 'General'}'. Queued for screening.",
                "status": "done",
            }],
        )

        # 7. Vectorize resume text for semantic search
        try:
            vectorize_and_store(candidate.id, raw_text)
        except Exception as e:
            logger.warning("Vectorization failed for %s: %s", candidate.id, e)

        # 8. Queue the LangGraph screening agent. The resume is already saved,
        # so a down broker must not turn this request into a 500.
        from kombu.exceptions import OperationalError

        from talentplus_ai.agent.tasks import trigger_screening

        queued = True
        try:
            trigger_screening.apply_async(
                args=[str(candidate.id), str(evaluation.id)],
                ignore_result=True,
                retry=False,
            )
        except OperationalError as exc:
            queued = False
            logger.exception(
                "Could not queue screening for %s: %s", candidate.id, exc
            )
            trace = list(evaluation.trace_log or [])
            trace.append(
                {
                    "step": "Queue",
                    "message": (
                        "Resume saved, but screening was not queued. "
                        "Redis is unreachable from this service."
                    ),
                    "status": "error",
                }
            )
            evaluation.trace_log = trace
            evaluation.reasoning = (
                "Resume saved. Screening is waiting for the worker queue."
            )
            evaluation.save(update_fields=["trace_log", "reasoning"])

        logger.info(
            "Candidate %s (%s) submitted for role '%s'. Screening queued=%s.",
            candidate.name, candidate.id, target_role or "General", queued,
        )

        return Response(
            {
                "message": (
                    "Resume uploaded successfully. Screening has started."
                    if queued
                    else (
                        "Resume saved, but screening was not queued. "
                        "Redis is unreachable from this service."
                    )
                ),
                "candidate_id": str(candidate.id),
                "evaluation_id": str(evaluation.id),
                "screening_queued": queued,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @staticmethod
    def _candidate_fields(parsed: dict) -> dict:
        """Maps parsed PDF output to Candidate model fields."""
        return {
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


class CandidateListView(APIView):
    """
    GET /api/candidates/
    Returns list of all candidates with their evaluations.
    """

    def get(self, request):
        candidates = Candidate.objects.prefetch_related("evaluations").all()
        serializer = CandidateSerializer(candidates, many=True)
        return Response(serializer.data)


class CandidateDetailView(APIView):
    """
    GET /api/candidates/<id>/
    Returns full candidate details including all role evaluations.
    """

    def get(self, request, candidate_id):
        try:
            candidate = Candidate.objects.prefetch_related("evaluations").get(id=candidate_id)
        except Candidate.DoesNotExist:
            return Response({"error": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CandidateSerializer(candidate)
        return Response(serializer.data)
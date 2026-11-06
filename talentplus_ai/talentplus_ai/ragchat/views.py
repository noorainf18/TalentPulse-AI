from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from anthropic import NotFoundError
from rest_framework import status
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RagChatMessage, RagChatSession
from .serializers import RagAskSerializer, RagIndexSerializer
from .services.answer_cache import get_cached_answer, set_cached_answer
from .services.indexer import index_candidates
from .services.query_expander import rewrite_with_history
from .services.qa_chain import generate_answer
from .services.retriever import _is_broad_query, hybrid_retrieve


class RagIndexView(APIView):
    """
    POST /api/ragchat/index/
    Body: { candidate_id?: uuid }
    """

    @extend_schema(
        request=RagIndexSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Indexing completed for one or all candidates.",
            )
        },
    )
    def post(self, request):
        serializer = RagIndexSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        result = index_candidates(
            candidate_id=str(payload["candidate_id"]) if payload.get("candidate_id") else None
        )
        return Response({"status": "ok", **result}, status=status.HTTP_200_OK)


class RagAskView(APIView):
    """
    POST /api/ragchat/ask/
    Body: { question, session_id?, candidate_id?, top_k? }

    FIX SUMMARY
    -----------
    The root cause of hallucination was that candidate_id was never read from
    the incoming request and was hardcoded as None in every downstream call.
    This caused:

      1. hybrid_retrieve() to search ALL candidates' chunks instead of the
         requested candidate's chunks, pulling in irrelevant resume data.

      2. get_cached_answer() / set_cached_answer() to use a cache key that
         had no candidate dimension, so a cached answer for one candidate
         would be returned verbatim for a completely different candidate
         asking the same question.

    The fix threads candidate_id through every service call so that vector
    search, BM25, reranking, and caching are all scoped to the correct
    candidate. When no candidate_id is supplied the behaviour is unchanged
    (global search across all indexed resumes).
    """

    @extend_schema(
        request=RagAskSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="RagAskResponse",
                    fields={
                        "session_id": serializers.UUIDField(),
                        "answer": serializers.CharField(),
                        "citations": serializers.ListField(),
                        "retrieved_count": serializers.IntegerField(),
                    },
                ),
                description="RAG answer generated successfully.",
            )
        },
    )
    @transaction.atomic
    def post(self, request):
        serializer = RagAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        top_k = data.get("top_k", 6)
        question = data["question"]
        session_id = data.get("session_id")

        # FIX 1: Read candidate_id from the request payload.
        # Previously this was never read, so it was always None and every
        # retrieval call silently searched the entire corpus.
        candidate_id: str | None = (
            str(data["candidate_id"]) if data.get("candidate_id") else None
        )

        session = None
        history = []
        if session_id:
            existing_session = RagChatSession.objects.filter(id=session_id).first()
            if existing_session:
                session = existing_session
                history = list(
                    existing_session.messages.order_by("created_at").values("role", "content")[:10]
                )
                # FIX 2: If session already has a candidate_id stored and the
                # request did not supply one, inherit it from the session so
                # that follow-up questions in the same session stay scoped to
                # the correct candidate.
                if not candidate_id and hasattr(existing_session, "candidate_id"):
                    candidate_id = (
                        str(existing_session.candidate_id)
                        if existing_session.candidate_id
                        else None
                    )

        standalone_question = rewrite_with_history(question, history)
        is_broad = _is_broad_query(standalone_question)
        effective_top_k = max(top_k, 10) if is_broad else top_k

        # FIX 3: Pass candidate_id to cache lookup so that cached answers are
        # never shared across candidates.
        cached = get_cached_answer(standalone_question, effective_top_k, candidate_id)
        if cached:
            answer, citations, retrieved = cached
        else:
            # FIX 4: Pass candidate_id to hybrid_retrieve so that MMR vector
            # search and BM25 are both scoped to this candidate's chunks only.
            retrieved = hybrid_retrieve(
                question=standalone_question,
                top_k=effective_top_k,
                candidate_id=candidate_id,
            )
            try:
                answer, citations = generate_answer(
                    question=standalone_question,
                    retrieved_rows=retrieved,
                    history=history,
                )
            except NotFoundError as exc:
                return Response(
                    {
                        "error": "Configured Anthropic model is not available.",
                        "details": str(exc),
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            # FIX 5: Pass candidate_id to cache write so the stored entry is
            # keyed per-candidate.
            set_cached_answer(
                standalone_question,
                effective_top_k,
                answer,
                citations,
                retrieved,
                candidate_id,
            )

        if session is None:
            session = RagChatSession.objects.create(
                title=(
                    standalone_question[:120] + "..."
                    if len(standalone_question) > 120
                    else standalone_question
                ),
                # FIX 6: Persist candidate_id on the session so that follow-up
                # questions (FIX 2 above) can inherit it automatically.
                candidate_id=candidate_id,
                created_by=(
                    request.user if request.user and request.user.is_authenticated else None
                ),
            )

        RagChatMessage.objects.create(
            session=session, role="user", content=standalone_question, citations=[]
        )
        RagChatMessage.objects.create(
            session=session, role="assistant", content=answer, citations=citations
        )

        return Response(
            {
                "session_id": str(session.id),
                "answer": answer,
                "citations": citations,
                "retrieved_count": len(retrieved),
            },
            status=status.HTTP_200_OK,
        )
from typing import Optional

from talentplus_ai.candidates.models import Candidate

from .chunker import build_candidate_document, chunk_text
from .vectorstore import index_candidate_chunks


def index_candidate(candidate: Candidate) -> int:
    text = build_candidate_document(candidate)
    chunks = chunk_text(text)
    return index_candidate_chunks(candidate_id=str(candidate.id), chunks=chunks)


def index_candidates(candidate_id: Optional[str] = None) -> dict:
    qs = Candidate.objects.all().order_by("-created_at")
    if candidate_id:
        qs = qs.filter(id=candidate_id)

    total_candidates = 0
    total_chunks = 0
    for candidate in qs:
        total_candidates += 1
        total_chunks += index_candidate(candidate)

    return {"candidates_indexed": total_candidates, "chunks_indexed": total_chunks}

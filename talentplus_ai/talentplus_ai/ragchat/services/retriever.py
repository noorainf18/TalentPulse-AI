import logging
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi

from .reranker import rerank
from .vectorstore import fetch_candidate_corpus, mmr_search

logger = logging.getLogger(__name__)

_BROAD_QUERY_SIGNALS = [
    "top ",
    "rank ",
    "best ",
    "list ",
    "all candidates",
    "compare all",
    "who is the best",
    "shortlist",
]


def _is_broad_query(question: str) -> bool:
    q = question.lower()
    return any(signal in q for signal in _BROAD_QUERY_SIGNALS)


def _tokenize(text: str) -> List[str]:
    return [tok for tok in text.lower().split() if tok]


def _rrf_fuse(
    semantic_hits: List[Dict[str, Any]],
    bm25_hits: List[Dict[str, Any]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion - merges ranked lists without incompatible score scales.
    """
    scores: Dict[str, float] = {}
    meta_map: Dict[str, Dict[str, Any]] = {}

    for rank, hit in enumerate(semantic_hits):
        key = f'{hit["metadata"].get("candidate_id","")}-{hit["metadata"].get("chunk_index","")}'
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        meta_map[key] = hit

    for rank, hit in enumerate(bm25_hits):
        key = f'{hit["metadata"].get("candidate_id","")}-{hit["metadata"].get("chunk_index","")}'
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        if key not in meta_map:
            meta_map[key] = hit

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    result: List[Dict[str, Any]] = []
    for key, rrf_score in ranked:
        entry = {**meta_map[key], "hybrid_score": round(rrf_score, 6)}
        result.append(entry)
    return result


def _bm25_rank(question: str, corpus_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not corpus_rows:
        return []
    tokenized = [_tokenize(r["text"]) for r in corpus_rows]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(_tokenize(question))
    ranked = sorted(zip(corpus_rows, scores), key=lambda x: x[1], reverse=True)
    return [row for row, score in ranked if score > 0]


def _one_chunk_per_candidate(
    fused: List[Dict[str, Any]], top_k: int
) -> List[Dict[str, Any]]:
    seen: set = set()
    result: List[Dict[str, Any]] = []
    for hit in fused:
        cid = hit["metadata"].get("candidate_id", "")
        if cid not in seen:
            seen.add(cid)
            result.append(hit)
        if len(result) >= top_k:
            break
    return result


def hybrid_retrieve(
    question: str,
    top_k: int = 6,
    candidate_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    FIX: candidate_id is now properly threaded through to both mmr_search
    and fetch_candidate_corpus.

    Previously, candidate_id was always None here regardless of what the
    caller passed, because views.py hardcoded None. Now both the vector
    search (MMR) and the BM25 corpus fetch are scoped to the correct
    candidate, preventing chunks from other candidates from polluting
    the retrieved context.
    """
    broad = _is_broad_query(question)
    fetch_multiplier = 5 if broad else 3

    semantic_hits = mmr_search(
        question=question,
        top_k=top_k * fetch_multiplier,
        # FIX: pass candidate_id so MMR is scoped to this candidate only
        candidate_id=candidate_id,
        fetch_k=max(50, top_k * 10),
        lambda_mult=0.7 if broad else 0.6,
    )

    # FIX: pass candidate_id so BM25 corpus is scoped to this candidate only
    corpus_rows = fetch_candidate_corpus(candidate_id=candidate_id, limit=800)

    bm25_ranked = _bm25_rank(question, corpus_rows) if corpus_rows else []
    fused = _rrf_fuse(semantic_hits, bm25_ranked)

    if broad:
        fused = _one_chunk_per_candidate(fused, top_k * 2)

    reranked = rerank(query=question, candidates=fused, top_n=top_k)
    logger.info(
        "hybrid_retrieve: semantic=%s bm25=%s fused=%s reranked=%s broad=%s candidate_id=%s",
        len(semantic_hits),
        len(bm25_ranked),
        len(fused),
        len(reranked),
        broad,
        candidate_id,
    )
    return reranked
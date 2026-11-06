import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from django.core.cache import cache


_CACHE_TTL = 60 * 30


def _cache_key(question: str, top_k: int, candidate_id: Optional[str] = None) -> str:
    """
    FIX: candidate_id is now part of the cache key.
    Previously, two different candidates with the same question and top_k
    would share a cache entry, causing answers from one candidate to bleed
    into another (hallucination via stale cache).
    """
    candidate_segment = candidate_id.lower().strip() if candidate_id else "__all__"
    raw = f"{question.lower().strip()}:{top_k}:{candidate_segment}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"ragchat:answer:{digest}"


def get_cached_answer(
    question: str,
    top_k: int,
    candidate_id: Optional[str] = None,
) -> Optional[Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]]:
    key = _cache_key(question, top_k, candidate_id)
    raw = cache.get(key)
    if raw:
        data = json.loads(raw)
        return data["answer"], data["citations"], data["retrieved"]
    return None


def set_cached_answer(
    question: str,
    top_k: int,
    answer: str,
    citations: List[Dict[str, Any]],
    retrieved: List[Dict[str, Any]],
    candidate_id: Optional[str] = None,
) -> None:
    key = _cache_key(question, top_k, candidate_id)
    cache.set(
        key,
        json.dumps({"answer": answer, "citations": citations, "retrieved": retrieved}),
        timeout=_CACHE_TTL,
    )
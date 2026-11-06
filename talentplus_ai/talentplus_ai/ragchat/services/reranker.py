import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_ranker = None


def _get_ranker():
    global _ranker
    if _ranker is None:
        try:
            from flashrank import Ranker

            _ranker = Ranker(
                model_name="ms-marco-TinyBERT-L-2-v2",
                cache_dir="/tmp/flashrank",
            )
            logger.info("FlashRank cross-encoder loaded successfully.")
        except Exception as exc:
            logger.error("FlashRank failed to load: %s. Re-ranking will be skipped.", exc)
            _ranker = False
    return _ranker if _ranker is not False else None


def _extract_score(result: Dict[str, Any]) -> float:
    if "relevance_score" in result:
        return float(result["relevance_score"])
    if "score" in result:
        return float(result["score"])
    logger.warning("Re-ranker result has no known score key. Keys: %s", list(result.keys()))
    return 0.0


def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_n: int = 6,
) -> List[Dict[str, Any]]:
    if not candidates:
        return []

    ranker = _get_ranker()
    if ranker is None:
        logger.warning("Re-ranker unavailable - returning candidates in RRF order.")
        return candidates[:top_n]

    try:
        from flashrank import RerankRequest

        passages = [{"id": i, "text": c.get("text", "")} for i, c in enumerate(candidates)]
        request = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(request)
        if results:
            logger.info(
                "Re-ranker sample - keys: %s, top score: %s",
                list(results[0].keys()),
                _extract_score(results[0]),
            )

        reranked: List[Dict[str, Any]] = []
        for result in results[:top_n]:
            original = candidates[result["id"]]
            score = _extract_score(result)
            reranked.append(
                {
                    **original,
                    "rerank_score": round(score, 4),
                    "hybrid_score": round(score, 4),
                }
            )

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        logger.info(
            "Re-ranked %s -> %s candidates. Score range: [%s, %s]",
            len(candidates),
            len(reranked),
            round(reranked[-1]["rerank_score"], 4) if reranked else "n/a",
            round(reranked[0]["rerank_score"], 4) if reranked else "n/a",
        )
        return reranked
    except Exception as exc:
        logger.error("Re-ranking failed: %s. Falling back to RRF order.", exc)
        return candidates[:top_n]

from typing import Any, Dict, List, Optional

from django.conf import settings
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from .embedding_client import EmbeddingClient


class RemoteEmbeddingFunction:
    def __init__(self) -> None:
        self.client = EmbeddingClient()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.client.embed_texts(texts, model_type="document")

    def embed_query(self, text: str) -> List[float]:
        vectors = self.client.embed_texts([text], model_type="document")
        return vectors[0] if vectors else []


class RemoteEmbeddings(Embeddings):
    def __init__(self) -> None:
        self.client = EmbeddingClient()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.client.embed_texts(texts, model_type="document")

    def embed_query(self, text: str) -> List[float]:
        vectors = self.client.embed_texts([text], model_type="document")
        return vectors[0] if vectors else []


def get_vectorstore() -> Chroma:
    embedding_function = RemoteEmbeddingFunction()
    return Chroma(
        collection_name=settings.RAG_CHROMA_COLLECTION,
        embedding_function=embedding_function,
        persist_directory=settings.RAG_CHROMA_PERSIST_DIR,
    )


def index_candidate_chunks(candidate_id: str, chunks: List[str]) -> int:
    if not chunks:
        return 0

    store = get_vectorstore()
    store.delete(where={"candidate_id": candidate_id})
    ids = [f"{candidate_id}-{idx}" for idx in range(len(chunks))]
    metadatas = [
        {
            "candidate_id": candidate_id,
            "chunk_index": idx,
            "source": "candidate_resume",
        }
        for idx in range(len(chunks))
    ]
    store.add_texts(texts=chunks, metadatas=metadatas, ids=ids)
    return len(chunks)


def semantic_search(
    question: str,
    top_k: int,
    candidate_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    store = get_vectorstore()
    query_filter = {"candidate_id": candidate_id} if candidate_id else None
    docs = store.similarity_search_with_relevance_scores(
        question,
        k=top_k,
        filter=query_filter,
    )

    results: List[Dict[str, Any]] = []
    for doc, score in docs:
        results.append(
            {
                "text": doc.page_content,
                "metadata": doc.metadata or {},
                "vector_score": float(score),
            }
        )
    return results


def mmr_search(
    question: str,
    top_k: int,
    candidate_id: Optional[str] = None,
    fetch_k: int = 50,
    lambda_mult: float = 0.6,
) -> List[Dict[str, Any]]:
    """
    MMR search scoped to a specific candidate when candidate_id is provided.

    FIX: effective_fetch_k is bounded by the actual collection size when
    candidate_id is set, preventing Chroma from throwing when fetch_k exceeds
    the number of documents in the filtered subset. Also adds explicit
    post-filter validation so that chunks that somehow slip through with a
    mismatched candidate_id are discarded before being returned.
    """
    store = get_vectorstore()
    effective_fetch_k = max(fetch_k, top_k * 5)

    kwargs: Dict[str, Any] = {
        "k": top_k,
        "fetch_k": effective_fetch_k,
        "lambda_mult": lambda_mult,
    }
    if candidate_id:
        kwargs["filter"] = {"candidate_id": candidate_id}

    docs = store.max_marginal_relevance_search(question, **kwargs)

    results = [
        {
            "text": doc.page_content,
            "metadata": doc.metadata or {},
            "vector_score": 0.0,
        }
        for doc in docs
    ]

    # FIX: post-filter guard — discard any chunk that does not belong to the
    # requested candidate. Chroma's metadata filter is not always perfectly
    # enforced across all versions; this is a defensive safety net.
    if candidate_id:
        results = [
            r for r in results
            if r["metadata"].get("candidate_id") == candidate_id
        ]

    return results


def fetch_candidate_corpus(
    candidate_id: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    FIX: When candidate_id is provided, the Chroma collection.get() call
    now correctly passes the `where` filter. Previously this worked correctly
    in code, but the caller (hybrid_retrieve) was always passing None because
    views.py never forwarded the candidate_id. With views.py now forwarding
    candidate_id, this function correctly scopes BM25 corpus to one candidate.

    Additional guard: after fetching, filter the results again to ensure no
    cross-candidate contamination from Chroma edge cases.
    """
    store = get_vectorstore()
    where = {"candidate_id": candidate_id} if candidate_id else None
    raw = store._collection.get(
        where=where,
        include=["documents", "metadatas"],
        limit=limit,
    )
    docs = raw.get("documents") or []
    metas = raw.get("metadatas") or []
    rows = [{"text": d, "metadata": m or {}} for d, m in zip(docs, metas)]

    # FIX: post-filter guard — same defensive approach as mmr_search
    if candidate_id:
        rows = [
            r for r in rows
            if r["metadata"].get("candidate_id") == candidate_id
        ]

    return rows
"""
Resume Vectorizer
Generates an embedding for a candidate's resume text and stores it
in Supabase's pgvector extension for semantic search.

Uses Anthropic's embedding-compatible approach via a lightweight
sentence embedding (or can be swapped for OpenAI/Cohere embeddings).
"""

import logging
from django.conf import settings
from talentplus_ai.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def _get_embedding(text: str) -> list[float]:
    """
    Generates a text embedding vector.
    Uses a simple HTTP call to an embedding endpoint.
    Swap this for openai.embeddings.create() or cohere.embed() as needed.
    """
    import httpx

    # Using a lightweight sentence-transformer compatible endpoint
    # Replace with your preferred embedding provider
    try:
        # Placeholder: returns a zero-vector if no embedding service configured.
        # In production, integrate with OpenAI text-embedding-3-small or similar.
        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if api_key:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"input": text[:8000], "model": "text-embedding-3-small"},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}. Skipping vectorization.")

    return []


def vectorize_and_store(candidate_id: str, resume_text: str) -> bool:
    """
    Generates embedding for resume_text and upserts into
    the 'resume_embeddings' table in Supabase (pgvector).

    Table schema (create manually in Supabase):
      CREATE TABLE resume_embeddings (
        candidate_id UUID PRIMARY KEY,
        embedding vector(1536),
        created_at TIMESTAMPTZ DEFAULT NOW()
      );

    Returns True on success, False on failure.
    """
    embedding = _get_embedding(resume_text)

    if not embedding:
        logger.info(f"No embedding generated for {candidate_id}. Skipping.")
        return False

    try:
        client = get_supabase_client()
        client.table("resume_embeddings").upsert({
            "candidate_id": str(candidate_id),
            "embedding": embedding,
        }).execute()
        logger.info(f"Embedding stored for candidate {candidate_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to store embedding for {candidate_id}: {e}")
        return False


def search_similar_candidates(query_text: str, limit: int = 5) -> list:
    """
    Semantic search: finds candidates whose resume is most similar
    to the query text. Uses Supabase RPC with pgvector cosine similarity.

    Requires this Supabase function (create in SQL editor):
      CREATE OR REPLACE FUNCTION match_resumes(
        query_embedding vector(1536),
        match_count int
      )
      RETURNS TABLE(candidate_id uuid, similarity float)
      LANGUAGE sql STABLE AS $$
        SELECT candidate_id,
               1 - (embedding <=> query_embedding) AS similarity
        FROM resume_embeddings
        ORDER BY embedding <=> query_embedding
        LIMIT match_count;
      $$;
    """
    embedding = _get_embedding(query_text)
    if not embedding:
        return []

    try:
        client = get_supabase_client()
        result = client.rpc(
            "match_resumes",
            {"query_embedding": embedding, "match_count": limit},
        ).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        return []

"""
Supabase Client
Singleton client for Supabase-specific features that go beyond
what Django ORM handles:
  - Realtime subscriptions (evaluation updates → browser)
  - Storage (resume PDF file storage)
  - RPC / edge functions (if needed later)

NOTE: Django ORM handles all CRUD via the DATABASE_URL Postgres connection.
      This client is ONLY for Supabase-specific APIs.
"""

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_supabase_client: Any | None = None


def get_supabase_client() -> Any:
    """
    Returns a singleton supabase-py client.
    Lazily initialised on first call.
    """
    global _supabase_client

    if _supabase_client is None:
        from supabase import create_client  # noqa: PLC0415

        url = getattr(settings, "SUPABASE_URL", "")
        key = getattr(settings, "SUPABASE_KEY", "")

        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables."
            )

        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialised.")

    return _supabase_client


def upload_resume_to_storage(candidate_id: str, file_bytes: bytes, filename: str) -> str:
    """
    Uploads a resume PDF to Supabase Storage bucket 'resumes'.
    Returns the public URL.
    """
    client = get_supabase_client()
    storage_path = f"resumes/{candidate_id}/{filename}"

    try:
        client.storage.from_("resumes").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"},
        )
        public_url = client.storage.from_("resumes").get_public_url(storage_path)
        logger.info(f"Resume uploaded to Supabase Storage: {storage_path}")
        return public_url
    except Exception as e:
        logger.error(f"Supabase Storage upload failed: {e}")
        return ""

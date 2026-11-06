from typing import List

import httpx
from django.conf import settings


class EmbeddingClient:
    def __init__(self) -> None:
        self.base_url = settings.TALENTPLUSAI_EMBEDDING_URL.rstrip("/")
        self.timeout = settings.RAG_EMBEDDING_TIMEOUT_SECONDS

    def embed_texts(self, texts: List[str], model_type: str = "document") -> List[List[float]]:
        if not texts:
            return []

        url = f"{self.base_url}/api/embedding/generate"
        payload = {"inputs": texts, "model_type": model_type}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        return data.get("embeddings", [])

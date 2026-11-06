from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODELS, EMBEDDING_TARGET_DIM


class EmbeddingModel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.models: Dict[str, SentenceTransformer] = {}
        self.model_configs = EMBEDDING_MODELS
        self.target_dim = EMBEDDING_TARGET_DIM

    def _ensure_model_loaded(self, model_type: str):
        if model_type not in self.model_configs:
            raise ValueError(f"Unknown model type: {model_type}")
        if model_type not in self.models:
            self.models[model_type] = SentenceTransformer(self.model_configs[model_type]["model_name"])

    def generate(self, text: str, model_type: str = "document") -> List[float]:
        self._ensure_model_loaded(model_type)
        embedding = self.models[model_type].encode(text, normalize_embeddings=True).tolist()
        return self._pad_embedding(embedding)

    def _pad_embedding(self, embedding: List[float]) -> List[float]:
        dim = len(embedding)
        if dim < self.target_dim:
            return np.pad(embedding, (0, self.target_dim - dim), mode="constant").tolist()
        return embedding


embedding_model = EmbeddingModel()

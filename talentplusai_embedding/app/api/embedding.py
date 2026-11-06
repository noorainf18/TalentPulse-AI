import logging
from typing import Dict, List

from fastapi import APIRouter, Body, HTTPException

from app.models.embedding import embedding_model

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate")
async def generate_embedding(
    inputs: List[str] = Body(..., description="Input texts for embedding generation"),
    model_type: str = Body("document", description="Model type: document or intent"),
) -> Dict[str, List[List[float]]]:
    try:
        embeddings = [embedding_model.generate(text, model_type=model_type) for text in inputs]
        return {"embeddings": embeddings}
    except ValueError as exc:
        logger.error("Invalid embedding request: %s", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Embedding generation failed")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(exc)}")

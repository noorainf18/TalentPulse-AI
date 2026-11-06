import os

from dotenv import load_dotenv

load_dotenv()

EMBEDDING_TARGET_DIM = int(os.getenv("EMBEDDING_TARGET_DIM", "768"))
EMBEDDING_HOST = os.getenv("EMBEDDING_HOST", "127.0.0.1")
EMBEDDING_PORT = int(os.getenv("EMBEDDING_PORT", "8010"))

EMBEDDING_MODELS = {
    "document": {"model_name": os.getenv("DOCUMENT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")},
    "intent": {"model_name": os.getenv("INTENT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")},
}

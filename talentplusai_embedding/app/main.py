from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import embedding

app = FastAPI(
    title="TalentPlusAI Embedding Service",
    description="Embedding API used by TalentPlus AI RAG chatbot",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(embedding.router, prefix="/api/embedding", tags=["embedding"])


@app.get("/health")
async def health():
    return {"status": "healthy"}

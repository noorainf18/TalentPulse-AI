from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from talentplus_ai.ragchat.prompts.qa_prompt import RAG_QA_SYSTEM_PROMPT


def _build_context(rows: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    blocks: List[str] = []
    citations: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        meta = row.get("metadata") or {}
        candidate_id = meta.get("candidate_id")
        chunk_index = meta.get("chunk_index")
        rerank_score = row.get("rerank_score", row.get("hybrid_score", 0.0))
        blocks.append(
            f"[{idx}] candidate_id={candidate_id} chunk={chunk_index} "
            f"retrieval_score={round(float(rerank_score), 4)}\n{row.get('text','')}"
        )
        citations.append(
            {
                "rank": idx,
                "candidate_id": candidate_id,
                "chunk_index": chunk_index,
                "score": round(float(rerank_score), 4),
            }
        )
    return "\n\n".join(blocks), citations


def generate_answer(
    question: str,
    retrieved_rows: List[Dict[str, Any]],
    history: Optional[List[dict]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    context, citations = _build_context(retrieved_rows)
    if not context.strip():
        return "I could not find matching resume evidence in the vector store.", []

    llm = ChatAnthropic(
        model=settings.RAG_ANTHROPIC_MODEL,
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        temperature=0,
        max_tokens=1200,
    )
    messages = [SystemMessage(content=RAG_QA_SYSTEM_PROMPT)]

    if history:
        for turn in history[-6:]:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            elif turn["role"] == "assistant":
                messages.append(AIMessage(content=turn["content"]))

    user_prompt = f"User question:\n{question}\n\nRetrieved resume context snippets:\n{context}"
    messages.append(HumanMessage(content=user_prompt))
    response = llm.invoke(messages)
    return str(response.content), citations

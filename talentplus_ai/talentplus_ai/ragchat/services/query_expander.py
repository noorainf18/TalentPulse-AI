from typing import List, Dict

from django.conf import settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


def _get_fast_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.RAG_ANTHROPIC_MODEL,
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        temperature=0,
        max_tokens=300,
    )


def rewrite_with_history(question: str, history: List[Dict[str, str]]) -> str:
    if not history:
        return question

    history_text = "\n".join(
        f'{m["role"].upper()}: {m["content"][:300]}' for m in history[-6:]
    )
    llm = _get_fast_llm()
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are a query rewriter. Given conversation history and a new question, "
                    "rewrite the question to be fully self-contained and specific. "
                    "If the question is already standalone, return it exactly as-is. "
                    "Return ONLY the rewritten question. No explanation."
                )
            ),
            HumanMessage(content=f"History:\n{history_text}\n\nNew question: {question}"),
        ]
    )
    return str(response.content).strip()

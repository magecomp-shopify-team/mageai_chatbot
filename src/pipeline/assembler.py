import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import load_app_config
from src.core.tokenizer import count_tokens, truncate_to_tokens
from src.pipeline.retriever import Chunk, retrieve

logger = logging.getLogger(__name__)


@dataclass
class AssembledContext:
    system_prompt: str
    messages: list[dict]
    rag_chunks: list[Chunk] = field(default_factory=list)
    token_breakdown: dict = field(default_factory=dict)


async def assemble(
    user_message: str,
    session_id: str,
    app_id: str,
    db: AsyncSession | None = None,
) -> AssembledContext:
    from config.settings import settings
    from src.pipeline.history import get_history

    cfg = load_app_config(app_id)

    # System prompt
    rules_text = "\n".join(f"- {r}" for r in cfg.rules)
    system_prompt = f"Role: {cfg.role}\nTone: {cfg.tone}\nRules:\n{rules_text}"
    system_tokens = count_tokens(system_prompt)
    if system_tokens > settings.DEFAULT_MAX_SYSTEM_TOKENS:
        system_prompt = truncate_to_tokens(system_prompt, settings.DEFAULT_MAX_SYSTEM_TOKENS)
        system_tokens = settings.DEFAULT_MAX_SYSTEM_TOKENS

    # RAG retrieval
    chunks = await retrieve(
        query=user_message,
        app_id=app_id,
        top_k=cfg.top_k_chunks,
        min_relevance=cfg.min_relevance,
    )
    rag_text = "\n\n".join(f"[{c.source_file}]\n{c.text}" for c in chunks)
    rag_tokens = count_tokens(rag_text)

    if rag_tokens > settings.DEFAULT_MAX_RAG_TOKENS:
        rag_text = truncate_to_tokens(rag_text, settings.DEFAULT_MAX_RAG_TOKENS)
        rag_tokens = settings.DEFAULT_MAX_RAG_TOKENS

    if rag_text:
        system_prompt += f"\n\nContext:\n{rag_text}"

    # History
    history: list[dict] = []
    if db:
        history = await get_history(
            db=db,
            session_id=session_id,
            app_id=app_id,
            max_turns=cfg.max_history_turns,
            max_tokens=settings.DEFAULT_MAX_HISTORY_TOKENS,
        )

    history_tokens = sum(count_tokens(m["content"]) for m in history)
    user_tokens = count_tokens(user_message)

    messages = history + [{"role": "user", "content": user_message}]

    return AssembledContext(
        system_prompt=system_prompt,
        messages=messages,
        rag_chunks=chunks,
        token_breakdown={
            "system": system_tokens,
            "rag": rag_tokens,
            "history": history_tokens,
            "user": user_tokens,
        },
    )

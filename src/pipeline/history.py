import logging
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Base
from src.core.tokenizer import count_tokens

logger = logging.getLogger(__name__)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        Index("idx_session_app", "session_id", "app_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False)
    app_id = Column(String(64), nullable=False)
    role = Column(String(16), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


async def save_turn(
    db: AsyncSession, session_id: str, app_id: str, role: str, content: str
) -> "ConversationTurn":
    tokens = count_tokens(content)
    now = datetime.utcnow()
    turn = ConversationTurn(
        session_id=session_id,
        app_id=app_id,
        role=role,
        content=content,
        token_count=tokens,
        created_at=now,
    )
    db.add(turn)
    await db.commit()
    return turn


async def get_history(
    db: AsyncSession,
    session_id: str,
    app_id: str,
    max_turns: int = 6,
    max_tokens: int = 800,
) -> list[dict]:
    result = await db.execute(
        select(ConversationTurn)
        .where(
            ConversationTurn.session_id == session_id,
            ConversationTurn.app_id == app_id,
        )
        .order_by(ConversationTurn.created_at.desc())
        .limit(max_turns * 2)
    )
    turns = list(reversed(result.scalars().all()))

    messages: list[dict] = []
    total_tokens = 0
    for turn in turns:
        total_tokens += turn.token_count
        if total_tokens > max_tokens:
            break
        messages.append({"role": turn.role, "content": turn.content})

    return messages


async def compress_history(
    db: AsyncSession,
    session_id: str,
    app_id: str,
) -> str:
    """Summarise history using the configured AI provider. Returns summary text."""
    from config.settings import settings
    from src.ai.registry import registry
    from src.core.exceptions import HistoryCompressionError

    messages = await get_history(db, session_id, app_id, max_turns=20, max_tokens=9999)
    if not messages:
        return ""

    history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)

    try:
        from src.core.config import load_app_config
        cfg = load_app_config(app_id)
        provider_id = cfg.provider
    except Exception:
        provider_id = settings.DEFAULT_PROVIDER

    if not registry.is_available(provider_id):
        provider_id = registry.get_all_ids()[0] if registry.get_all_ids() else None

    if not provider_id:
        raise HistoryCompressionError("No provider available for history compression")

    try:
        provider = registry.get(provider_id)
        result = await provider.complete(
            system_prompt="Summarise the conversation in 2-3 sentences. Output only the summary.",
            messages=[{"role": "user", "content": history_text}],
            model=settings.DEFAULT_MODEL,
            max_tokens=150,
            temperature=0.3,
        )
        return result.text
    except Exception as exc:
        raise HistoryCompressionError(str(exc)) from exc


async def clear_session(db: AsyncSession, session_id: str, app_id: str) -> None:
    result = await db.execute(
        select(ConversationTurn).where(
            ConversationTurn.session_id == session_id,
            ConversationTurn.app_id == app_id,
        )
    )
    for turn in result.scalars().all():
        await db.delete(turn)
    await db.commit()

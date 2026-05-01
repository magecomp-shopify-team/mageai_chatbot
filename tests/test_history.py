import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.pipeline.history import clear_session, get_history, save_turn


@pytest.mark.asyncio
async def test_save_and_get_history(db_session: AsyncSession):
    await save_turn(db_session, "sess-1", "test_app", "user", "Hello")
    await save_turn(db_session, "sess-1", "test_app", "assistant", "Hi there!")

    history = await get_history(db_session, "sess-1", "test_app", max_turns=10, max_tokens=9999)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_history_isolation_by_app(db_session: AsyncSession):
    await save_turn(db_session, "sess-2", "app_a", "user", "Message in app_a")
    await save_turn(db_session, "sess-2", "app_b", "user", "Message in app_b")

    history_a = await get_history(db_session, "sess-2", "app_a")
    history_b = await get_history(db_session, "sess-2", "app_b")

    assert len(history_a) == 1
    assert history_a[0]["content"] == "Message in app_a"
    assert len(history_b) == 1
    assert history_b[0]["content"] == "Message in app_b"


@pytest.mark.asyncio
async def test_clear_session(db_session: AsyncSession):
    await save_turn(db_session, "sess-clear", "test_app", "user", "To be cleared")
    await clear_session(db_session, "sess-clear", "test_app")
    history = await get_history(db_session, "sess-clear", "test_app")
    assert history == []

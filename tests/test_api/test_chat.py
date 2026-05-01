from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import NormalisedResponse


@pytest.mark.asyncio
async def test_chat_app_not_found_returns_404(client):
    r = await client.post("/chat/", json={
        "app_id": "nonexistent_app_xyz",
        "session_id": "sess-1",
        "message": "hello",
    })
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_chat_returns_reply(client):
    mock_result = NormalisedResponse(
        text="Test reply", input_tokens=10, output_tokens=5,
        model="claude-haiku-4-5-20251001", provider="anthropic",
        finish_reason="stop", raw={}
    )
    mock_cfg = MagicMock()
    mock_cfg.role = "assistant"
    mock_cfg.tone = "helpful"
    mock_cfg.rules = []
    mock_cfg.top_k_chunks = 2
    mock_cfg.min_relevance = 0.0
    mock_cfg.max_history_turns = 4
    mock_cfg.max_response_tokens = 256
    mock_cfg.temperature = 0.7
    mock_cfg.provider = "anthropic"
    mock_cfg.model = "claude-haiku-4-5-20251001"

    with patch("src.api.routers.chat.load_app_config", return_value=mock_cfg), \
         patch("src.api.routers.chat.assemble", new_callable=AsyncMock) as mock_assemble, \
         patch("src.api.routers.chat.ai_router.complete", new_callable=AsyncMock, return_value=mock_result), \
         patch("src.api.routers.chat.save_turn", new_callable=AsyncMock):

        mock_assemble.return_value = MagicMock(
            system_prompt="sys", messages=[{"role": "user", "content": "hello"}]
        )
        r = await client.post("/chat/", json={
            "app_id": "ecommerce",
            "session_id": "sess-test",
            "message": "hello",
        })

    assert r.status_code == 200
    data = r.json()
    assert data["reply"] == "Test reply"
    assert data["provider_used"] == "anthropic"

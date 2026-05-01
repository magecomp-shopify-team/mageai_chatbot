from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.assembler import AssembledContext, assemble


@pytest.mark.asyncio
async def test_assemble_returns_context():
    mock_cfg = MagicMock()
    mock_cfg.role = "Test role"
    mock_cfg.tone = "neutral"
    mock_cfg.rules = ["Rule 1", "Rule 2"]
    mock_cfg.top_k_chunks = 2
    mock_cfg.min_relevance = 0.0
    mock_cfg.max_history_turns = 4
    mock_cfg.max_response_tokens = 256
    mock_cfg.temperature = 0.7

    with patch("src.pipeline.assembler.load_app_config", return_value=mock_cfg), \
         patch("src.pipeline.assembler.retrieve", new_callable=AsyncMock, return_value=[]), \
         patch("src.pipeline.assembler.get_history", new_callable=AsyncMock, return_value=[]):
        ctx = await assemble("What is the return policy?", "sess-x", "ecommerce", db=MagicMock())

    assert isinstance(ctx, AssembledContext)
    assert "Test role" in ctx.system_prompt
    assert ctx.messages[-1]["role"] == "user"
    assert ctx.messages[-1]["content"] == "What is the return policy?"


@pytest.mark.asyncio
async def test_assemble_includes_rag_context():
    from src.pipeline.retriever import Chunk

    mock_cfg = MagicMock()
    mock_cfg.role = "Assistant"
    mock_cfg.tone = "helpful"
    mock_cfg.rules = []
    mock_cfg.top_k_chunks = 2
    mock_cfg.min_relevance = 0.0
    mock_cfg.max_history_turns = 4
    mock_cfg.max_response_tokens = 256
    mock_cfg.temperature = 0.7

    chunks = [Chunk(text="Return policy: 30 days.", source_file="policy.txt", chunk_index=0, distance=0.1)]

    with patch("src.pipeline.assembler.load_app_config", return_value=mock_cfg), \
         patch("src.pipeline.assembler.retrieve", new_callable=AsyncMock, return_value=chunks), \
         patch("src.pipeline.assembler.get_history", new_callable=AsyncMock, return_value=[]):
        ctx = await assemble("Return policy?", "sess-y", "ecommerce", db=MagicMock())

    assert "Return policy: 30 days." in ctx.system_prompt
    assert ctx.rag_chunks == chunks

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.retriever import Chunk, retrieve


@pytest.mark.asyncio
async def test_retrieve_returns_empty_when_no_collection():
    with patch("src.pipeline.retriever.collection_exists", return_value=False):
        result = await retrieve("test query", "nonexistent_app")
        assert result == []


@pytest.mark.asyncio
async def test_retrieve_returns_chunks():
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["chunk text one", "chunk text two"]],
        "metadatas": [[
            {"source_file": "doc.txt", "chunk_index": 0},
            {"source_file": "doc.txt", "chunk_index": 1},
        ]],
        "distances": [[0.1, 0.3]],
    }

    with patch("src.pipeline.retriever.collection_exists", return_value=True), \
         patch("src.pipeline.retriever.encode", return_value=[[0.1] * 384]), \
         patch("src.pipeline.retriever.get_or_create_collection", return_value=mock_collection):
        result = await retrieve("test query", "test_app", top_k=2, min_relevance=0.0)

    assert len(result) == 2
    assert isinstance(result[0], Chunk)
    assert result[0].text == "chunk text one"
    assert result[0].source_file == "doc.txt"


@pytest.mark.asyncio
async def test_retrieve_filters_by_relevance():
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["relevant chunk", "irrelevant chunk"]],
        "metadatas": [[
            {"source_file": "a.txt", "chunk_index": 0},
            {"source_file": "b.txt", "chunk_index": 0},
        ]],
        "distances": [[0.1, 0.95]],  # second has distance 0.95 → relevance 0.05
    }

    with patch("src.pipeline.retriever.collection_exists", return_value=True), \
         patch("src.pipeline.retriever.encode", return_value=[[0.1] * 384]), \
         patch("src.pipeline.retriever.get_or_create_collection", return_value=mock_collection):
        result = await retrieve("query", "app", top_k=4, min_relevance=0.5)

    assert len(result) == 1
    assert result[0].text == "relevant chunk"

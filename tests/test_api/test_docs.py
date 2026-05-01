import pytest


@pytest.mark.asyncio
async def test_list_docs_public(client):
    """GET /docs/{app_id} is public."""
    r = await client.get("/docs/ecommerce")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_upload_without_auth_returns_401(client):
    r = await client.post("/docs/upload", data={"app_id": "ecommerce"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_upload_with_auth_and_valid_file(client, auth_headers, tmp_path):
    """Upload a .txt file and verify it returns an index result."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.pipeline.indexer import IndexResult

    mock_result = IndexResult(
        app_id="ecommerce", filename="test.txt", chunks_indexed=3, file_hash="abc123"
    )

    with patch("src.api.routers.docs.index_file", new_callable=AsyncMock, return_value=mock_result), \
         patch("src.api.routers.docs.log_action", new_callable=AsyncMock):
        r = await client.post(
            "/docs/upload",
            headers=auth_headers,
            data={"app_id": "ecommerce"},
            files={"file": ("test.txt", b"hello world " * 50, "text/plain")},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["chunks_indexed"] == 3
    assert data["filename"] == "test.txt"

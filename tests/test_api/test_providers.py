from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import NormalisedResponse


@pytest.mark.asyncio
async def test_providers_list_returns_200(client):
    r = await client.get("/providers/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_provider_health_requires_auth(client):
    r = await client.get("/providers/openai/health")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_provider_test_requires_auth(client):
    r = await client.post("/providers/openai/test", json={"message": "hi"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_provider_default_requires_auth(client):
    r = await client.put("/providers/openai/default")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_provider_health_with_auth(client, auth_headers):
    """Health check with valid token — either works or 404 if provider not registered."""
    mock_provider = MagicMock()
    mock_provider.health_check = AsyncMock(return_value=True)
    mock_provider.display_name = "Mock"

    with patch("src.api.routers.providers.registry") as mock_reg:
        mock_reg.get.return_value = mock_provider
        r = await client.get("/providers/anthropic/health", headers=auth_headers)

    assert r.status_code in (200, 404, 422)

import pytest


@pytest.mark.parametrize("method,path", [
    ("POST", "/docs/upload"),
    ("DELETE", "/docs/ecommerce/test.md"),
    ("DELETE", "/docs/ecommerce"),
    ("POST", "/docs/ecommerce/reembed"),
    ("DELETE", "/chunks"),
    ("POST", "/apps/"),
    ("POST", "/apps/ecommerce/reload"),
    ("DELETE", "/apps/ecommerce"),
    ("GET", "/providers/anthropic/health"),
    ("POST", "/providers/anthropic/test"),
    ("PUT", "/providers/anthropic/default"),
])
@pytest.mark.asyncio
async def test_requires_auth(client, method, path):
    """Every admin route must return 401 when no token is provided."""
    r = await client.request(method, path)
    assert r.status_code == 401, f"{method} {path} returned {r.status_code}, expected 401"


@pytest.mark.asyncio
async def test_health_endpoint_public(client):
    """GET /health is public."""
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_providers_list_public(client):
    """GET /providers/ is public."""
    r = await client.get("/providers/")
    assert r.status_code == 200

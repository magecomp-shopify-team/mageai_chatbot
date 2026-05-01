from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ai.base import AIProvider, NormalisedResponse
from src.ai.registry import ProviderRegistry
from src.core.exceptions import ProviderNotFoundError


class MockProvider(AIProvider):
    provider_id = "mock"
    display_name = "Mock Provider"

    async def complete(self, system_prompt, messages, model, max_tokens=512,
                       temperature=0.7, stream=False):
        return NormalisedResponse(
            text="mocked", input_tokens=5, output_tokens=3,
            model=model, provider="mock", finish_reason="stop", raw={}
        )

    async def list_models(self):
        return ["mock-model"]

    async def health_check(self):
        return True

    def count_tokens(self, text):
        return len(text.split())


def test_registry_register_and_get():
    reg = ProviderRegistry()
    reg.register(MockProvider())
    p = reg.get("mock")
    assert p.provider_id == "mock"


def test_registry_raises_on_unknown():
    reg = ProviderRegistry()
    with pytest.raises(ProviderNotFoundError):
        reg.get("doesnotexist")


def test_registry_is_available():
    reg = ProviderRegistry()
    assert not reg.is_available("mock")
    reg.register(MockProvider())
    assert reg.is_available("mock")


def test_registry_get_all_ids():
    reg = ProviderRegistry()
    reg.register(MockProvider())
    assert "mock" in reg.get_all_ids()


@pytest.mark.asyncio
async def test_router_uses_app_config_provider(monkeypatch):
    from src.ai import router as ai_router
    from src.pipeline.assembler import AssembledContext

    reg = ProviderRegistry()
    reg.register(MockProvider())
    monkeypatch.setattr("src.ai.router.registry", reg)

    mock_cfg = MagicMock()
    mock_cfg.provider = "mock"
    mock_cfg.model = "mock-model"
    mock_cfg.max_response_tokens = 256
    mock_cfg.temperature = 0.7
    monkeypatch.setattr("src.ai.router.load_app_config", lambda app_id: mock_cfg)

    ctx = AssembledContext(
        system_prompt="You are helpful.",
        messages=[{"role": "user", "content": "hi"}],
    )
    result = await ai_router.complete(ctx, "test_app")
    assert result.provider == "mock"
    assert result.text == "mocked"


@pytest.mark.asyncio
async def test_router_falls_back_to_default(monkeypatch):
    from src.ai import router as ai_router
    from src.pipeline.assembler import AssembledContext

    reg = ProviderRegistry()
    reg.register(MockProvider())
    monkeypatch.setattr("src.ai.router.registry", reg)
    monkeypatch.setattr("src.ai.router.settings", MagicMock(DEFAULT_PROVIDER="mock", DEFAULT_MODEL="mock-model"))
    monkeypatch.setattr("src.ai.router.load_app_config", MagicMock(side_effect=Exception("no config")))

    ctx = AssembledContext(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])
    result = await ai_router.complete(ctx, "unknown_app")
    assert result.provider == "mock"

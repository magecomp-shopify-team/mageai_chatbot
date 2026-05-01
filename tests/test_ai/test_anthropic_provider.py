from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import NormalisedResponse
from src.core.exceptions import ProviderAuthError, ProviderRateLimitError


@pytest.mark.asyncio
async def test_complete_returns_normalised():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Hello from Claude")]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5
    mock_response.model = "claude-haiku-4-5-20251001"
    mock_response.stop_reason = "stop"
    mock_response.model_dump.return_value = {}

    with patch("src.ai.providers.anthropic_provider.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        from src.ai.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        result = await provider.complete(
            "You are helpful.",
            [{"role": "user", "content": "hi"}],
            "claude-haiku-4-5-20251001",
        )

    assert isinstance(result, NormalisedResponse)
    assert result.text == "Hello from Claude"
    assert result.provider == "anthropic"
    assert result.input_tokens == 10


@pytest.mark.asyncio
async def test_complete_maps_401_to_provider_auth_error():
    import anthropic

    with patch("src.ai.providers.anthropic_provider.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.AuthenticationError(
                message="Invalid API key", response=MagicMock(), body={}
            )
        )

        from src.ai.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        with pytest.raises(ProviderAuthError):
            await provider.complete("sys", [{"role": "user", "content": "hi"}], "claude-haiku-4-5-20251001")


@pytest.mark.asyncio
async def test_complete_maps_429_to_rate_limit_error():
    import anthropic

    with patch("src.ai.providers.anthropic_provider.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.RateLimitError(
                message="Rate limit", response=MagicMock(), body={}
            )
        )

        from src.ai.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        with pytest.raises(ProviderRateLimitError):
            await provider.complete("sys", [{"role": "user", "content": "hi"}], "claude-haiku-4-5-20251001")


@pytest.mark.asyncio
async def test_list_models():
    with patch("src.ai.providers.anthropic_provider.anthropic.AsyncAnthropic"):
        from src.ai.providers.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        models = await provider.list_models()
    assert "claude-haiku-4-5-20251001" in models
    assert len(models) > 0

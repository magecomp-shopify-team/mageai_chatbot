from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import NormalisedResponse
from src.core.exceptions import ProviderAuthError, ProviderRateLimitError


def _mock_openai_response():
    choice = MagicMock()
    choice.message.content = "OpenAI reply"
    choice.finish_reason = "stop"
    r = MagicMock()
    r.choices = [choice]
    r.usage.prompt_tokens = 12
    r.usage.completion_tokens = 6
    r.model = "gpt-4o-mini"
    r.model_dump.return_value = {}
    return r


@pytest.mark.asyncio
async def test_complete_returns_normalised():
    with patch("src.ai.providers.openai_provider.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=_mock_openai_response())

        from src.ai.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        result = await provider.complete("sys", [{"role": "user", "content": "hi"}], "gpt-4o-mini")

    assert isinstance(result, NormalisedResponse)
    assert result.text == "OpenAI reply"
    assert result.provider == "openai"


@pytest.mark.asyncio
async def test_complete_maps_401_to_auth_error():
    import openai

    with patch("src.ai.providers.openai_provider.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.AuthenticationError(
                message="bad key", response=MagicMock(), body={}
            )
        )

        from src.ai.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        with pytest.raises(ProviderAuthError):
            await provider.complete("sys", [{"role": "user", "content": "hi"}], "gpt-4o-mini")


@pytest.mark.asyncio
async def test_complete_maps_429_to_rate_limit_error():
    import openai

    with patch("src.ai.providers.openai_provider.AsyncOpenAI") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.RateLimitError(
                message="rate limit", response=MagicMock(), body={}
            )
        )

        from src.ai.providers.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        with pytest.raises(ProviderRateLimitError):
            await provider.complete("sys", [{"role": "user", "content": "hi"}], "gpt-4o-mini")

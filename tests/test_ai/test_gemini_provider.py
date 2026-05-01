from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import NormalisedResponse


def _mock_gemini_response():
    part = MagicMock()
    part.text = "Gemini reply"
    candidate = MagicMock()
    candidate.content.parts = [part]
    candidate.finish_reason = MagicMock(__str__=lambda s: "stop")
    usage = MagicMock()
    usage.prompt_token_count = 8
    usage.candidates_token_count = 4
    r = MagicMock()
    r.candidates = [candidate]
    r.usage_metadata = usage
    r.model = "gemini-2.0-flash"
    return r


@pytest.mark.asyncio
async def test_complete_returns_normalised():
    with patch("src.ai.providers.gemini_provider.genai") as mock_genai:
        mock_model_instance = AsyncMock()
        mock_model_instance.generate_content_async = AsyncMock(
            return_value=_mock_gemini_response()
        )
        mock_genai.GenerativeModel.return_value = mock_model_instance
        mock_genai.GenerationConfig = MagicMock()

        from src.ai.providers.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        result = await provider.complete(
            "sys", [{"role": "user", "content": "hi"}], "gemini-2.0-flash"
        )

    assert isinstance(result, NormalisedResponse)
    assert result.text == "Gemini reply"
    assert result.provider == "gemini"


@pytest.mark.asyncio
async def test_list_models():
    with patch("src.ai.providers.gemini_provider.genai"):
        from src.ai.providers.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        models = await provider.list_models()
    assert "gemini-2.0-flash" in models

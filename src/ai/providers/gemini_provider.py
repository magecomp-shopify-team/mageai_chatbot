import logging
from typing import AsyncIterator, Union

from google import genai
from google.api_core.exceptions import GoogleAPIError, PermissionDenied, ResourceExhausted
from google.genai import types

from config.settings import settings
from src.ai.base import AIProvider, NormalisedResponse
from src.ai.normaliser import normalise_gemini
from src.core.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


# Models that use internal thinking — budget is separate from response tokens
_THINKING_MODELS = {"gemini-2.5-pro", "gemini-2.5-flash"}
_THINKING_BUDGET = 1024  # tokens reserved for reasoning


def _build_contents(messages: list[dict]) -> list[types.Content]:
    role_map = {"user": "user", "assistant": "model"}
    return [
        types.Content(
            role=role_map.get(m["role"], "user"),
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]


class GeminiProvider(AIProvider):
    provider_id = "gemini"
    display_name = "Google Gemini"

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Union[NormalisedResponse, AsyncIterator[str]]:
        is_thinking = any(model.startswith(m) for m in _THINKING_MODELS)
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            # For thinking models, max_output_tokens is the total cap (thinking + response).
            # Add the thinking budget so response tokens are never crowded out.
            max_output_tokens=max_tokens + _THINKING_BUDGET if is_thinking else max_tokens,
            temperature=temperature,
            thinking_config=types.ThinkingConfig(thinking_budget=_THINKING_BUDGET) if is_thinking else None,
        )
        contents = _build_contents(messages)
        try:
            if stream:
                return self._stream(model, contents, config)
            response = await self._client.aio.models.generate_content(
                model=model, contents=contents, config=config
            )
            return normalise_gemini(response)
        except PermissionDenied as e:
            raise ProviderAuthError(str(e)) from e
        except ResourceExhausted as e:
            raise ProviderRateLimitError(str(e)) from e
        except GoogleAPIError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def _stream(self, model: str, contents, config) -> AsyncIterator[str]:
        try:
            async for chunk in await self._client.aio.models.generate_content_stream(
                model=model, contents=contents, config=config
            ):
                if chunk.text:
                    yield chunk.text
        except PermissionDenied as e:
            raise ProviderAuthError(str(e)) from e
        except ResourceExhausted as e:
            raise ProviderRateLimitError(str(e)) from e
        except GoogleAPIError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def list_models(self) -> list[str]:
        return [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]

    async def health_check(self) -> bool:
        try:
            # Single metadata fetch — no tokens consumed, validates API key.
            await self._client.aio.models.get(model="gemini-2.0-flash-lite")
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

import logging
from typing import AsyncIterator, Union

import anthropic

from config.settings import settings
from src.ai.base import AIProvider, NormalisedResponse
from src.ai.normaliser import normalise_anthropic
from src.core.exceptions import (
    ModelNotFoundError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    provider_id = "anthropic"
    display_name = "Anthropic Claude"

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Union[NormalisedResponse, AsyncIterator[str]]:
        kwargs = dict(model=model, max_tokens=max_tokens, system=system_prompt, messages=messages)
        try:
            if stream:
                return self._stream(**kwargs)
            r = await self._client.messages.create(**kwargs)
            return normalise_anthropic(r)
        except anthropic.AuthenticationError as e:
            raise ProviderAuthError(str(e)) from e
        except anthropic.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except anthropic.APITimeoutError as e:
            raise ProviderTimeoutError(str(e)) from e
        except anthropic.NotFoundError as e:
            raise ModelNotFoundError(str(e)) from e
        except anthropic.APIError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def _stream(self, **kwargs) -> AsyncIterator[str]:
        try:
            async with self._client.messages.stream(**kwargs) as s:
                async for chunk in s.text_stream:
                    yield chunk
        except anthropic.AuthenticationError as e:
            raise ProviderAuthError(str(e)) from e
        except anthropic.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except anthropic.APITimeoutError as e:
            raise ProviderTimeoutError(str(e)) from e
        except anthropic.APIError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def list_models(self) -> list[str]:
        return [
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-5",
            "claude-opus-4-5",
            "claude-sonnet-4-6",
            "claude-opus-4-6",
        ]

    async def health_check(self) -> bool:
        try:
            await self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=5,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

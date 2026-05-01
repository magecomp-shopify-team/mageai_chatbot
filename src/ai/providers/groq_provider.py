import logging
from typing import AsyncIterator, Union

import groq as groq_sdk
from groq import AsyncGroq

from config.settings import settings
from src.ai.base import AIProvider, NormalisedResponse
from src.ai.normaliser import normalise_openai
from src.core.exceptions import (
    ModelNotFoundError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    provider_id = "groq"
    display_name = "Groq"

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Union[NormalisedResponse, AsyncIterator[str]]:
        msgs = [{"role": "system", "content": system_prompt}] + messages
        try:
            if stream:
                return self._stream(msgs, model, max_tokens, temperature)
            r = await self._client.chat.completions.create(
                model=model, messages=msgs, max_tokens=max_tokens, temperature=temperature
            )
            result = normalise_openai(r)
            return result.model_copy(update={"provider": "groq"})
        except groq_sdk.AuthenticationError as e:
            raise ProviderAuthError(str(e)) from e
        except groq_sdk.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except groq_sdk.APITimeoutError as e:
            raise ProviderTimeoutError(str(e)) from e
        except groq_sdk.NotFoundError as e:
            raise ModelNotFoundError(str(e)) from e
        except groq_sdk.APIError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def _stream(
        self, msgs: list[dict], model: str, max_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        try:
            async with await self._client.chat.completions.create(
                model=model, messages=msgs, max_tokens=max_tokens,
                temperature=temperature, stream=True
            ) as resp:
                async for chunk in resp:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except groq_sdk.APIError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def list_models(self) -> list[str]:
        try:
            models = await self._client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
            ]

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))

import logging
from typing import AsyncIterator, Union

import openai
from openai import AsyncOpenAI

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


class OpenAICompatProvider(AIProvider):
    """Generic OpenAI-compatible provider (Together AI, Perplexity, Fireworks, Azure, vLLM …)."""

    provider_id = "openai_compat"
    display_name = "OpenAI Compatible"

    def __init__(
        self, base_url: str, api_key: str, provider_label: str = "openai_compat"
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.provider_id = provider_label

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
            return result.model_copy(update={"provider": self.provider_id})
        except openai.AuthenticationError as e:
            raise ProviderAuthError(str(e)) from e
        except openai.RateLimitError as e:
            raise ProviderRateLimitError(str(e)) from e
        except openai.APITimeoutError as e:
            raise ProviderTimeoutError(str(e)) from e
        except openai.NotFoundError as e:
            raise ModelNotFoundError(str(e)) from e
        except openai.APIError as e:
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
        except openai.APIError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def list_models(self) -> list[str]:
        try:
            models = await self._client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return []

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

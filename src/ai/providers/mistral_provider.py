import logging
from typing import AsyncIterator, Union

from mistralai.client import Mistral
from mistralai.client.errors import SDKError

from config.settings import settings
from src.ai.base import AIProvider, NormalisedResponse
from src.ai.normaliser import normalise_mistral
from src.core.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class MistralProvider(AIProvider):
    provider_id = "mistral"
    display_name = "Mistral AI"

    def __init__(self) -> None:
        self._client = Mistral(api_key=settings.MISTRAL_API_KEY)

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
            r = await self._client.chat.complete_async(
                model=model, messages=msgs, max_tokens=max_tokens, temperature=temperature
            )
            return normalise_mistral(r)
        except SDKError as e:
            if e.status_code == 401:
                raise ProviderAuthError(str(e)) from e
            if e.status_code == 429:
                raise ProviderRateLimitError(str(e)) from e
            raise ProviderUnavailableError(str(e)) from e
        except Exception as e:
            raise ProviderUnavailableError(str(e)) from e

    async def _stream(
        self, msgs: list[dict], model: str, max_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        try:
            async for event in await self._client.chat.stream_async(
                model=model, messages=msgs, max_tokens=max_tokens, temperature=temperature
            ):
                if event.data.choices[0].delta.content:
                    yield event.data.choices[0].delta.content
        except SDKError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def list_models(self) -> list[str]:
        return [
            "mistral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
            "codestral-latest",
            "open-mixtral-8x7b",
        ]

    async def health_check(self) -> bool:
        try:
            await self._client.models.list_async()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))

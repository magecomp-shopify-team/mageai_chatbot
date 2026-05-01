import logging
from typing import AsyncIterator, Union

import cohere

from config.settings import settings
from src.ai.base import AIProvider, NormalisedResponse
from src.ai.normaliser import normalise_cohere
from src.core.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


def _messages_to_cohere_history(messages: list[dict]) -> list[dict]:
    role_map = {"user": "USER", "assistant": "CHATBOT"}
    return [{"role": role_map.get(m["role"], "USER"), "message": m["content"]} for m in messages]


class CohereProvider(AIProvider):
    provider_id = "cohere"
    display_name = "Cohere"

    def __init__(self) -> None:
        self._client = cohere.AsyncClientV2(api_key=settings.COHERE_API_KEY)

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Union[NormalisedResponse, AsyncIterator[str]]:
        # Cohere v2: all messages including system in messages list
        all_msgs = [{"role": "system", "content": system_prompt}] + messages
        try:
            if stream:
                return self._stream(all_msgs, model, max_tokens, temperature)
            r = await self._client.chat(
                model=model,
                messages=all_msgs,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return normalise_cohere(r)
        except cohere.errors.UnauthorizedError as e:
            raise ProviderAuthError(str(e)) from e
        except cohere.errors.TooManyRequestsError as e:
            raise ProviderRateLimitError(str(e)) from e
        except Exception as e:
            raise ProviderUnavailableError(str(e)) from e

    async def _stream(
        self, msgs: list[dict], model: str, max_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        try:
            async for event in self._client.chat_stream(
                model=model, messages=msgs, max_tokens=max_tokens, temperature=temperature
            ):
                if hasattr(event, "type") and event.type == "content-delta":
                    delta = getattr(event.delta, "message", None)
                    if delta and hasattr(delta, "content"):
                        yield delta.content.text
        except Exception as e:
            raise ProviderUnavailableError(str(e)) from e

    async def list_models(self) -> list[str]:
        return ["command-r-plus", "command-r", "command-light", "command-nightly"]

    async def health_check(self) -> bool:
        try:
            await self._client.check_api_key()
            return True
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

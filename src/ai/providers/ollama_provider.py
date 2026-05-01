import json
import logging
from typing import AsyncIterator, Union

import httpx

from config.settings import settings
from src.ai.base import AIProvider, NormalisedResponse
from src.ai.normaliser import normalise_ollama
from src.core.exceptions import ProviderTimeoutError, ProviderUnavailableError

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    provider_id = "ollama"
    display_name = "Ollama (Local)"

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Union[NormalisedResponse, AsyncIterator[str]]:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "options": {"num_predict": max_tokens, "temperature": temperature},
            "stream": stream,
        }
        try:
            if stream:
                return self._stream(payload)
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    f"{self._base_url}/api/chat", json={**payload, "stream": False}
                )
                r.raise_for_status()
                return normalise_ollama(r.json())
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(str(e)) from e
        except httpx.HTTPError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def _stream(self, payload: dict) -> AsyncIterator[str]:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as r:
                    async for line in r.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if not data.get("done"):
                                yield data["message"]["content"]
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(str(e)) from e
        except httpx.HTTPError as e:
            raise ProviderUnavailableError(str(e)) from e

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

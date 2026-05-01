from abc import ABC, abstractmethod
from typing import AsyncIterator, Union

from pydantic import BaseModel


class NormalisedResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    finish_reason: str  # "stop" | "length" | "tool_calls" | "error"
    raw: dict           # full raw response for debugging


class AIProvider(ABC):
    provider_id: str    # e.g. "anthropic"
    display_name: str   # e.g. "Anthropic Claude"

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Union[NormalisedResponse, AsyncIterator[str]]: ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return available model IDs for this provider."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if provider is reachable and API key is valid."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Provider-specific token count, or tiktoken fallback."""
        ...

import logging

from pydantic import BaseModel

from config.settings import settings
from src.ai.base import AIProvider
from src.core.exceptions import ProviderNotFoundError

logger = logging.getLogger(__name__)


class ProviderInfo(BaseModel):
    provider_id: str
    display_name: str
    available: bool
    default_model: str
    models: list[str]


class ProviderRegistry:
    """Singleton registry. Providers are registered on startup."""

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}

    def register(self, provider: AIProvider) -> None:
        self._providers[provider.provider_id] = provider
        logger.info("Registered AI provider: %s", provider.provider_id)

    def get(self, provider_id: str) -> AIProvider:
        if provider_id not in self._providers:
            raise ProviderNotFoundError(f"Unknown provider: {provider_id}")
        return self._providers[provider_id]

    def is_available(self, provider_id: str) -> bool:
        return provider_id in self._providers

    def list_providers(self) -> list[ProviderInfo]:
        infos: list[ProviderInfo] = []
        for pid, p in self._providers.items():
            infos.append(
                ProviderInfo(
                    provider_id=pid,
                    display_name=p.display_name,
                    available=True,
                    default_model="",
                    models=[],
                )
            )
        return infos

    def get_all_ids(self) -> list[str]:
        return list(self._providers.keys())


registry = ProviderRegistry()


def init_registry() -> None:
    """Register all providers whose API key is non-empty. Called once on startup."""
    from src.ai.providers.anthropic_provider import AnthropicProvider
    from src.ai.providers.cohere_provider import CohereProvider
    from src.ai.providers.deepseek_provider import DeepSeekProvider
    from src.ai.providers.gemini_provider import GeminiProvider
    from src.ai.providers.groq_provider import GroqProvider
    from src.ai.providers.mistral_provider import MistralProvider
    from src.ai.providers.ollama_provider import OllamaProvider
    from src.ai.providers.openai_compat_provider import OpenAICompatProvider
    from src.ai.providers.openai_provider import OpenAIProvider

    if settings.ANTHROPIC_API_KEY:
        registry.register(AnthropicProvider())
    if settings.OPENAI_API_KEY:
        registry.register(OpenAIProvider())
    if settings.GEMINI_API_KEY:
        registry.register(GeminiProvider())
    if settings.DEEPSEEK_API_KEY:
        registry.register(DeepSeekProvider())
    if settings.MISTRAL_API_KEY:
        registry.register(MistralProvider())
    if settings.COHERE_API_KEY:
        registry.register(CohereProvider())
    if settings.GROQ_API_KEY:
        registry.register(GroqProvider())

    # Ollama is always registered — health_check determines actual availability
    registry.register(OllamaProvider())

    # OpenAI-compat extras
    if settings.TOGETHER_API_KEY:
        registry.register(
            OpenAICompatProvider(
                base_url="https://api.together.xyz/v1",
                api_key=settings.TOGETHER_API_KEY,
                provider_label="together",
            )
        )
    if settings.PERPLEXITY_API_KEY:
        registry.register(
            OpenAICompatProvider(
                base_url="https://api.perplexity.ai",
                api_key=settings.PERPLEXITY_API_KEY,
                provider_label="perplexity",
            )
        )

    logger.info("Provider registry initialised. Available: %s", registry.get_all_ids())

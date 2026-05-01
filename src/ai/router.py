import logging
import time
from typing import AsyncIterator, Union

from config.settings import settings
from src.ai.base import AIProvider, NormalisedResponse
from src.ai.registry import registry
from src.core.config import load_app_config
from src.core.exceptions import ProviderUnavailableError

logger = logging.getLogger(__name__)


async def resolve_provider(
    app_id: str, override_provider: str | None = None
) -> AIProvider:
    """
    Resolution order:
    1. override_provider (admin testing only)
    2. app config provider field
    3. settings.DEFAULT_PROVIDER
    4. First available provider (fallback)
    """
    candidates: list[tuple[str, str]] = []

    if override_provider:
        candidates.append((override_provider, "override"))

    try:
        cfg = load_app_config(app_id)
        if cfg.provider:
            candidates.append((cfg.provider, "app_config"))
    except Exception:
        pass

    candidates.append((settings.DEFAULT_PROVIDER, "default"))

    for provider_id, source in candidates:
        if registry.is_available(provider_id):
            logger.debug("Resolved provider '%s' via %s for app '%s'", provider_id, source, app_id)
            return registry.get(provider_id)

    # last resort: first registered
    all_ids = registry.get_all_ids()
    if all_ids:
        logger.warning("Falling back to first available provider: %s", all_ids[0])
        return registry.get(all_ids[0])

    raise ProviderUnavailableError("No AI provider available. Check API keys and provider config.")


async def complete(
    context: "AssembledContext",
    app_id: str,
    override_provider: str | None = None,
    stream: bool = False,
) -> Union[NormalisedResponse, AsyncIterator[str]]:
    """Single entry point for all AI completions."""
    provider = await resolve_provider(app_id, override_provider)

    try:
        cfg = load_app_config(app_id)
        model = cfg.model
        max_tokens = cfg.max_response_tokens
        temperature = cfg.temperature
    except Exception:
        model = settings.DEFAULT_MODEL
        max_tokens = 512
        temperature = 0.7

    start = time.perf_counter()
    result = await provider.complete(
        system_prompt=context.system_prompt,
        messages=context.messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=stream,
    )
    latency = time.perf_counter() - start

    if not stream:
        logger.info(
            "AI completion: provider=%s model=%s input_tokens=%s output_tokens=%s latency=%.2fs",
            result.provider, result.model, result.input_tokens, result.output_tokens, latency,
        )
    return result


# Avoid circular import — AssembledContext imported at type-check time only
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.pipeline.assembler import AssembledContext

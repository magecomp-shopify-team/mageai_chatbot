import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.registry import registry
from src.api.deps import get_current_admin, get_db
from src.api.schemas.providers import (
    EnableProviderRequest,
    ProviderHealthResult,
    ProviderInfo,
    ProviderTestRequest,
    ProviderTestResult,
)
from src.auth.audit import log_action
from src.auth.models import AdminUser

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Public ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ProviderInfo])
async def list_providers() -> list[ProviderInfo]:
    result = []
    for pid in registry.get_all_ids():
        p = registry.get(pid)
        models = await p.list_models()
        result.append(ProviderInfo(
            provider_id=pid,
            display_name=p.display_name,
            available=True,
            default_model=models[0] if models else "",
            models=models,
        ))
    return result


@router.get("/{provider_id}/models", response_model=list[str])
async def list_provider_models(provider_id: str) -> list[str]:
    provider = registry.get(provider_id)
    return await provider.list_models()


# ── Admin ─────────────────────────────────────────────────────────────────────

@router.get("/{provider_id}/health", response_model=ProviderHealthResult)
async def provider_health(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ProviderHealthResult:
    provider = registry.get(provider_id)
    start = time.perf_counter()
    healthy = await provider.health_check()
    latency_ms = (time.perf_counter() - start) * 1000
    return ProviderHealthResult(provider=provider_id, healthy=healthy, latency_ms=latency_ms)


@router.post("/{provider_id}/test", response_model=ProviderTestResult)
async def test_provider(
    provider_id: str,
    body: ProviderTestRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ProviderTestResult:
    provider = registry.get(provider_id)
    models = await provider.list_models()
    model = body.model or (models[0] if models else "")

    start = time.perf_counter()
    result = await provider.complete(
        system_prompt="You are a helpful assistant.",
        messages=[{"role": "user", "content": body.message}],
        model=model,
        max_tokens=100,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    await log_action(db, admin.username, "provider.test", target=provider_id)
    return ProviderTestResult(
        provider=provider_id,
        model=result.model,
        reply=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=latency_ms,
    )


@router.post("/{provider_id}/enable")
async def enable_provider(
    provider_id: str,
    body: EnableProviderRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    # Update the enabled flag in provider YAML
    import yaml
    from pathlib import Path
    yaml_path = Path(f"config/providers/{provider_id}.yaml")
    if yaml_path.exists():
        with yaml_path.open() as f:
            data = yaml.safe_load(f)
        data["enabled"] = body.enabled
        with yaml_path.open("w") as f:
            yaml.dump(data, f)
    await log_action(
        db, admin.username, "provider.enable", target=provider_id,
        detail={"enabled": body.enabled}
    )
    return {"provider": provider_id, "enabled": body.enabled}


@router.put("/{provider_id}/default")
async def set_default_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    # Persist to .env
    from pathlib import Path
    env_path = Path(".env")
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("DEFAULT_PROVIDER="):
            new_lines.append(f"DEFAULT_PROVIDER={provider_id}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"DEFAULT_PROVIDER={provider_id}")
    env_path.write_text("\n".join(new_lines) + "\n")

    await log_action(db, admin.username, "provider.set_default", target=provider_id)
    return {"default_provider": provider_id}

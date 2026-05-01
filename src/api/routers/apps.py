import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_admin, get_db
from src.api.schemas.apps import AppDetail, AppInfo, CreateAppRequest, UpdateAppRequest, UpdateProviderRequest
from src.auth.audit import log_action
from src.auth.models import AdminUser
from src.core.config import list_app_ids, load_app_config, reload_app_config

logger = logging.getLogger(__name__)
router = APIRouter()

_APPS_DIR = Path("config/apps")


@router.get("/", response_model=list[AppInfo])
async def list_apps() -> list[AppInfo]:
    apps = []
    for app_id in list_app_ids():
        try:
            cfg = load_app_config(app_id)
            apps.append(AppInfo(
                app_id=app_id,
                name=cfg.name,
                provider=cfg.provider,
                model=cfg.model,
            ))
        except Exception:
            pass
    return apps


@router.post("/", response_model=AppInfo)
async def create_app(
    body: CreateAppRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> AppInfo:
    path = _APPS_DIR / f"{body.app_id}.yaml"
    if path.exists():
        raise HTTPException(status_code=409, detail="App already exists")
    _APPS_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(body.model_dump(exclude={"app_id"}), f, default_flow_style=False)
    await log_action(db, admin.username, "app.create", target=body.app_id)
    return AppInfo(app_id=body.app_id, name=body.name, provider=body.provider, model=body.model)


@router.get("/{app_id}", response_model=AppDetail)
async def get_app(app_id: str) -> AppDetail:
    cfg = load_app_config(app_id)
    return AppDetail(
        app_id=app_id,
        name=cfg.name,
        role=cfg.role,
        tone=cfg.tone,
        rules=cfg.rules,
        provider=cfg.provider,
        model=cfg.model,
        max_history_turns=cfg.max_history_turns,
        max_chunk_tokens=cfg.max_chunk_tokens,
        top_k_chunks=cfg.top_k_chunks,
        min_relevance=cfg.min_relevance,
        max_response_tokens=cfg.max_response_tokens,
        temperature=cfg.temperature,
    )


@router.put("/{app_id}", response_model=AppDetail)
async def update_app(
    app_id: str,
    body: UpdateAppRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> AppDetail:
    path = _APPS_DIR / f"{app_id}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="App not found")
    with path.open("w") as f:
        yaml.dump(body.model_dump(), f, default_flow_style=False)
    cfg = reload_app_config(app_id)
    await log_action(db, admin.username, "app.update", target=app_id)
    return AppDetail(
        app_id=app_id,
        name=cfg.name,
        role=cfg.role,
        tone=cfg.tone,
        rules=cfg.rules,
        provider=cfg.provider,
        model=cfg.model,
        max_history_turns=cfg.max_history_turns,
        max_chunk_tokens=cfg.max_chunk_tokens,
        top_k_chunks=cfg.top_k_chunks,
        min_relevance=cfg.min_relevance,
        max_response_tokens=cfg.max_response_tokens,
        temperature=cfg.temperature,
    )


@router.patch("/{app_id}/provider", response_model=AppInfo)
async def update_app_provider(
    app_id: str,
    body: UpdateProviderRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> AppInfo:
    path = _APPS_DIR / f"{app_id}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="App not found")
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    data["provider"] = body.provider
    data["model"] = body.model
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)
    cfg = reload_app_config(app_id)
    await log_action(
        db, admin.username, "app.update_provider",
        target=app_id,
        detail={"provider": body.provider, "model": body.model},
    )
    return AppInfo(app_id=app_id, name=cfg.name, provider=cfg.provider, model=cfg.model)


@router.post("/{app_id}/reload")
async def reload_app(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    cfg = reload_app_config(app_id)
    await log_action(db, admin.username, "app.reload", target=app_id)
    return {"app_id": app_id, "name": cfg.name}


@router.delete("/{app_id}")
async def delete_app(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    from src.manager.doc_manager import delete_app_data
    path = _APPS_DIR / f"{app_id}.yaml"
    if path.exists():
        path.unlink()
    await delete_app_data(app_id)
    await log_action(db, admin.username, "app.delete", target=app_id)
    return {"deleted": True}

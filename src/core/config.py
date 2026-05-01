from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

_CONFIG_DIR = Path("config/apps")
_cache: dict[str, "AppConfig"] = {}


class AppConfig(BaseModel):
    name: str
    role: str
    tone: str
    rules: list[str]
    provider: str
    model: str
    max_history_turns: int = 6
    max_chunk_tokens: int = 800
    top_k_chunks: int = 4
    min_relevance: float = 0.3
    max_response_tokens: int = 512
    temperature: float = 0.7


def _load_yaml(app_id: str) -> AppConfig:
    path = _CONFIG_DIR / f"{app_id}.yaml"
    if not path.exists():
        from src.core.exceptions import AppNotFoundError
        raise AppNotFoundError(f"No config found for app '{app_id}'")
    with path.open() as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)


def load_app_config(app_id: str) -> AppConfig:
    if app_id not in _cache:
        _cache[app_id] = _load_yaml(app_id)
    return _cache[app_id]


def reload_app_config(app_id: str) -> AppConfig:
    _cache.pop(app_id, None)
    _cache[app_id] = _load_yaml(app_id)
    return _cache[app_id]


def list_app_ids() -> list[str]:
    return [p.stem for p in _CONFIG_DIR.glob("*.yaml") if not p.stem.startswith("_")]

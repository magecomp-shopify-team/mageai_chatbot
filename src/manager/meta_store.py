import asyncio
import json
import logging
from pathlib import Path

import aiofiles

from config.settings import settings

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()


class MetaStore:
    """Thread-safe async JSON meta store for document tracking."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or settings.META_DB_PATH

    async def _read(self) -> dict:
        if not self._path.exists():
            return {}
        async with aiofiles.open(self._path, "r") as f:
            content = await f.read()
        return json.loads(content) if content.strip() else {}

    async def _write(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self._path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def get_doc(self, app_id: str, filename: str) -> dict | None:
        async with _lock:
            data = await self._read()
            return data.get(app_id, {}).get(filename)

    async def upsert_doc(self, app_id: str, filename: str, meta: dict) -> None:
        async with _lock:
            data = await self._read()
            data.setdefault(app_id, {})[filename] = meta
            await self._write(data)

    async def remove_doc(self, app_id: str, filename: str) -> None:
        async with _lock:
            data = await self._read()
            data.get(app_id, {}).pop(filename, None)
            await self._write(data)

    async def list_docs(self, app_id: str) -> dict:
        async with _lock:
            data = await self._read()
            return data.get(app_id, {})

    async def remove_app(self, app_id: str) -> None:
        async with _lock:
            data = await self._read()
            data.pop(app_id, None)
            await self._write(data)

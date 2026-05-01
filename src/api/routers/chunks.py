import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_admin, get_db
from src.auth.audit import log_action
from src.auth.models import AdminUser
from src.core.chroma import get_or_create_collection

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{app_id}")
async def list_chunks(app_id: str, limit: int = 20) -> dict:
    collection = await asyncio.to_thread(get_or_create_collection, app_id)
    results = await asyncio.to_thread(
        lambda: collection.get(limit=limit, include=["documents", "metadatas"])
    )
    chunks = [
        {"id": id_, "text": doc, "meta": meta}
        for id_, doc, meta in zip(
            results.get("ids", []),
            results.get("documents", []),
            results.get("metadatas", []),
        )
    ]
    return {"app_id": app_id, "chunks": chunks}


@router.delete("")
async def delete_chunks(
    chunk_ids: list[str],
    app_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    from src.manager.doc_manager import remove_chunks
    await remove_chunks(chunk_ids, app_id)
    await log_action(db, admin.username, "chunks.delete", target=app_id, detail={"ids": chunk_ids})
    return {"deleted": len(chunk_ids)}

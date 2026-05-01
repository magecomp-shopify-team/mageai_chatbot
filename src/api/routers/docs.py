import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_admin, get_db
from src.api.schemas.docs import IndexResultSchema
from src.auth.audit import log_action
from src.auth.models import AdminUser
from src.manager.doc_manager import remove_document, wipe_and_reindex_app
from src.manager.meta_store import MetaStore
from src.pipeline.indexer import index_file

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=IndexResultSchema)
async def upload_document(
    app_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> IndexResultSchema:
    if not file.filename or not file.filename.endswith((".md", ".txt", ".pdf")):
        raise HTTPException(status_code=422, detail="Only .md, .txt, and .pdf files are supported")

    content = await file.read()
    with tempfile.NamedTemporaryFile(
        suffix=Path(file.filename).suffix, delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        result = await index_file(tmp_path, app_id)
    finally:
        tmp_path.unlink(missing_ok=True)

    await log_action(db, admin.username, "doc.upload", target=f"{app_id}/{file.filename}")
    return IndexResultSchema(**result.model_dump())


@router.get("/{app_id}")
async def list_documents(app_id: str) -> dict:
    meta = MetaStore()
    docs = await meta.list_docs(app_id)
    return {"app_id": app_id, "documents": docs}


@router.delete("/{app_id}/{filename}")
async def delete_document(
    app_id: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    await remove_document(app_id, filename)
    await log_action(db, admin.username, "doc.delete", target=f"{app_id}/{filename}")
    return {"deleted": True}


@router.delete("/{app_id}")
async def delete_all_documents(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    from src.manager.doc_manager import delete_app_data
    await delete_app_data(app_id)
    await log_action(db, admin.username, "doc.delete_all", target=app_id)
    return {"deleted": True}


@router.post("/{app_id}/reembed")
async def reembed_app(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    total = await wipe_and_reindex_app(app_id)
    await log_action(db, admin.username, "doc.reembed", target=app_id)
    return {"app_id": app_id, "chunks_indexed": total}

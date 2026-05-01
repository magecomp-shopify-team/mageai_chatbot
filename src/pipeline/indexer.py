import asyncio
import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path

import aiofiles
from pydantic import BaseModel

from config.settings import settings
from src.core.chroma import get_or_create_collection
from src.core.embedder import encode
from src.pipeline.chunker import chunk_text

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (".md", ".txt", ".pdf")


def _extract_pdf_text(file_path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    return "\n\n".join(pages)


class IndexResult(BaseModel):
    app_id: str
    filename: str
    chunks_indexed: int
    file_hash: str
    skipped: bool = False


async def index_file(
    file_path: Path,
    app_id: str,
    chunk_size: int = 450,
    force: bool = False,
) -> IndexResult:
    from src.manager.meta_store import MetaStore

    if file_path.suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}. "
            f"Allowed: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    if file_path.suffix == ".pdf":
        content = await asyncio.to_thread(_extract_pdf_text, file_path)
    else:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()

    file_hash = hashlib.md5(content.encode()).hexdigest()
    filename = file_path.name
    meta = MetaStore()

    existing = await meta.get_doc(app_id, filename)
    if existing and existing.get("hash") == file_hash and not force:
        logger.info("Skipping unchanged file: %s/%s", app_id, filename)
        return IndexResult(
            app_id=app_id, filename=filename,
            chunks_indexed=existing.get("chunk_count", 0),
            file_hash=file_hash, skipped=True,
        )

    chunks = chunk_text(content, chunk_size=chunk_size)
    if not chunks:
        logger.warning("No chunks produced for %s/%s", app_id, filename)
        return IndexResult(app_id=app_id, filename=filename, chunks_indexed=0, file_hash=file_hash)

    embeddings = await asyncio.to_thread(encode, chunks)

    collection = await asyncio.to_thread(get_or_create_collection, app_id)

    # Remove existing chunks for this file
    await asyncio.to_thread(
        lambda: collection.delete(where={"source_file": filename})
    )

    now = datetime.utcnow().isoformat()
    ids = [f"{app_id}_{filename}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source_file": filename,
            "app_id": app_id,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "indexed_at": now,
        }
        for i in range(len(chunks))
    ]

    await asyncio.to_thread(
        lambda: collection.upsert(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
    )

    # Copy raw file to storage
    dest_dir = settings.STORAGE_ROOT / app_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    await asyncio.to_thread(shutil.copy2, str(file_path), str(dest))

    await meta.upsert_doc(app_id, filename, {
        "hash": file_hash,
        "chunk_count": len(chunks),
        "indexed_at": now,
        "file_path": str(dest),
    })

    logger.info("Indexed %d chunks for %s/%s", len(chunks), app_id, filename)
    return IndexResult(
        app_id=app_id, filename=filename, chunks_indexed=len(chunks), file_hash=file_hash
    )

import asyncio
import logging
import shutil
from pathlib import Path

from config.settings import settings
from src.core.chroma import delete_collection, get_or_create_collection
from src.manager.meta_store import MetaStore

logger = logging.getLogger(__name__)


async def remove_document(app_id: str, filename: str) -> None:
    logger.warning("Removing document: %s/%s", app_id, filename)
    meta = MetaStore()

    collection = await asyncio.to_thread(get_or_create_collection, app_id)
    await asyncio.to_thread(
        lambda: collection.delete(where={"source_file": filename})
    )

    stored_path = settings.STORAGE_ROOT / app_id / filename
    if stored_path.exists():
        stored_path.unlink()

    await meta.remove_doc(app_id, filename)


async def remove_chunks(chunk_ids: list[str], app_id: str) -> None:
    collection = await asyncio.to_thread(get_or_create_collection, app_id)
    await asyncio.to_thread(lambda: collection.delete(ids=chunk_ids))


async def wipe_and_reindex_app(app_id: str) -> int:
    logger.warning("Wiping and reindexing app: %s", app_id)
    from src.pipeline.indexer import index_file

    await asyncio.to_thread(delete_collection, app_id)
    meta = MetaStore()

    files_dir = settings.STORAGE_ROOT / app_id
    total_chunks = 0
    if files_dir.exists():
        for f in files_dir.iterdir():
            if f.suffix in (".md", ".txt"):
                result = await index_file(f, app_id, force=True)
                total_chunks += result.chunks_indexed
    return total_chunks


async def delete_app_data(app_id: str) -> None:
    logger.warning("Deleting all data for app: %s", app_id)
    await asyncio.to_thread(delete_collection, app_id)

    files_dir = settings.STORAGE_ROOT / app_id
    if files_dir.exists():
        await asyncio.to_thread(shutil.rmtree, str(files_dir))

    meta = MetaStore()
    await meta.remove_app(app_id)

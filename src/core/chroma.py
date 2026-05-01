from functools import lru_cache

import chromadb
from chromadb import Collection

from config.settings import settings


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(settings.CHROMA_PATH))


def get_or_create_collection(app_id: str) -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(name=f"{app_id}_app")


def collection_exists(app_id: str) -> bool:
    client = get_chroma_client()
    existing = [c.name for c in client.list_collections()]
    return f"{app_id}_app" in existing


def delete_collection(app_id: str) -> None:
    client = get_chroma_client()
    try:
        client.delete_collection(name=f"{app_id}_app")
    except Exception:
        pass

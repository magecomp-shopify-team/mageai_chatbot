import asyncio
import logging
from dataclasses import dataclass

from src.core.chroma import collection_exists, get_or_create_collection
from src.core.embedder import encode

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    source_file: str
    chunk_index: int
    distance: float


async def retrieve(
    query: str,
    app_id: str,
    top_k: int = 4,
    min_relevance: float = 0.0,
) -> list[Chunk]:
    if not await asyncio.to_thread(collection_exists, app_id):
        return []

    query_embedding = (await asyncio.to_thread(encode, [query]))[0]
    collection = await asyncio.to_thread(get_or_create_collection, app_id)

    n_results = min(top_k + 2, max(1, top_k + 2))
    results = await asyncio.to_thread(
        lambda: collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
    )

    chunks: list[Chunk] = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, dists):
        # ChromaDB returns squared-L2 distance for unit vectors (range 0–4).
        # Convert to [0, 1] relevance: relevance = 1 - dist/2.
        relevance = max(0.0, 1.0 - dist / 2.0)
        if relevance >= min_relevance:
            chunks.append(
                Chunk(
                    text=doc,
                    source_file=meta.get("source_file", ""),
                    chunk_index=meta.get("chunk_index", 0),
                    distance=dist,
                )
            )

    return chunks[:top_k]

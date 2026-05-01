import logging
import time
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    start = time.perf_counter()
    model = SentenceTransformer(settings.EMBED_MODEL)
    elapsed = time.perf_counter() - start
    logger.info("Embedding model '%s' loaded in %.2fs", settings.EMBED_MODEL, elapsed)
    return model


def encode(texts: list[str]) -> list[list[float]]:
    """Batch-encode texts; always returns a list of float vectors."""
    model = get_embedder()
    batch_size = settings.EMBED_BATCH_SIZE
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
    return embeddings.tolist()

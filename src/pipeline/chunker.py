def chunk_text(text: str, chunk_size: int = 450, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-boundary chunks. Filters chunks < 20 words."""
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk = " ".join(chunk_words)
        if len(chunk_words) >= 20:
            chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)

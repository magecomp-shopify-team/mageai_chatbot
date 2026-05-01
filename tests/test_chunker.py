from src.pipeline.chunker import chunk_text, estimate_tokens


def test_chunk_text_basic():
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = chunk_text(text, chunk_size=30, overlap=5)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.split()) >= 20


def test_chunk_text_overlap():
    words = [f"word{i}" for i in range(60)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=30, overlap=5)
    # Last words of chunk 0 should appear at start of chunk 1
    last_words_chunk0 = chunks[0].split()[-5:]
    first_words_chunk1 = chunks[1].split()[:5]
    assert last_words_chunk0 == first_words_chunk1


def test_chunk_text_filters_short():
    short_text = "only ten words here today not quite twenty words total here"
    chunks = chunk_text(short_text, chunk_size=50, overlap=5)
    for chunk in chunks:
        assert len(chunk.split()) >= 20


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_estimate_tokens():
    text = " ".join(["word"] * 100)
    estimate = estimate_tokens(text)
    assert 120 <= estimate <= 140  # 100 * 1.3

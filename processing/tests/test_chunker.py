from processing.services.chunker import chunk_text


def test_chunk_text_basic():
    # Since the new chunk_size is 2000, this short text should return as a single chunk.
    text = "one two three four five six seven eight nine ten"
    chunks = chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_empty():
    assert chunk_text("") == []

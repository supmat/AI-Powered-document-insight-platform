from processing.services.chunker import chunk_text


def test_chunk_text_basic():
    # 10 words
    text = "one two three four five six seven eight nine ten"

    # max 4, overlap 2
    chunks = chunk_text(text, max_words=4, overlap=2)

    assert chunks[0] == "one two three four"
    assert chunks[1] == "three four five six"
    assert chunks[2] == "five six seven eight"
    assert chunks[3] == "seven eight nine ten"


def test_chunk_text_empty():
    assert chunk_text("") == []

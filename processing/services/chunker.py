def chunk_text(text: str, max_words: int = 400, overlap: int = 50) -> list[str]:
    """
    Naively chunks text by words with sliding overlap to maintain semantic context
    while strictly fitting within Gemini and Vector DB dimension limits.
    """
    words = text.split()
    chunks: list[str] = []

    if not words:
        return chunks

    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + max_words])
        chunks.append(chunk)
        i += max_words - overlap

    return chunks

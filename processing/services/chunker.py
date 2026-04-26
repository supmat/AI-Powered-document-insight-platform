from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(text: str) -> list[str]:
    """
    Smart chunking using LangChain's RecursiveCharacterTextSplitter.
    Splits text cleanly at natural boundaries.
    """
    if not text.strip():
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=250,
        separators=["\n\n", "\n", "(?<=\. )", " ", ""],
    )

    return text_splitter.split_text(text)

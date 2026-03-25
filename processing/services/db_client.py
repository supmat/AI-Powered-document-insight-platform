from processing.core.database import AsyncSessionLocal, DocumentChunk, engine, Base
from sqlalchemy import text


async def init_db():
    """Idempotently bootstrap the PostgreSQL pgvector extension and schemas."""
    async with engine.begin() as conn:
        # Strictly ensure the pgvector C-extension is enabled on the database!
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def store_document_chunks(
    document_id: str,
    tenant_id: str,
    filename: str,
    chunks: list[str],
    embeddings: list[list[float]],
    entities_list: list[list[dict]],
):
    """
    Atomically stores the exact text chunks, their 768-D AI embeddings,
    and extracted SpaCy NER entities directly into the local PostgreSQL pgvector table.
    """
    async with AsyncSessionLocal() as session:
        for i, (chunk, embedding, entities) in enumerate(
            zip(chunks, embeddings, entities_list)
        ):
            doc_chunk = DocumentChunk(
                document_id=document_id,
                tenant_id=tenant_id,
                filename=filename,
                chunk_index=i,
                text_content=chunk,
                entities=entities,
                embedding=embedding,
            )
            session.add(doc_chunk)

        await session.commit()

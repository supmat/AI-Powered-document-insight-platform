from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from query.models.query import QueryRequest, QueryResponse, SourceQuote
from query.services.gemini_client import (
    retrieve_relevant_chunks,
    generate_rag_answer,
    get_embeddings,
)
from shared.database import get_db
from gateway.api.deps import get_current_user
from gateway.models.user import User

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # 1. Embed the user's question
        embeddings_list = await get_embeddings([request.question])
        question_embedding = embeddings_list[0]

        # 2. Retrieve chunks using the explicitly passed filter - enforce current user
        filters = request.filter or {}
        filters["tenant_id"] = current_user.email

        chunk_results = await retrieve_relevant_chunks(
            db=db,
            question_embedding=question_embedding,
            filters=filters,
            top_k=request.top_k,
        )
        if chunk_results:
            top_distance = chunk_results[0][1]

            # Convert distance to similarity (confidence).
            # E.g., a distance of 0.15 becomes 0.85 confidence.
            confidence = max(0.0, 1.0 - top_distance)

            # Extract just the DocumentChunk objects for the LLM
            chunks = [row[0] for row in chunk_results]
        else:
            confidence = 0.0
            chunks = []

        # 3. Format Sources and Entities
        sources = []
        all_entities = set()

        for chunk in chunks:
            sources.append(
                SourceQuote(
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    text_snippet=chunk.text_content[:150] + "...",
                )
            )

            if chunk.entities:
                for ent_dict in chunk.entities:
                    entity_name = ent_dict.get("text") or str(ent_dict)
                    all_entities.add(entity_name)

        # 4. Get Answer from Gemini / local LLM
        answer = await generate_rag_answer(request.question, chunks)

        # 5. Return exact required payload
        return QueryResponse(
            answer=answer,
            confidence_score=round(confidence, 2),
            quoted_sources=sources,
            detected_entities=list(all_entities),
        )

    except Exception as e:
        print(f"[ERROR!] Query Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process query")

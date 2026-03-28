from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class QueryRequest(BaseModel):
    question: str = Field(..., description="The user's question to be answered via RAG")
    top_k: int = Field(default=5, description="Number of document chunks to retrieve")
    filter: Optional[Dict[str, str]] = Field(
        default=None, description="Optional filter, e.g. {'tenant_id': 'xyz'}"
    )


class SourceQuote(BaseModel):
    document_id: str
    filename: str
    text_snippet: str


class QueryResponse(BaseModel):
    answer: str
    confidence_score: float
    quoted_sources: List[SourceQuote]
    detected_entities: List[str]

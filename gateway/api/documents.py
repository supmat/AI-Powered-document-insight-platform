"""
Documents management API.

Provides endpoints for:
  GET  /api/v1/documents/   → list all documents ingested by the current user
  DELETE /api/v1/documents/{document_id} → delete all chunks for a document
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from pydantic import BaseModel
from typing import List

from gateway.api.deps import get_current_user
from shared.database import get_db
from shared.models import DocumentChunk
from gateway.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    tenant_id: str

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentSummary]


class DeleteResponse(BaseModel):
    message: str
    document_id: str
    chunks_deleted: int


# ---------------------------------------------------------------------------
# GET /  — list all documents for the authenticated user
# ---------------------------------------------------------------------------


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a deduplicated list of all documents ingested by the current user,
    with the number of vector chunks stored per document.
    """
    stmt = (
        select(
            DocumentChunk.document_id,
            DocumentChunk.filename,
            DocumentChunk.tenant_id,
            func.count(DocumentChunk.id).label("chunk_count"),
        )
        .where(DocumentChunk.tenant_id == current_user.email)
        .group_by(
            DocumentChunk.document_id,
            DocumentChunk.filename,
            DocumentChunk.tenant_id,
        )
        .order_by(DocumentChunk.filename)
    )

    result = await db.execute(stmt)
    rows = result.all()

    documents = [
        DocumentSummary(
            document_id=row.document_id,
            filename=row.filename,
            tenant_id=row.tenant_id,
            chunk_count=row.chunk_count,
        )
        for row in rows
    ]

    return DocumentListResponse(total=len(documents), documents=documents)


# ---------------------------------------------------------------------------
# DELETE /{document_id}  — remove all chunks for a document
# ---------------------------------------------------------------------------


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently deletes all vector chunks for the specified document.
    Only the tenant who owns the document may delete it.
    """
    # First verify ownership — prevent one user from deleting another's data
    ownership_check = await db.execute(
        select(DocumentChunk.id)
        .where(DocumentChunk.document_id == document_id)
        .where(DocumentChunk.tenant_id == current_user.email)
        .limit(1)
    )
    if ownership_check.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found or does not belong to you.",
        )

    # Count before deleting so we can report it
    count_result = await db.execute(
        select(func.count(DocumentChunk.id))
        .where(DocumentChunk.document_id == document_id)
        .where(DocumentChunk.tenant_id == current_user.email)
    )
    chunks_deleted = count_result.scalar_one()

    # Hard delete all chunks
    await db.execute(
        delete(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .where(DocumentChunk.tenant_id == current_user.email)
    )
    await db.commit()

    return DeleteResponse(
        message=f"Document '{document_id}' deleted successfully.",
        document_id=document_id,
        chunks_deleted=chunks_deleted,
    )

from sqlalchemy import Column, Integer, String, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from shared.database import Base


class DBUser(Base):
    """PostgreSQL user model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)


class DocumentChunk(Base):
    """PostgreSQL model for storing vectorized document chunks (pgvector)."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String, index=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    filename: Mapped[str] = mapped_column(String)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text_content: Mapped[str] = mapped_column(Text)
    entities: Mapped[dict] = mapped_column(JSON, default=list)

    # 768-dimensional AI embeddings
    embedding: Mapped[list] = mapped_column(Vector(768))

import asyncio
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from typing import Dict, Tuple


class DatabaseSettings(BaseSettings):
    """Configuration specific to the database, loaded from .env."""

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_DB: str = "document_insights"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    model_config = {"env_file": ".env", "extra": "ignore"}


db_settings = DatabaseSettings()


class Base(DeclarativeBase):
    """Shared base class for all database models across microservices."""

    pass


# Loop-aware registry to prevent 'attached to a different loop' errors
_engines: Dict[asyncio.AbstractEventLoop, AsyncEngine] = {}
_sessionmakers: Dict[asyncio.AbstractEventLoop, async_sessionmaker[AsyncSession]] = {}


def get_db_components() -> Tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Uses a loop-aware registry to ensure connections are strictly tied to the active loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Fallback if called outside an active loop (e.g. at import level in some contexts)
        raise RuntimeError(
            "get_db_components must be called within a running event loop."
        )

    if loop not in _engines:
        engine = create_async_engine(
            db_settings.SQLALCHEMY_DATABASE_URI,
            echo=False,
            pool_pre_ping=True,
            # Cycle connections every 5 minutes (down from 1 hour) to avoid stale pool errors
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
        )
        session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
        _engines[loop] = engine
        _sessionmakers[loop] = session_factory

    return _engines[loop], _sessionmakers[loop]


async def init_db():
    """Create all PostgreSQL tables/schemata during application startup sequence."""
    engine, _ = get_db_components()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI Dependency for database sessions."""
    _, AsyncSessionLocal = get_db_components()
    async with AsyncSessionLocal() as session:
        yield session


# Backwards compatibility handles:
engine = None
AsyncSessionLocal = None

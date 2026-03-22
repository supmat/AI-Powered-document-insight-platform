from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from gateway.core.config import settings

# Create async engine using asyncpg
engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, echo=False)

# Session factory for dependencies
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    """FastAPI Dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        yield session

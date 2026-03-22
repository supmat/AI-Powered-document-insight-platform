from fastapi import FastAPI
from contextlib import asynccontextmanager
from gateway.core.config import settings
from gateway.core.rate_limit import rate_limit_middleware
from gateway.api import auth, users, ingestion
from gateway.core.database import engine, Base
from starlette.middleware.base import BaseHTTPMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all PostgreSQL tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure MinIO bucket exists
    from gateway.services.minio_client import ensure_bucket_exists

    try:
        ensure_bucket_exists()
    except Exception as e:
        print(f"Failed to initialize MinIO bucket: {e}")

    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Register custom middleware
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)  # type: ignore

# Register Routers
app.include_router(
    auth.router, prefix=f"{settings.APP_V1_STR}/auth", tags=["authentication"]
)
app.include_router(users.router, prefix=f"{settings.APP_V1_STR}/users", tags=["users"])
app.include_router(
    ingestion.router, prefix=f"{settings.APP_V1_STR}/documents", tags=["documents"]
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "gateway"}

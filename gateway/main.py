from fastapi import FastAPI
from contextlib import asynccontextmanager
from gateway.core.config import settings
from gateway.core.rate_limit import rate_limit_middleware
from gateway.api import auth, users, ingestion, documents
from query.api import q_response
from shared.database import get_db_components, Base
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from prometheus_fastapi_instrumentator import Instrumentator


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all PostgreSQL tables on startup
    engine, _ = get_db_components()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure MinIO bucket exists
    from gateway.services.minio_client import ensure_bucket_exists

    try:
        ensure_bucket_exists()
    except Exception as e:
        print(f"Failed to initialize MinIO bucket: {e}")

    yield


# ------------------------------------------------------------------------------
# OpenTelemetry Tracing Setup
# ------------------------------------------------------------------------------
resource = Resource(attributes={"service.name": "gateway"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True)
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Instrument FastAPI with OTel and Prometheus
FastAPIInstrumentor.instrument_app(app)
Instrumentator().instrument(app).expose(app)

# Register custom middleware
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)  # type: ignore

# Register Routers
app.include_router(
    auth.router, prefix=f"{settings.APP_V1_STR}/auth", tags=["authentication"]
)
app.include_router(users.router, prefix=f"{settings.APP_V1_STR}/users", tags=["users"])
app.include_router(
    ingestion.router,
    prefix=f"{settings.APP_V1_STR}/upload_documents",
    tags=["documents"],
)
app.include_router(
    documents.router, prefix=f"{settings.APP_V1_STR}/documents", tags=["documents"]
)

app.include_router(
    q_response.router, prefix=f"{settings.APP_V1_STR}/query", tags=["query"]
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "gateway"}

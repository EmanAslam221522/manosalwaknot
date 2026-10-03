from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from starlette.middleware.base import RequestResponseEndpoint

from app.api import admin, auth, deliveries, food, mano, matching, notifications, profile, reservations, safety, trust
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import ApiError, api_error_handler
from app.core.rate_limit import check_redis

settings = get_settings()


def validate_embedding_configuration():
    """Validate that embedding configuration matches database schema."""
    try:
        with engine.connect() as connection:
            # Check if pgvector is available
            vector_available = connection.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            if not vector_available:
                raise ApiError(
                    500,
                    "PGVECTOR_UNAVAILABLE",
                    "pgvector extension is not available. RAG features require pgvector.",
                )

            # Check if knowledge_chunks table exists
            table_exists = connection.scalar(
                text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'knowledge_chunks')")
            )
            if table_exists:
                # Check vector column dimension
                # This is a simplified check - in production you might want to inspect the actual column type
                # For now, we trust the migration set VECTOR(1536) and validate config matches
                if settings.embedding_dimension != 1536:
                    raise ApiError(
                        500,
                        "EMBEDDING_CONFIG_MISMATCH",
                        f"EMBEDDING_DIMENSION is set to {settings.embedding_dimension}, but database expects 1536. "
                        "Update configuration or run migration to change vector dimension.",
                    )
    except ApiError:
        raise
    except Exception as exc:
        # Don't fail startup for validation errors in non-production
        if settings.environment == "production":
            raise ApiError(500, "CONFIG_VALIDATION_FAILED", "Failed to validate embedding configuration.") from exc


# Validate embedding configuration on startup
try:
    validate_embedding_configuration()
except ApiError:
    if settings.environment == "production":
        raise

app = FastAPI(
    title="ManOSalwaKnot API",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    openapi_url="/openapi.json" if settings.environment != "production" else None,
)

if settings.environment == "staging":
    # Staging is a public demo API. It uses bearer tokens rather than cookies,
    # so wildcard CORS safely supports Bilt previews and the published PWA.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Client-Request-Id", "X-Idempotency-Key"],
        expose_headers=["X-Request-Id"],
    )
elif settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Client-Request-Id", "X-Idempotency-Key"],
        expose_headers=["X-Request-Id"],
    )


@app.middleware("http")
async def request_context(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    request_id = request.headers.get("x-client-request-id") or str(uuid4())
    request.state.request_id = request_id[:128]
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    return api_error_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    fields = [
        {
            "field": ".".join(str(value) for value in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return api_error_handler(
        request,
        ApiError(
            422,
            "VALIDATION_ERROR",
            "Please check the submitted information.",
            {"fields": fields},
        ),
    )


@app.get("/health", tags=["Operations"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    redis_available = check_redis()
    if not redis_available and settings.environment == "production":
        raise ApiError(
            503,
            "REDIS_UNAVAILABLE",
            "The service is temporarily unavailable.",
        )

    return {
        "status": "ok" if redis_available else "degraded",
        "database": "ok",
        "redis": "ok" if redis_available else "unavailable",
    }


for router in (
    auth.router,
    profile.router,
    food.router,
    reservations.router,
    trust.router,
    admin.router,
    notifications.router,
    deliveries.router,
    mano.router,
    matching.router,
    safety.router,
):
    app.include_router(router, prefix=settings.api_v1_prefix)

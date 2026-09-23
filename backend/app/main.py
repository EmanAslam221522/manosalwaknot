from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import admin, auth, deliveries, food, mano, notifications, profile, reservations, trust
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import ApiError, api_error_handler

settings = get_settings()
app = FastAPI(
    title="ManOSalwaKnot API",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    openapi_url="/openapi.json" if settings.environment != "production" else None,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Client-Request-Id", "X-Idempotency-Key"],
        expose_headers=["X-Request-Id"],
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
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
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [{"field": ".".join(str(value) for value in error["loc"]), "message": error["msg"]} for error in exc.errors()]
    return api_error_handler(
        request,
        ApiError(422, "VALIDATION_ERROR", "Please check the submitted information.", {"fields": fields}),
    )


@app.get("/health", tags=["Operations"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


for router in (auth.router, profile.router, food.router, reservations.router, trust.router, admin.router, notifications.router, deliveries.router, mano.router):
    app.include_router(router, prefix="/api/v1")

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ManOSalwaKnot API"
    environment: Literal["development", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    migrations_database_url: str | None = None
    redis_url: str
    jwt_secret: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    handover_token_minutes: int = Field(default=10, ge=2, le=30)
    cors_origins: list[str] = Field(default_factory=list)
    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: AnyHttpUrl = Field(default_factory=lambda: AnyHttpUrl("https://api.groq.com/openai/v1"))
    otp_debug_code: SecretStr | None = None
    max_upload_bytes: int = Field(default=8_000_000, ge=100_000, le=20_000_000)

    @field_validator("database_url", "migrations_database_url")
    @classmethod
    def require_postgresql(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql://", 1)
        if not value.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("Database URLs must use PostgreSQL")
        return value.replace("postgresql://", "postgresql+psycopg://", 1)

    @field_validator("jwt_secret")
    @classmethod
    def strong_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

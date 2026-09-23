import pytest
from pydantic import ValidationError

from app.core.config import Settings

BASE = {
    "database_url": "postgresql://mano:password@localhost:5432/manosalwa",
    "redis_url": "redis://localhost:6379/0",
    "jwt_secret": "a-secret-value-that-is-longer-than-thirty-two-characters",
}


def test_postgresql_url_is_normalized_to_psycopg() -> None:
    settings = Settings(**BASE)
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_rejects_non_postgresql_database() -> None:
    with pytest.raises(ValidationError):
        Settings(**{**BASE, "database_url": "sqlite:///local.db"})


def test_rejects_weak_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(**{**BASE, "jwt_secret": "too-short"})


def test_environment_is_explicit() -> None:
    with pytest.raises(ValidationError):
        Settings(**{**BASE, "environment": "qa"})

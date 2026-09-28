from typing import NoReturn

import pytest

from app.core import rate_limit


def raise_invalid_url() -> NoReturn:
    raise ValueError("invalid Redis URL")


def test_redis_health_handles_client_creation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rate_limit, "get_redis", raise_invalid_url)
    assert rate_limit.check_redis() is False

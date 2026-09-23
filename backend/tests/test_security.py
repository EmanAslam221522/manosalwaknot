from uuid import uuid4

import pytest

from app.core.errors import ApiError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_opaque_token,
    hash_password,
    new_opaque_token,
    verify_password,
)


def test_password_is_argon2_hashed_and_verifiable() -> None:
    encoded = hash_password("A-strong-test-password-123")
    assert encoded != "A-strong-test-password-123"
    assert encoded.startswith("$argon2")
    assert verify_password("A-strong-test-password-123", encoded)
    assert not verify_password("wrong-password", encoded)


def test_opaque_tokens_are_random_and_only_hash_is_stable() -> None:
    first = new_opaque_token()
    second = new_opaque_token()
    assert first != second
    assert len(first) >= 48
    assert hash_opaque_token(first) == hash_opaque_token(first)
    assert hash_opaque_token(first) != hash_opaque_token(second)


def test_access_token_round_trip_binds_user_and_session() -> None:
    user_id, session_id = uuid4(), uuid4()
    assert decode_access_token(create_access_token(user_id, session_id)) == (user_id, session_id)


def test_refresh_token_cannot_be_used_as_access_token() -> None:
    with pytest.raises(ApiError) as caught:
        decode_access_token(new_opaque_token())
    assert caught.value.status_code == 401
    assert caught.value.code == "INVALID_ACCESS_TOKEN"

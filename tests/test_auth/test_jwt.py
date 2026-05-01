import time

import pytest
from jose import jwt

from src.auth.service import create_access_token, create_refresh_token, verify_token
from src.core.exceptions import AuthenticationError


def test_valid_access_token():
    token = create_access_token("admin_user")
    username = verify_token(token, expected_type="access")
    assert username == "admin_user"


def test_refresh_token_rejected_as_access():
    token = create_refresh_token("admin_user")
    with pytest.raises(AuthenticationError):
        verify_token(token, expected_type="access")


def test_access_token_rejected_as_refresh():
    token = create_access_token("admin_user")
    with pytest.raises(AuthenticationError):
        verify_token(token, expected_type="refresh")


def test_tampered_token_raises():
    token = create_access_token("admin_user")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(AuthenticationError):
        verify_token(tampered)


def test_expired_token_raises(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from config.settings import settings

    # Create a token that is already expired
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    token = jwt.encode(
        {"sub": "admin_user", "type": "access", "exp": past},
        settings.AUTH_SECRET_KEY,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        verify_token(token)

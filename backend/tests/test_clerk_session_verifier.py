from __future__ import annotations

import pytest
from clerk_backend_api.security.types import AuthStatus, RequestState
from starlette.requests import Request

from app.auth.clerk import ClerkSessionVerificationError, ClerkSessionVerifier
from app.core.config import Settings


def make_request(authorization: str | None = "Bearer session-token") -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    return Request({"type": "http", "headers": headers})


def make_verifier(secret: str | None = "clerk-secret") -> ClerkSessionVerifier:
    return ClerkSessionVerifier(
        Settings(
            clerk_secret_key=secret,
            clerk_authorized_parties="https://green-mate.example.com",
        )
    )


def assert_sanitized(exc: ClerkSessionVerificationError) -> None:
    rendered = str(exc)

    assert rendered == "Authentication failed"
    assert "session-token" not in rendered
    assert "clerk-secret" not in rendered
    assert "user_123" not in rendered
    assert "raw-claim" not in rendered


def test_missing_bearer_token_fails_closed_without_calling_clerk_sdk(monkeypatch):
    def fail_if_called(*_args: object, **_kwargs: object) -> RequestState:
        raise AssertionError("Clerk SDK should not be called without a bearer token")

    monkeypatch.setattr("app.auth.clerk.authenticate_request", fail_if_called)

    with pytest.raises(ClerkSessionVerificationError) as exc_info:
        make_verifier().verify_request(make_request(None))

    assert_sanitized(exc_info.value)


@pytest.mark.parametrize(
    "authorization",
    [
        "Basic session-token",
        "Bearer",
        "Bearer ",
        "session-token",
    ],
)
def test_malformed_authorization_header_fails_closed_without_calling_clerk_sdk(
    authorization: str,
    monkeypatch: pytest.MonkeyPatch,
):
    def fail_if_called(*_args: object, **_kwargs: object) -> RequestState:
        raise AssertionError("Clerk SDK should not be called without a bearer token")

    monkeypatch.setattr("app.auth.clerk.authenticate_request", fail_if_called)

    with pytest.raises(ClerkSessionVerificationError) as exc_info:
        make_verifier().verify_request(make_request(authorization))

    assert_sanitized(exc_info.value)


def test_missing_secret_key_fails_closed_without_exposing_configuration(monkeypatch):
    def fail_if_called(*_args: object, **_kwargs: object) -> RequestState:
        raise AssertionError("Clerk SDK should not be called without a secret key")

    monkeypatch.setattr("app.auth.clerk.authenticate_request", fail_if_called)

    with pytest.raises(ClerkSessionVerificationError) as exc_info:
        make_verifier(secret=None).verify_request(make_request())

    assert_sanitized(exc_info.value)


def test_signed_out_or_invalid_token_fails_closed_with_sanitized_message(monkeypatch):
    def fake_authenticate_request(request: Request, options: object) -> RequestState:
        assert request.headers["authorization"] == "Bearer session-token"
        assert getattr(options, "secret_key") == "clerk-secret"
        assert getattr(options, "authorized_parties") == ["https://green-mate.example.com"]
        return RequestState(
            status=AuthStatus.SIGNED_OUT,
            token="session-token",
            payload={"sub": "user_123", "claim": "raw-claim"},
        )

    monkeypatch.setattr("app.auth.clerk.authenticate_request", fake_authenticate_request)

    with pytest.raises(ClerkSessionVerificationError) as exc_info:
        make_verifier().verify_request(make_request())

    assert_sanitized(exc_info.value)


def test_valid_token_returns_clerk_user_id_and_optional_profile(monkeypatch):
    def fake_authenticate_request(_request: Request, _options: object) -> RequestState:
        return RequestState(
            status=AuthStatus.SIGNED_IN,
            payload={
                "sub": "user_123",
                "email": "midoriko@example.com",
                "name": "緑子",
                "image_url": "https://example.com/avatar.jpg",
            },
        )

    monkeypatch.setattr("app.auth.clerk.authenticate_request", fake_authenticate_request)

    claims = make_verifier().verify_request(make_request())

    assert claims.clerk_user_id == "user_123"
    assert claims.email == "midoriko@example.com"
    assert claims.display_name == "緑子"
    assert claims.avatar_url == "https://example.com/avatar.jpg"


def test_signed_in_state_without_subject_fails_closed(monkeypatch):
    def fake_authenticate_request(_request: Request, _options: object) -> RequestState:
        return RequestState(
            status=AuthStatus.SIGNED_IN,
            token="session-token",
            payload={"claim": "raw-claim"},
        )

    monkeypatch.setattr("app.auth.clerk.authenticate_request", fake_authenticate_request)

    with pytest.raises(ClerkSessionVerificationError) as exc_info:
        make_verifier().verify_request(make_request())

    assert_sanitized(exc_info.value)


def test_clerk_sdk_exception_fails_closed_with_sanitized_message(monkeypatch):
    def fake_authenticate_request(_request: Request, _options: object) -> RequestState:
        raise RuntimeError("bad token session-token raw-claim clerk-secret")

    monkeypatch.setattr("app.auth.clerk.authenticate_request", fake_authenticate_request)

    with pytest.raises(ClerkSessionVerificationError) as exc_info:
        make_verifier().verify_request(make_request())

    assert_sanitized(exc_info.value)

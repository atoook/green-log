from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import anyio
import pytest
from starlette.requests import Request
from svix.webhooks import Webhook

from app.auth.webhooks import ClerkWebhookVerificationError, ClerkWebhookVerifier
from app.core.config import Settings


WEBHOOK_SECRET = "whsec_test_secret"
RAW_PAYLOAD = b'{"type":"user.created","data":{"id":"user_123"},"object":"event"}'
SIGNATURE = "v1,raw-payload-signature"
TOKEN = "Bearer sensitive-token"


def make_request(
    body: bytes = RAW_PAYLOAD,
    headers: dict[str, str] | None = None,
) -> Request:
    header_items = [
        (key.lower().encode(), value.encode())
        for key, value in (headers or {}).items()
    ]

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request({"type": "http", "headers": header_items}, receive)


def make_settings(secret: str | None = WEBHOOK_SECRET) -> Settings:
    return Settings(clerk_webhook_secret=secret)


def verify(verifier: ClerkWebhookVerifier, request: Request) -> Any:
    return anyio.run(verifier.verify_request, request)


def assert_sanitized(exc: ClerkWebhookVerificationError) -> None:
    rendered = str(exc)

    assert rendered == "Webhook verification failed"
    assert RAW_PAYLOAD.decode() not in rendered
    assert WEBHOOK_SECRET not in rendered
    assert SIGNATURE not in rendered
    assert "sensitive-token" not in rendered
    assert "user_123" not in rendered


def signed_headers(payload: bytes, secret: str = WEBHOOK_SECRET) -> dict[str, str]:
    msg_id = "msg_123"
    timestamp = datetime.now(timezone.utc)
    signature = Webhook(secret).sign(msg_id, timestamp, payload.decode())
    return {
        "svix-id": msg_id,
        "svix-timestamp": str(int(timestamp.timestamp())),
        "svix-signature": signature,
        "authorization": TOKEN,
    }


def test_missing_webhook_secret_fails_closed_without_calling_svix(monkeypatch):
    def fail_if_called(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("Svix should not be constructed without a webhook secret")

    monkeypatch.setattr("app.auth.webhooks.Webhook", fail_if_called)

    verifier = ClerkWebhookVerifier(make_settings(secret=None))

    with pytest.raises(ClerkWebhookVerificationError) as exc_info:
        verify(verifier, make_request(headers={"svix-signature": SIGNATURE}))

    assert_sanitized(exc_info.value)


def test_invalid_svix_signature_fails_with_sanitized_error():
    verifier = ClerkWebhookVerifier(make_settings())

    with pytest.raises(ClerkWebhookVerificationError) as exc_info:
        verify(
            verifier,
            make_request(
                headers={
                    "svix-id": "msg_123",
                    "svix-timestamp": "123",
                    "svix-signature": SIGNATURE,
                    "authorization": TOKEN,
                }
            )
        )

    assert_sanitized(exc_info.value)


def test_raw_body_and_svix_headers_are_passed_to_svix_verifier(monkeypatch):
    captured: dict[str, object] = {}

    class FakeWebhook:
        def __init__(self, secret: str) -> None:
            captured["secret"] = secret

        def verify(self, data: bytes | str, headers: dict[str, str]) -> dict[str, object]:
            captured["data"] = data
            captured["headers"] = headers
            return {
                "id": "evt_123",
                "type": "user.created",
                "data": {
                    "id": "user_123",
                    "email_addresses": [
                        {"id": "email_1", "email_address": "secondary@example.com"},
                        {"id": "email_2", "email_address": "primary@example.com"},
                    ],
                    "primary_email_address_id": "email_2",
                    "first_name": "Midori",
                    "last_name": "Ito",
                    "image_url": "https://example.com/avatar.jpg",
                },
            }

    monkeypatch.setattr("app.auth.webhooks.Webhook", FakeWebhook)

    event = verify(
        ClerkWebhookVerifier(make_settings()),
        make_request(
            headers={
                "Svix-Id": "msg_123",
                "Svix-Timestamp": "456",
                "Svix-Signature": SIGNATURE,
                "Authorization": TOKEN,
            }
        )
    )

    assert captured == {
        "secret": WEBHOOK_SECRET,
        "data": RAW_PAYLOAD,
        "headers": {
            "svix-id": "msg_123",
            "svix-timestamp": "456",
            "svix-signature": SIGNATURE,
        },
    }
    assert event.event_id == "evt_123"
    assert event.event_type == "user.created"
    assert event.clerk_user_id == "user_123"
    assert event.primary_email == "primary@example.com"
    assert event.display_name == "Midori Ito"
    assert event.avatar_url == "https://example.com/avatar.jpg"


def test_unsupported_event_type_is_rejected_after_verification(monkeypatch):
    class FakeWebhook:
        def __init__(self, _secret: str) -> None:
            pass

        def verify(self, _data: bytes | str, _headers: dict[str, str]) -> dict[str, object]:
            return {"id": "evt_123", "type": "session.created", "data": {"id": "user_123"}}

    monkeypatch.setattr("app.auth.webhooks.Webhook", FakeWebhook)

    with pytest.raises(ClerkWebhookVerificationError) as exc_info:
        verify(ClerkWebhookVerifier(make_settings()), make_request())

    assert_sanitized(exc_info.value)


@pytest.mark.parametrize("event_type", ["user.created", "user.updated", "user.deleted"])
def test_supported_events_parse_to_typed_event_with_profile_fields(event_type: str):
    payload = json.dumps(
        {
            "id": f"evt_{event_type}",
            "type": event_type,
            "data": {
                "id": "user_123",
                "email_addresses": [{"email_address": "midoriko@example.com"}],
                "username": "midoriko",
                "image_url": "https://example.com/avatar.jpg",
            },
        },
        separators=(",", ":"),
    ).encode()

    event = verify(
        ClerkWebhookVerifier(make_settings()),
        make_request(body=payload, headers=signed_headers(payload))
    )

    assert event.event_id == f"evt_{event_type}"
    assert event.event_type == event_type
    assert event.clerk_user_id == "user_123"
    assert event.primary_email == "midoriko@example.com"
    assert event.display_name == "midoriko"
    assert event.avatar_url == "https://example.com/avatar.jpg"


@pytest.mark.parametrize(
    "verified_payload",
    [
        {"id": "evt_123", "type": "user.created", "data": {}},
        {"id": "evt_123", "type": "user.created"},
        {"id": "evt_123", "type": "user.created", "data": {"id": ""}},
    ],
)
def test_malformed_or_missing_data_id_is_rejected(
    verified_payload: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeWebhook:
        def __init__(self, _secret: str) -> None:
            pass

        def verify(self, _data: bytes | str, _headers: dict[str, str]) -> dict[str, object]:
            return verified_payload

    monkeypatch.setattr("app.auth.webhooks.Webhook", FakeWebhook)

    with pytest.raises(ClerkWebhookVerificationError) as exc_info:
        verify(ClerkWebhookVerifier(make_settings()), make_request())

    assert_sanitized(exc_info.value)

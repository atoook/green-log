from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session, select
from svix.webhooks import Webhook

from app.auth.webhooks import ClerkWebhookVerifier
from app.core.config import Settings
from app.main import app
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.routers.webhooks import get_clerk_webhook_verifier
from app.services.user_service import InactiveUserError, UserProfileInput, UserService


WEBHOOK_SECRET = "whsec_dGVzdF9zZWNyZXQ"


def compact_payload(
    event_type: str,
    *,
    event_id: str,
    clerk_user_id: str,
    email: str | None = "midoriko@example.com",
    first_name: str | None = "Midori",
    last_name: str | None = "Ito",
    image_url: str | None = "https://example.com/avatar.jpg",
) -> bytes:
    data: dict[str, Any] = {
        "id": clerk_user_id,
        "email_addresses": [{"id": "email_1", "email_address": email}]
        if email is not None
        else [],
        "primary_email_address_id": "email_1",
        "first_name": first_name,
        "last_name": last_name,
        "image_url": image_url,
    }
    return json.dumps(
        {"id": event_id, "type": event_type, "data": data},
        separators=(",", ":"),
    ).encode()


def signed_headers(payload: bytes, *, msg_id: str = "msg_integration") -> dict[str, str]:
    timestamp = datetime.now(timezone.utc)
    signature = Webhook(WEBHOOK_SECRET).sign(msg_id, timestamp, payload.decode())
    return {
        "svix-id": msg_id,
        "svix-timestamp": str(int(timestamp.timestamp())),
        "svix-signature": signature,
    }


def install_test_webhook_verifier() -> None:
    app.dependency_overrides[get_clerk_webhook_verifier] = lambda: ClerkWebhookVerifier(
        Settings(clerk_webhook_secret=WEBHOOK_SECRET)
    )


def post_signed_webhook(api_client: TestClient, payload: bytes) -> Response:
    return api_client.post(
        "/webhooks/clerk",
        content=payload,
        headers=signed_headers(payload),
    )


def users(session: Session) -> list[User]:
    return session.exec(select(User)).all()


def user_by_clerk_id(session: Session, clerk_user_id: str) -> User:
    return session.exec(select(User).where(User.clerk_user_id == clerk_user_id)).one()


def make_user_service(session: Session) -> UserService:
    return UserService(UserRepository(session))


def test_invalid_signature_rejects_event_without_changing_user_state(
    api_client: TestClient,
    test_engine,
):
    install_test_webhook_verifier()
    payload = compact_payload(
        "user.created",
        event_id="evt_invalid_signature",
        clerk_user_id="user_invalid_signature",
    )

    response = api_client.post(
        "/webhooks/clerk",
        content=payload,
        headers={
            "svix-id": "msg_invalid_signature",
            "svix-timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            "svix-signature": "v1,invalid-signature",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid webhook"}
    assert "user_invalid_signature" not in response.text
    assert "invalid-signature" not in response.text
    assert WEBHOOK_SECRET not in response.text

    with Session(test_engine) as session:
        assert users(session) == []


def test_duplicate_create_and_update_events_do_not_duplicate_application_user(
    api_client: TestClient,
    test_engine,
):
    install_test_webhook_verifier()
    created_payload = compact_payload(
        "user.created",
        event_id="evt_duplicate_create",
        clerk_user_id="user_duplicate",
        email="created@example.com",
        first_name="Created",
        last_name="User",
    )
    updated_payload = compact_payload(
        "user.updated",
        event_id="evt_duplicate_update",
        clerk_user_id="user_duplicate",
        email="updated@example.com",
        first_name="Updated",
        last_name="User",
        image_url=None,
    )

    first_create = post_signed_webhook(api_client, created_payload)
    duplicate_create = post_signed_webhook(api_client, created_payload)
    first_update = post_signed_webhook(api_client, updated_payload)
    duplicate_update = post_signed_webhook(api_client, updated_payload)

    assert first_create.status_code == 200
    assert duplicate_create.status_code == 200
    assert first_update.status_code == 200
    assert duplicate_update.status_code == 200
    assert first_create.json() == {"received": True}

    with Session(test_engine) as session:
        stored_users = users(session)

        assert len(stored_users) == 1
        stored_user = stored_users[0]
        assert stored_user.clerk_user_id == "user_duplicate"
        assert stored_user.status == "active"
        assert stored_user.primary_email == "updated@example.com"
        assert stored_user.display_name == "Updated User"
        assert stored_user.avatar_url is None


def test_deleted_event_makes_existing_user_unusable_for_protected_data_operation(
    api_client: TestClient,
    test_engine,
):
    install_test_webhook_verifier()
    created_payload = compact_payload(
        "user.created",
        event_id="evt_deleted_create",
        clerk_user_id="user_deleted_by_webhook",
    )
    deleted_payload = compact_payload(
        "user.deleted",
        event_id="evt_deleted_delete",
        clerk_user_id="user_deleted_by_webhook",
    )

    assert post_signed_webhook(api_client, created_payload).status_code == 200
    assert post_signed_webhook(api_client, deleted_payload).status_code == 200

    with Session(test_engine) as session:
        user_service = make_user_service(session)
        stored_user = user_by_clerk_id(session, "user_deleted_by_webhook")

        assert stored_user.status == "deleted"
        with pytest.raises(InactiveUserError):
            user_service.require_active_owner_id(stored_user)

        lazy_user = user_service.get_or_create_from_clerk(
            UserProfileInput(
                clerk_user_id="user_deleted_by_webhook",
                primary_email="late-session@example.com",
            )
        )

        assert lazy_user.id == stored_user.id
        assert lazy_user.status == "deleted"
        with pytest.raises(InactiveUserError):
            user_service.require_active_owner_id(lazy_user)


def test_lazy_upsert_before_webhook_retry_converges_to_single_updated_user(
    api_client: TestClient,
    test_engine,
):
    install_test_webhook_verifier()

    with Session(test_engine) as session:
        lazy_user = make_user_service(session).get_or_create_from_clerk(
            UserProfileInput(
                clerk_user_id="user_lazy_then_webhook",
                primary_email="lazy@example.com",
                display_name="Lazy User",
            )
        )
        lazy_user_id = lazy_user.id

    updated_payload = compact_payload(
        "user.updated",
        event_id="evt_lazy_retry_update",
        clerk_user_id="user_lazy_then_webhook",
        email="webhook@example.com",
        first_name="Webhook",
        last_name="Retry",
    )

    first_update = post_signed_webhook(api_client, updated_payload)
    retry_update = post_signed_webhook(api_client, updated_payload)

    assert first_update.status_code == 200
    assert retry_update.status_code == 200

    with Session(test_engine) as session:
        stored_users = users(session)

        assert len(stored_users) == 1
        stored_user = stored_users[0]
        assert stored_user.id == lazy_user_id
        assert stored_user.clerk_user_id == "user_lazy_then_webhook"
        assert stored_user.primary_email == "webhook@example.com"
        assert stored_user.display_name == "Webhook Retry"
        assert stored_user.status == "active"

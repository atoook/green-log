from __future__ import annotations

import pytest
from fastapi import Request
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.auth.webhooks import ClerkWebhookEvent, ClerkWebhookVerificationError
from app.main import app
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.routers.webhooks import get_clerk_webhook_service, get_clerk_webhook_verifier
from app.services.clerk_webhook_service import ClerkWebhookService
from app.services.user_service import InactiveUserError, UserProfileInput, UserService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_user_service(session: Session) -> UserService:
    return UserService(UserRepository(session))


def count_users(session: Session) -> int:
    return len(session.exec(select(User)).all())


def event(
    event_type: str,
    *,
    clerk_user_id: str = "user_clerk_123",
    primary_email: str | None = "midoriko@example.com",
    display_name: str | None = "Midori Ito",
    avatar_url: str | None = "https://example.com/avatar.jpg",
) -> ClerkWebhookEvent:
    return ClerkWebhookEvent(
        event_id=f"evt_{event_type}",
        event_type=event_type,
        clerk_user_id=clerk_user_id,
        primary_email=primary_email,
        display_name=display_name,
        avatar_url=avatar_url,
    )


@pytest.mark.parametrize("event_type", ["user.created", "user.updated"])
def test_clerk_webhook_service_upserts_created_and_updated_events(
    session: Session,
    event_type: str,
):
    service = ClerkWebhookService(make_user_service(session))

    first = service.handle_event(event(event_type))
    second = service.handle_event(
        event(
            event_type,
            primary_email="updated@example.com",
            display_name="Updated Name",
            avatar_url=None,
        )
    )

    assert count_users(session) == 1
    assert second.id == first.id
    assert second.status == "active"
    assert second.primary_email == "updated@example.com"
    assert second.display_name == "Updated Name"
    assert second.avatar_url is None


def test_clerk_webhook_service_does_not_duplicate_lazy_upserted_user(
    session: Session,
):
    user_service = make_user_service(session)
    lazy_user = user_service.get_or_create_from_clerk(
        UserProfileInput(
            clerk_user_id="user_lazy",
            primary_email="lazy@example.com",
            display_name="Lazy User",
        )
    )

    synced = ClerkWebhookService(user_service).handle_event(
        event(
            "user.updated",
            clerk_user_id="user_lazy",
            primary_email="webhook@example.com",
            display_name="Webhook User",
        )
    )

    assert count_users(session) == 1
    assert synced.id == lazy_user.id
    assert synced.primary_email == "webhook@example.com"
    assert synced.display_name == "Webhook User"


def test_clerk_webhook_service_marks_deleted_user_inactive(session: Session):
    user_service = make_user_service(session)
    user = user_service.sync_from_clerk_event(
        UserProfileInput(clerk_user_id="user_deleted", primary_email="gone@example.com")
    )

    deleted = ClerkWebhookService(user_service).handle_event(
        event("user.deleted", clerk_user_id="user_deleted")
    )

    assert deleted is not None
    assert deleted.id == user.id
    assert deleted.status == "deleted"
    with pytest.raises(InactiveUserError):
        user_service.require_active_owner_id(deleted)


def test_clerk_webhook_service_does_not_reactivate_deleted_user_from_late_update(
    session: Session,
):
    user_service = make_user_service(session)
    service = ClerkWebhookService(user_service)
    created = service.handle_event(
        event(
            "user.created",
            clerk_user_id="user_late_update",
            primary_email="before-delete@example.com",
        )
    )

    deleted = service.handle_event(
        event("user.deleted", clerk_user_id="user_late_update")
    )
    late_update = service.handle_event(
        event(
            "user.updated",
            clerk_user_id="user_late_update",
            primary_email="after-delete@example.com",
            display_name="Late Update",
        )
    )

    assert count_users(session) == 1
    assert created is not None
    assert deleted is not None
    stored_users = session.exec(select(User)).all()
    assert len(stored_users) == 1
    stored_user = stored_users[0]
    assert late_update.id == created.id == stored_user.id
    assert stored_user.status == "deleted"
    with pytest.raises(InactiveUserError):
        user_service.require_active_owner_id(stored_user)


class StubVerifier:
    def __init__(
        self,
        verified_event: ClerkWebhookEvent | None = None,
        *,
        fail: bool = False,
    ) -> None:
        self.verified_event = verified_event or event("user.created")
        self.fail = fail
        self.calls = 0

    async def verify_request(self, request: Request) -> ClerkWebhookEvent:
        self.calls += 1
        if self.fail:
            raise ClerkWebhookVerificationError()
        return self.verified_event


class StubWebhookService:
    def __init__(self) -> None:
        self.events: list[ClerkWebhookEvent] = []

    def handle_event(self, verified_event: ClerkWebhookEvent) -> None:
        self.events.append(verified_event)


def test_clerk_webhook_route_returns_received_after_verified_event(api_client):
    verifier = StubVerifier(event("user.updated", clerk_user_id="user_route"))
    service = StubWebhookService()
    app.dependency_overrides[get_clerk_webhook_verifier] = lambda: verifier
    app.dependency_overrides[get_clerk_webhook_service] = lambda: service

    response = api_client.post("/webhooks/clerk", json={"ignored": "raw"})

    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert verifier.calls == 1
    assert [handled.clerk_user_id for handled in service.events] == ["user_route"]


def test_clerk_webhook_route_rejects_unverified_event_without_calling_service(api_client):
    verifier = StubVerifier(fail=True)
    service = StubWebhookService()
    app.dependency_overrides[get_clerk_webhook_verifier] = lambda: verifier
    app.dependency_overrides[get_clerk_webhook_service] = lambda: service

    response = api_client.post(
        "/webhooks/clerk",
        content=b'{"secret":"payload","id":"user_123"}',
        headers={"svix-signature": "sensitive-signature"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid webhook"}
    assert verifier.calls == 1
    assert service.events == []
    assert "sensitive-signature" not in response.text
    assert "user_123" not in response.text

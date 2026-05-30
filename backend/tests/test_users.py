from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.auth.types import UserStatus
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import (
    InactiveUserError,
    UserProfileInput,
    UserService,
)


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


def make_service(session: Session) -> UserService:
    return UserService(UserRepository(session))


def profile(
    clerk_user_id: str = "user_2abc",
    *,
    primary_email: str | None = "midoriko@example.com",
    display_name: str | None = "緑子",
    avatar_url: str | None = "https://example.com/avatar.jpg",
    status: UserStatus = "active",
) -> UserProfileInput:
    return UserProfileInput(
        clerk_user_id=clerk_user_id,
        primary_email=primary_email,
        display_name=display_name,
        avatar_url=avatar_url,
        status=status,
    )


def count_users(session: Session) -> int:
    return len(session.exec(select(User)).all())


def test_get_or_create_from_clerk_creates_application_user_once(session: Session):
    service = make_service(session)

    first = service.get_or_create_from_clerk(profile())
    second = service.get_or_create_from_clerk(
        profile(display_name="更新されない表示名", primary_email="new@example.com")
    )

    assert count_users(session) == 1
    assert second.id == first.id
    assert second.clerk_user_id == "user_2abc"
    assert second.status == "active"
    assert second.primary_email == "midoriko@example.com"
    assert second.display_name == "緑子"
    assert second.id != second.clerk_user_id


def test_sync_from_clerk_event_idempotently_creates_and_updates_profile(session: Session):
    service = make_service(session)

    first = service.sync_from_clerk_event(profile())
    second = service.sync_from_clerk_event(
        profile(
            primary_email="updated@example.com",
            display_name="更新済み",
            avatar_url=None,
        )
    )

    assert count_users(session) == 1
    assert second.id == first.id
    assert second.primary_email == "updated@example.com"
    assert second.display_name == "更新済み"
    assert second.avatar_url is None
    assert second.updated_at >= first.updated_at


@pytest.mark.parametrize("status", ["disabled", "deleted"])
def test_non_active_user_cannot_be_used_as_protected_owner(
    session: Session,
    status: UserStatus,
):
    service = make_service(session)
    user = service.sync_from_clerk_event(profile(status=status))

    with pytest.raises(InactiveUserError) as exc_info:
        service.require_active_owner_id(user)

    assert exc_info.value.status == status


def test_active_owner_id_returns_only_internal_application_user_id(session: Session):
    service = make_service(session)
    user = service.get_or_create_from_clerk(profile(clerk_user_id="clerk-owner"))

    owner_id = service.require_active_owner_id(user)

    assert owner_id == user.id
    assert owner_id != "clerk-owner"


def test_mark_deleted_updates_existing_user_and_returns_none_for_absent_user(session: Session):
    service = make_service(session)
    user = service.get_or_create_from_clerk(profile())

    deleted = service.mark_deleted(user.clerk_user_id)
    missing = service.mark_deleted("missing-clerk-user")

    assert deleted is not None
    assert deleted.id == user.id
    assert deleted.status == "deleted"
    assert missing is None


def test_repository_recovers_existing_user_after_unique_constraint_race(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    existing = User(
        id="winner-user-id",
        clerk_user_id="race-clerk-user",
        status="active",
        primary_email="winner@example.com",
    )
    session.add(existing)
    session.commit()

    repository = UserRepository(session)
    original_lookup = repository.get_by_clerk_user_id
    original_commit = session.commit
    lookup_calls = 0

    def lookup_with_stale_initial_read(clerk_user_id: str) -> User | None:
        nonlocal lookup_calls
        lookup_calls += 1
        if lookup_calls == 1:
            return None
        return original_lookup(clerk_user_id)

    def raise_integrity_error_once() -> None:
        session.commit = original_commit
        raise IntegrityError("INSERT INTO users", {}, Exception("unique race"))

    monkeypatch.setattr(repository, "get_by_clerk_user_id", lookup_with_stale_initial_read)
    monkeypatch.setattr(session, "commit", raise_integrity_error_once)

    recovered = repository.upsert_by_clerk_user_id(
        User(
            id="loser-user-id",
            clerk_user_id="race-clerk-user",
            status="active",
            primary_email="loser@example.com",
        )
    )

    assert recovered.id == "winner-user-id"
    assert count_users(session) == 1
    assert recovered.primary_email == "winner@example.com"

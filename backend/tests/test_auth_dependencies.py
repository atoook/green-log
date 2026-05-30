from __future__ import annotations

import pytest
from fastapi import HTTPException, Request
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.auth.types import ClerkSessionClaims, ClerkSessionVerificationError, UserStatus
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services import user_service as user_service_module
from app.services.user_service import UserProfileInput, UserService


class StubVerifier:
    def __init__(self, claims: ClerkSessionClaims | None = None) -> None:
        self.claims = claims
        self.calls = 0

    def verify_request(self, request: Request) -> ClerkSessionClaims:
        self.calls += 1
        if self.claims is None:
            raise ClerkSessionVerificationError()
        return self.claims


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


def request_with_bearer() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/plants",
            "headers": [(b"authorization", b"Bearer test-token")],
        }
    )


def count_users(session: Session) -> int:
    return len(session.exec(select(User)).all())


def make_user_service(session: Session) -> UserService:
    return UserService(UserRepository(session))


def existing_user(
    session: Session,
    *,
    status: UserStatus = "active",
    clerk_user_id: str = "clerk-existing",
) -> User:
    user = User(
        id=f"internal-{status}",
        clerk_user_id=clerk_user_id,
        status=status,
        primary_email="stored@example.com",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_current_user_dependency_lazily_creates_application_user_from_clerk_claims(
    session: Session,
):
    verifier = StubVerifier(
        ClerkSessionClaims(
            clerk_user_id="clerk-user-1",
            email="leaf@example.com",
            display_name="Leaf Keeper",
            avatar_url="https://example.com/avatar.jpg",
        )
    )

    current_user = get_current_user(request_with_bearer(), make_user_service(session), verifier)

    assert verifier.calls == 1
    assert count_users(session) == 1
    assert current_user.clerk_user_id == "clerk-user-1"
    assert current_user.status == "active"
    assert current_user.id != "clerk-user-1"

    stored = session.exec(select(User)).one()
    assert current_user.id == stored.id
    assert stored.primary_email == "leaf@example.com"
    assert stored.display_name == "Leaf Keeper"
    assert stored.avatar_url == "https://example.com/avatar.jpg"


def test_current_user_dependency_reuses_existing_application_user(session: Session):
    user = existing_user(session, clerk_user_id="clerk-returning")
    verifier = StubVerifier(
        ClerkSessionClaims(
            clerk_user_id="clerk-returning",
            email="new@example.com",
            display_name="New Name",
        )
    )

    current_user = get_current_user(request_with_bearer(), make_user_service(session), verifier)

    assert count_users(session) == 1
    assert current_user.id == user.id
    assert current_user.id != "clerk-returning"
    assert current_user.status == "active"


@pytest.mark.parametrize("status", ["disabled", "deleted"])
def test_current_user_dependency_rejects_inactive_users_with_403(
    session: Session,
    status: UserStatus,
):
    existing_user(session, status=status, clerk_user_id="clerk-inactive")
    verifier = StubVerifier(ClerkSessionClaims(clerk_user_id="clerk-inactive"))

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(request_with_bearer(), make_user_service(session), verifier)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden"
    assert "clerk-inactive" not in exc_info.value.detail


def test_current_user_dependency_maps_invalid_auth_to_401_without_user_operation(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    verifier = StubVerifier()
    user_service_called = False

    def fail_if_called(self: UserService, profile: UserProfileInput) -> User:
        nonlocal user_service_called
        user_service_called = True
        raise AssertionError("UserService must not run when auth cannot be verified")

    monkeypatch.setattr(
        user_service_module.UserService,
        "get_or_create_from_clerk",
        fail_if_called,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(request_with_bearer(), make_user_service(session), verifier)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authentication required"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    assert user_service_called is False
    assert count_users(session) == 0

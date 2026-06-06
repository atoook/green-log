import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.dependencies import get_current_user  # noqa: E402
from app.auth.types import CurrentUser, UserStatus  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def dependency_overrides_are_test_local():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def app_dependency_override():
    def override(dependency, replacement) -> None:
        app.dependency_overrides[dependency] = replacement

    return override


@pytest.fixture()
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def api_client(test_engine):
    def override_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    with TestClient(app) as client:
        yield client


@pytest.fixture()
def current_user_factory(test_engine) -> Callable[..., CurrentUser]:
    def make_current_user(
        user_id: str = "test-user",
        *,
        status: UserStatus = "active",
        clerk_user_id: str | None = None,
    ) -> CurrentUser:
        current_user = CurrentUser(
            id=user_id,
            clerk_user_id=clerk_user_id or f"clerk-{user_id}",
            status=status,
        )

        with Session(test_engine) as session:
            user = session.get(User, current_user.id)
            if user is None:
                user = User(
                    id=current_user.id,
                    clerk_user_id=current_user.clerk_user_id,
                    status=current_user.status,
                )
            else:
                user.clerk_user_id = current_user.clerk_user_id
                user.status = current_user.status
            session.add(user)
            session.commit()

        return current_user

    return make_current_user


@pytest.fixture()
def override_current_user(
    current_user_factory: Callable[..., CurrentUser],
) -> Callable[..., CurrentUser]:
    def use_current_user(
        user_id: str = "test-user",
        *,
        status: UserStatus = "active",
        clerk_user_id: str | None = None,
    ) -> CurrentUser:
        current_user = current_user_factory(
            user_id,
            status=status,
            clerk_user_id=clerk_user_id,
        )

        if current_user.status == "active":
            app.dependency_overrides[get_current_user] = lambda: current_user
        else:
            app.dependency_overrides[get_current_user] = _forbidden_current_user

        return current_user

    return use_current_user


@pytest.fixture()
def protected_client(
    api_client: TestClient,
    override_current_user: Callable[..., CurrentUser],
) -> Callable[..., TestClient]:
    def use_protected_client(
        user_id: str = "test-user",
        *,
        status: UserStatus = "active",
        clerk_user_id: str | None = None,
    ) -> TestClient:
        override_current_user(
            user_id,
            status=status,
            clerk_user_id=clerk_user_id,
        )
        return api_client

    return use_protected_client


def _forbidden_current_user() -> CurrentUser:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden",
    )

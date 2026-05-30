from typing import cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from app.auth.types import UserStatus
from app.models.user import User, utc_now
from app.repositories.user_repository import UserRepository


class UserProfileInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    clerk_user_id: str
    primary_email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    status: UserStatus = "active"


class InactiveUserError(PermissionError):
    def __init__(self, status: UserStatus) -> None:
        self.status = status
        super().__init__("Application user is not active")


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def get_or_create_from_clerk(self, profile: UserProfileInput) -> User:
        return self.repository.upsert_by_clerk_user_id(
            self._new_user(profile),
            update_existing=False,
        )

    def sync_from_clerk_event(self, profile: UserProfileInput) -> User:
        return self.repository.upsert_by_clerk_user_id(
            self._new_user(profile),
            update_existing=True,
        )

    def mark_deleted(self, clerk_user_id: str) -> User | None:
        return self.repository.set_status(clerk_user_id, "deleted")

    def set_status(self, clerk_user_id: str, status: UserStatus) -> User:
        user = self.repository.set_status(clerk_user_id, status)
        if user is None:
            raise LookupError("Application user not found")
        return user

    def require_active_owner_id(self, user: User) -> str:
        if user.status != "active":
            raise InactiveUserError(cast(UserStatus, user.status))
        return user.id

    def _new_user(self, profile: UserProfileInput) -> User:
        now = utc_now()
        return User(
            id=str(uuid4()),
            clerk_user_id=profile.clerk_user_id,
            status=profile.status,
            primary_email=profile.primary_email,
            display_name=profile.display_name,
            avatar_url=profile.avatar_url,
            created_at=now,
            updated_at=now,
        )

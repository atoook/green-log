from typing import Literal

from pydantic import BaseModel


UserStatus = Literal["active", "disabled", "deleted"]


class CurrentUser(BaseModel):
    id: str
    clerk_user_id: str
    status: UserStatus


class ClerkSessionClaims(BaseModel):
    clerk_user_id: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class ClerkSessionVerificationError(PermissionError):
    def __init__(self) -> None:
        super().__init__("Authentication failed")

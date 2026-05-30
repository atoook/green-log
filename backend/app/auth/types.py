from typing import Literal

from pydantic import BaseModel


UserStatus = Literal["active", "disabled", "deleted"]


class CurrentUser(BaseModel):
    id: str
    clerk_user_id: str
    status: UserStatus


from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.auth.types import CurrentUser
from app.db.session import get_session


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
) -> CurrentUser:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


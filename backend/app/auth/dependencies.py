from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.auth.clerk import ClerkSessionVerifier
from app.auth.types import ClerkSessionClaims, ClerkSessionVerificationError, CurrentUser
from app.db.session import get_session
from app.repositories.user_repository import UserRepository
from app.services.user_service import InactiveUserError, UserProfileInput, UserService


def get_clerk_session_verifier() -> ClerkSessionVerifier:
    return ClerkSessionVerifier()


def get_user_service(session: Annotated[Session, Depends(get_session)]) -> UserService:
    return UserService(UserRepository(session))


def get_current_user(
    request: Request,
    user_service: Annotated[UserService, Depends(get_user_service)],
    verifier: Annotated[ClerkSessionVerifier, Depends(get_clerk_session_verifier)],
) -> CurrentUser:
    try:
        claims = verifier.verify_request(request)
    except ClerkSessionVerificationError as exc:
        raise _authentication_error() from exc

    user = user_service.get_or_create_from_clerk(_profile_from_claims(claims))

    try:
        owner_id = user_service.require_active_owner_id(user)
    except InactiveUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        ) from exc

    return CurrentUser(
        id=owner_id,
        clerk_user_id=user.clerk_user_id,
        status="active",
    )


def _profile_from_claims(claims: ClerkSessionClaims) -> UserProfileInput:
    return UserProfileInput(
        clerk_user_id=claims.clerk_user_id,
        primary_email=claims.email,
        display_name=claims.display_name,
        avatar_url=claims.avatar_url,
    )


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )

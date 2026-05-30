from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.auth.webhooks import ClerkWebhookVerificationError, ClerkWebhookVerifier
from app.db.session import get_session
from app.repositories.user_repository import UserRepository
from app.services.clerk_webhook_service import ClerkWebhookService
from app.services.user_service import UserService


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_clerk_webhook_verifier() -> ClerkWebhookVerifier:
    return ClerkWebhookVerifier()


def get_clerk_webhook_service(
    session: Annotated[Session, Depends(get_session)],
) -> ClerkWebhookService:
    return ClerkWebhookService(UserService(UserRepository(session)))


@router.post("/clerk")
async def receive_clerk_webhook(
    request: Request,
    verifier: Annotated[ClerkWebhookVerifier, Depends(get_clerk_webhook_verifier)],
    webhook_service: Annotated[ClerkWebhookService, Depends(get_clerk_webhook_service)],
) -> dict[str, bool]:
    try:
        event = await verifier.verify_request(request)
    except ClerkWebhookVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook",
        ) from exc

    webhook_service.handle_event(event)
    return {"received": True}


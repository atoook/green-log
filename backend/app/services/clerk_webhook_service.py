from __future__ import annotations

from app.auth.webhooks import ClerkWebhookEvent
from app.models.user import User
from app.services.user_service import UserProfileInput, UserService


class ClerkWebhookService:
    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    def handle_event(self, event: ClerkWebhookEvent) -> User | None:
        if event.event_type == "user.deleted":
            return self.user_service.mark_deleted(event.clerk_user_id)

        return self.user_service.sync_from_clerk_event(
            UserProfileInput(
                clerk_user_id=event.clerk_user_id,
                primary_email=event.primary_email,
                display_name=event.display_name,
                avatar_url=event.avatar_url,
                status="active",
            )
        )

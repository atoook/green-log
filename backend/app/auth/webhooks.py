from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from fastapi import Request
from pydantic import BaseModel, ValidationError
from svix.webhooks import Webhook, WebhookVerificationError

from app.core.config import Settings, get_settings

ClerkWebhookEventType = Literal["user.created", "user.updated", "user.deleted"]


class ClerkWebhookEvent(BaseModel):
    event_id: str
    event_type: ClerkWebhookEventType
    clerk_user_id: str
    primary_email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class ClerkWebhookVerificationError(ValueError):
    def __init__(self, reason: str = "verification_failed", safe_detail: str | None = None) -> None:
        super().__init__("Webhook verification failed")
        self.reason = reason
        self.safe_detail = safe_detail


class ClerkWebhookVerifier:
    _SVIX_HEADER_NAMES = ("svix-id", "svix-timestamp", "svix-signature")
    _SUPPORTED_EVENT_TYPES = {"user.created", "user.updated", "user.deleted"}

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def verify_request(self, request: Request) -> ClerkWebhookEvent:
        secret = self._webhook_secret()
        if secret is None:
            raise ClerkWebhookVerificationError(reason="missing_secret")

        raw_body = await request.body()
        headers = self._webhook_headers(request.headers)

        try:
            verified_payload = Webhook(secret).verify(raw_body, headers)
            return self._to_event(verified_payload)
        except ClerkWebhookVerificationError:
            raise
        except WebhookVerificationError as exc:
            raise ClerkWebhookVerificationError(
                reason="signature_verification_failed",
                safe_detail=str(exc),
            ) from exc
        except (ValidationError, TypeError, ValueError) as exc:
            raise ClerkWebhookVerificationError(reason="payload_parse_failed") from exc
        except Exception as exc:
            raise ClerkWebhookVerificationError(reason="unexpected_verification_error") from exc

    def _webhook_secret(self) -> str | None:
        secret = self.settings.clerk_webhook_secret
        if secret is None:
            return None
        value = secret.get_secret_value().strip()
        return value or None

    @classmethod
    def _webhook_headers(cls, headers: Mapping[str, str]) -> dict[str, str]:
        return {
            header_name: headers[header_name]
            for header_name in cls._SVIX_HEADER_NAMES
            if header_name in headers
        }

    @classmethod
    def _to_event(cls, payload: Any) -> ClerkWebhookEvent:
        if not isinstance(payload, Mapping):
            raise ClerkWebhookVerificationError(reason="payload_not_mapping")

        event_type = cls._non_blank_string(payload.get("type"))
        if event_type not in cls._SUPPORTED_EVENT_TYPES:
            raise ClerkWebhookVerificationError(reason="unsupported_event_type")

        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise ClerkWebhookVerificationError(reason="missing_event_data")

        event_id = cls._non_blank_string(payload.get("id"))
        clerk_user_id = cls._non_blank_string(data.get("id"))
        if event_id is None or clerk_user_id is None:
            raise ClerkWebhookVerificationError(reason="missing_event_or_user_id")

        return ClerkWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            clerk_user_id=clerk_user_id,
            primary_email=cls._primary_email(data),
            display_name=cls._display_name(data),
            avatar_url=cls._non_blank_string(data.get("image_url")),
        )

    @staticmethod
    def _non_blank_string(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value
        return None

    @classmethod
    def _primary_email(cls, data: Mapping[str, object]) -> str | None:
        direct_email = cls._non_blank_string(data.get("email"))
        if direct_email is not None:
            return direct_email

        email_addresses = data.get("email_addresses")
        if not isinstance(email_addresses, list):
            return None

        primary_email_address_id = cls._non_blank_string(data.get("primary_email_address_id"))
        fallback_email: str | None = None

        for item in email_addresses:
            if not isinstance(item, Mapping):
                continue

            email = cls._non_blank_string(item.get("email_address"))
            if email is None:
                continue

            if fallback_email is None:
                fallback_email = email

            email_id = cls._non_blank_string(item.get("id"))
            if primary_email_address_id is not None and email_id == primary_email_address_id:
                return email

        return fallback_email

    @classmethod
    def _display_name(cls, data: Mapping[str, object]) -> str | None:
        names = [
            name
            for name in (
                cls._non_blank_string(data.get("first_name")),
                cls._non_blank_string(data.get("last_name")),
            )
            if name is not None
        ]
        if names:
            return " ".join(names)

        return cls._non_blank_string(data.get("username"))

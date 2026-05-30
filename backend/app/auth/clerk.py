from __future__ import annotations

from collections.abc import Mapping

from clerk_backend_api.security import authenticate_request
from clerk_backend_api.security.types import (
    AuthenticateRequestOptions,
    AuthStatus,
    RequestState,
)
from fastapi import Request

from app.auth.types import ClerkSessionClaims, ClerkSessionVerificationError
from app.core.config import Settings, get_settings


class ClerkSessionVerifier:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def verify_request(self, request: Request) -> ClerkSessionClaims:
        if not self._has_bearer_token(request.headers):
            raise ClerkSessionVerificationError()

        secret_key = self._secret_key()
        if secret_key is None:
            raise ClerkSessionVerificationError()

        options = AuthenticateRequestOptions(
            secret_key=secret_key,
            authorized_parties=self.settings.clerk_authorized_party_list or None,
        )

        try:
            state = authenticate_request(request, options)
        except Exception as exc:
            raise ClerkSessionVerificationError() from exc

        if state.status != AuthStatus.SIGNED_IN:
            raise ClerkSessionVerificationError()

        payload = self._payload(state)
        clerk_user_id = self._string_claim(payload, "sub")
        if clerk_user_id is None:
            raise ClerkSessionVerificationError()

        return ClerkSessionClaims(
            clerk_user_id=clerk_user_id,
            email=self._first_string_claim(payload, ("email", "primary_email")),
            display_name=self._display_name(payload),
            avatar_url=self._first_string_claim(payload, ("avatar_url", "image_url", "picture")),
        )

    def _secret_key(self) -> str | None:
        secret = self.settings.clerk_secret_key
        if secret is None:
            return None
        value = secret.get_secret_value().strip()
        return value or None

    @staticmethod
    def _has_bearer_token(headers: Mapping[str, str]) -> bool:
        authorization = headers.get("authorization")
        if authorization is None:
            return False
        scheme, separator, token = authorization.partition(" ")
        return bool(separator and scheme.lower() == "bearer" and token.strip())

    @staticmethod
    def _payload(state: RequestState) -> Mapping[str, object]:
        payload = state.payload
        if not isinstance(payload, dict):
            raise ClerkSessionVerificationError()
        return payload

    @staticmethod
    def _string_claim(payload: Mapping[str, object], key: str) -> str | None:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
        return None

    @classmethod
    def _first_string_claim(
        cls,
        payload: Mapping[str, object],
        keys: tuple[str, ...],
    ) -> str | None:
        for key in keys:
            value = cls._string_claim(payload, key)
            if value is not None:
                return value
        return None

    @classmethod
    def _display_name(cls, payload: Mapping[str, object]) -> str | None:
        direct_name = cls._first_string_claim(payload, ("name", "display_name", "full_name"))
        if direct_name is not None:
            return direct_name

        names = [
            name
            for name in (
                cls._string_claim(payload, "first_name"),
                cls._string_claim(payload, "last_name"),
            )
            if name is not None
        ]
        return " ".join(names) or None

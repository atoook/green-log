from __future__ import annotations

from collections.abc import Mapping

from fastapi import Request
from fastapi.routing import APIRoute
from sqlmodel import Session, select

from app.auth.dependencies import get_clerk_session_verifier
from app.auth.types import ClerkSessionClaims, ClerkSessionVerificationError
from app.auth.webhooks import ClerkWebhookVerificationError
from app.main import app
from app.models.plant import Plant
from app.models.user import User
from app.routers.webhooks import get_clerk_webhook_verifier


class StubSessionVerifier:
    def __init__(self, claims_by_token: Mapping[str, ClerkSessionClaims]) -> None:
        self.claims_by_token = claims_by_token

    def verify_request(self, request: Request) -> ClerkSessionClaims:
        authorization = request.headers.get("authorization", "")
        _, _, token = authorization.partition(" ")
        try:
            return self.claims_by_token[token]
        except KeyError as exc:
            raise ClerkSessionVerificationError() from exc


class RejectingWebhookVerifier:
    async def verify_request(self, request: Request):
        raise ClerkWebhookVerificationError()


def test_main_app_registers_webhook_and_protected_plant_care_routers():
    routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    expected_watering_routes = {
        ("GET", "/care/today"),
        ("GET", "/plants/{plant_id}/watering"),
        ("POST", "/plants/{plant_id}/watering-records"),
    }
    openapi_watering_routes = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/care") or "watering" in path
        for method in operations
    }

    assert {
        ("GET", "/plants"),
        ("POST", "/plants"),
        ("GET", "/plants/{plant_id}"),
        ("POST", "/webhooks/clerk"),
    }.union(expected_watering_routes).issubset(routes)
    assert openapi_watering_routes == expected_watering_routes


def test_app_level_auth_error_contract_is_401_and_secret_safe(api_client):
    response = api_client.get(
        "/plants",
        headers={"Authorization": "Bearer leaked-session-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert response.headers["www-authenticate"] == "Bearer"
    assert "leaked-session-token" not in response.text


def test_app_level_disabled_user_contract_is_403_and_stops_data_access(
    api_client,
    test_engine,
):
    with Session(test_engine) as session:
        session.add(
            User(
                id="internal-disabled-user",
                clerk_user_id="clerk-disabled-user",
                status="disabled",
            )
        )
        session.commit()

    app.dependency_overrides[get_clerk_session_verifier] = lambda: StubSessionVerifier(
        {
            "disabled-token": ClerkSessionClaims(
                clerk_user_id="clerk-disabled-user",
                email="disabled@example.com",
            )
        }
    )

    response = api_client.get(
        "/plants",
        headers={"Authorization": "Bearer disabled-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}
    assert "clerk-disabled-user" not in response.text
    assert "internal-disabled-user" not in response.text

    with Session(test_engine) as session:
        assert session.exec(select(Plant)).all() == []


def test_app_level_other_owner_detail_contract_is_404_and_hides_existence(
    api_client,
):
    app.dependency_overrides[get_clerk_session_verifier] = lambda: StubSessionVerifier(
        {
            "user-a-token": ClerkSessionClaims(clerk_user_id="clerk-user-a"),
            "user-b-token": ClerkSessionClaims(clerk_user_id="clerk-user-b"),
        }
    )

    created_response = api_client.post(
        "/plants",
        headers={"Authorization": "Bearer user-a-token"},
        json={"name": "Aの植物", "wateringCycleDays": 7},
    )
    assert created_response.status_code == 201

    response = api_client.get(
        f"/plants/{created_response.json()['id']}",
        headers={"Authorization": "Bearer user-b-token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Plant not found"}
    assert "clerk-user-a" not in response.text
    assert "clerk-user-b" not in response.text


def test_app_level_plant_validation_contract_omits_raw_input(api_client):
    app.dependency_overrides[get_clerk_session_verifier] = lambda: StubSessionVerifier(
        {"valid-token": ClerkSessionClaims(clerk_user_id="clerk-valid-user")}
    )

    response = api_client.post(
        "/plants",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "ポトス",
            "ownerUserId": "internal-other-user",
            "secret": "sk_test_should_not_echo",
        },
    )

    assert response.status_code == 422
    assert "detail" in response.json()
    assert "input" not in response.text
    assert "ownerUserId" not in response.text
    assert "internal-other-user" not in response.text
    assert "sk_test_should_not_echo" not in response.text


def test_app_level_webhook_error_contract_is_400_and_secret_safe(api_client):
    app.dependency_overrides[
        get_clerk_webhook_verifier
    ] = lambda: RejectingWebhookVerifier()

    response = api_client.post(
        "/webhooks/clerk",
        json={
            "id": "evt_secret",
            "type": "user.created",
            "data": {"id": "user_secret"},
        },
        headers={"svix-signature": "v1,secret-signature"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid webhook"}
    assert "secret-signature" not in response.text
    assert "user_secret" not in response.text

from __future__ import annotations

from collections.abc import Mapping

from fastapi import Request
from fastapi.routing import APIRoute
from sqlmodel import Session, select

from app.auth.dependencies import get_clerk_session_verifier
from app.auth.types import ClerkSessionClaims, ClerkSessionVerificationError
from app.main import app
from app.models.plant import Plant
from app.models.user import User


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


def test_owner_model_request_flow_creates_reuses_and_scopes_application_user(
    api_client,
    test_engine,
):
    app.dependency_overrides[get_clerk_session_verifier] = lambda: StubSessionVerifier(
        {
            "user-a-token": ClerkSessionClaims(
                clerk_user_id="clerk-user-a",
                email="a@example.com",
            ),
            "user-b-token": ClerkSessionClaims(
                clerk_user_id="clerk-user-b",
                email="b@example.com",
            ),
        }
    )

    first_request_response = api_client.get("/plants", headers=auth("user-a-token"))

    assert first_request_response.status_code == 200
    assert first_request_response.json() == []
    user_a = get_user_by_clerk_id(test_engine, "clerk-user-a")
    assert user_a.id != "clerk-user-a"
    assert count_users(test_engine) == 1

    created_response = api_client.post(
        "/plants",
        headers=auth("user-a-token"),
        json={
            "name": "Aのフィカス",
            "wateringCycleDays": 7,
            "ownerUserId": "clerk-user-b",
            "userId": "clerk-user-b",
            "clerkUserId": "clerk-user-b",
        },
    )

    assert created_response.status_code == 201
    created = created_response.json()
    assert_no_owner_fields(created)
    assert count_users(test_engine) == 1

    plant_snapshot = get_plant_snapshot(test_engine, created["id"])
    assert plant_snapshot["owner_user_id"] == user_a.id
    assert plant_snapshot["owner_user_id"] != "clerk-user-a"
    assert plant_snapshot["owner_user_id"] != "clerk-user-b"

    own_detail_response = api_client.get(
        f"/plants/{created['id']}",
        headers=auth("user-a-token"),
    )
    own_list_response = api_client.get("/plants", headers=auth("user-a-token"))

    assert own_detail_response.status_code == 200
    assert own_detail_response.json()["id"] == created["id"]
    assert_no_owner_fields(own_detail_response.json())
    assert own_list_response.status_code == 200
    assert [plant["id"] for plant in own_list_response.json()] == [created["id"]]
    for plant in own_list_response.json():
        assert_no_owner_fields(plant)

    other_list_response = api_client.get("/plants", headers=auth("user-b-token"))
    other_detail_response = api_client.get(
        f"/plants/{created['id']}",
        headers=auth("user-b-token"),
    )
    other_update_response = api_client.patch(
        f"/plants/{created['id']}",
        headers=auth("user-b-token"),
        json={"name": "Bによる上書き"},
    )
    other_delete_response = api_client.delete(
        f"/plants/{created['id']}",
        headers=auth("user-b-token"),
    )

    assert other_list_response.status_code == 200
    assert other_list_response.json() == []
    assert other_detail_response.status_code == 404
    assert other_update_response.status_code == 405
    assert other_delete_response.status_code == 405
    assert count_users(test_engine) == 2
    assert get_plant_snapshot(test_engine, created["id"]) == plant_snapshot


def test_owner_model_gate_keeps_adjacent_domain_routes_out_of_scope():
    routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    paths = {path for _, path in routes}
    watering_mvp_routes = {
        ("GET", "/care/today"),
        ("GET", "/care/watering-heatmap"),
        ("GET", "/plants/{plant_id}/watering"),
        ("POST", "/plants/{plant_id}/watering-records"),
    }
    watering_route_surface = {
        (method, path)
        for method, path in routes
        if path.startswith("/care") or "watering" in path
    }

    assert {("GET", "/plants"), ("POST", "/plants"), ("GET", "/plants/{plant_id}")}.issubset(
        routes
    )
    assert watering_route_surface == watering_mvp_routes
    assert ("PATCH", "/plants/{plant_id}") not in routes
    assert ("DELETE", "/plants/{plant_id}") not in routes
    assert not any(
        forbidden in path
        for path in paths
        for forbidden in (
            "notification",
            "permission",
            "skip",
            "defer",
            "growth",
            "photo",
            "share",
            "care-type",
            "fertilizer",
            "pruning",
            "repotting",
            "streak",
            "ranking",
            "calendar",
            "weekly",
            "monthly",
            "summary",
            "recommend",
        )
    )


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def get_user_by_clerk_id(engine, clerk_user_id: str) -> User:
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.clerk_user_id == clerk_user_id)
        ).one()
        return User.model_validate(user)


def count_users(engine) -> int:
    with Session(engine) as session:
        return len(session.exec(select(User)).all())


def get_plant_snapshot(engine, plant_id: int) -> dict[str, object]:
    with Session(engine) as session:
        plant = session.get(Plant, plant_id)
        assert plant is not None
        return {
            "owner_user_id": plant.owner_user_id,
            "name": plant.name,
            "watering_cycle_days": plant.watering_cycle_days,
            "updated_at": plant.updated_at,
        }


def assert_no_owner_fields(payload: dict) -> None:
    assert "owner" not in payload
    assert "ownerUserId" not in payload
    assert "owner_user_id" not in payload
    assert "userId" not in payload
    assert "clerkUserId" not in payload

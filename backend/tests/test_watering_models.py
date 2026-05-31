from datetime import date, datetime, timezone

from sqlmodel import SQLModel

from app.models import WateringRecord
from app.schemas.watering import (
    PlantWateringDetailRead,
    PlantWateringStateRead,
    TodayCareItemRead,
    TodayCareRead,
    WateringHeatmapDayRead,
    WateringHeatmapPlantRead,
    WateringHeatmapRead,
    WateringPlantSummaryRead,
    WateringRecordCreateResult,
    WateringRecordRead,
)


def test_watering_record_model_matches_migration_shape_and_metadata():
    assert SQLModel.metadata.tables["watering_records"] is WateringRecord.__table__

    columns = WateringRecord.__table__.c
    assert columns.id.primary_key
    assert not columns.owner_user_id.nullable
    assert not columns.plant_id.nullable
    assert not columns.watered_at.nullable
    assert not columns.created_at.nullable

    assert {foreign_key.column.table.name for foreign_key in columns.owner_user_id.foreign_keys} == {
        "users"
    }
    assert {foreign_key.column.table.name for foreign_key in columns.plant_id.foreign_keys} == {
        "plants"
    }

    indexes = {
        index.name: [column.name for column in index.columns]
        for index in WateringRecord.__table__.indexes
    }
    assert indexes["ix_watering_records_owner_user_id_plant_id_watered_at"] == [
        "owner_user_id",
        "plant_id",
        "watered_at",
    ]
    assert indexes["ix_watering_records_owner_user_id_watered_at"] == [
        "owner_user_id",
        "watered_at",
    ]
    assert "note" not in columns
    assert "care_type" not in columns
    assert "next_watering_date" not in columns


def test_watering_detail_schema_represents_unrecorded_plant_without_owner_fields():
    detail = PlantWateringDetailRead(
        plant_id=1,
        last_watered_at=None,
        next_watering_date=None,
        is_due_today=True,
        due_status="unrecorded",
        history=[],
    )

    payload = detail.model_dump(mode="json", by_alias=True)

    assert payload == {
        "plantId": 1,
        "lastWateredAt": None,
        "nextWateringDate": None,
        "isDueToday": True,
        "dueStatus": "unrecorded",
        "history": [],
    }
    assert "ownerUserId" not in payload
    assert "owner_user_id" not in payload


def test_today_care_schema_serializes_due_item_with_camel_case_and_utc_datetime():
    item = TodayCareItemRead(
        plant_id=2,
        last_watered_at=datetime(2026, 5, 23, 9, 30),
        next_watering_date=date(2026, 5, 30),
        is_due_today=True,
        due_status="due_today",
        plant=WateringPlantSummaryRead(
            id=2,
            name="リビングのモンステラ",
            image_url=None,
            watering_cycle_days=7,
        ),
    )
    today_care = TodayCareRead(today=date(2026, 5, 30), items=[item])

    payload = today_care.model_dump(mode="json", by_alias=True)

    assert payload["today"] == "2026-05-30"
    assert payload["items"][0]["lastWateredAt"] == "2026-05-23T09:30:00Z"
    assert payload["items"][0]["nextWateringDate"] == "2026-05-30"
    assert payload["items"][0]["dueStatus"] == "due_today"
    assert payload["items"][0]["plant"] == {
        "id": 2,
        "name": "リビングのモンステラ",
        "imageUrl": None,
        "wateringCycleDays": 7,
    }
    assert "ownerUserId" not in payload["items"][0]
    assert "ownerUserId" not in payload["items"][0]["plant"]


def test_create_result_schema_represents_record_and_history_without_extra_care_types():
    watered_at = datetime(2026, 5, 30, 8, 0, tzinfo=timezone.utc)
    created_at = datetime(2026, 5, 30, 8, 0, 1, tzinfo=timezone.utc)
    record = WateringRecordRead(
        id=10,
        plant_id=3,
        watered_at=watered_at,
        created_at=created_at,
    )
    state = PlantWateringDetailRead(
        plant_id=3,
        last_watered_at=watered_at,
        next_watering_date=date(2026, 6, 6),
        is_due_today=False,
        due_status=None,
        history=[record],
    )
    result = WateringRecordCreateResult(record=record, state=state)

    payload = result.model_dump(mode="json", by_alias=True)

    assert payload["record"] == {
        "id": 10,
        "plantId": 3,
        "wateredAt": "2026-05-30T08:00:00Z",
        "createdAt": "2026-05-30T08:00:01Z",
    }
    assert payload["state"]["lastWateredAt"] == "2026-05-30T08:00:00Z"
    assert payload["state"]["nextWateringDate"] == "2026-06-06"
    assert payload["state"]["history"][0] == payload["record"]
    dumped_text = str(payload)
    assert "owner" not in dumped_text
    assert "careType" not in dumped_text
    assert "note" not in dumped_text


def test_watering_schemas_accept_existing_camel_case_validation_aliases():
    state = PlantWateringStateRead.model_validate(
        {
            "plantId": 4,
            "lastWateredAt": None,
            "nextWateringDate": None,
            "isDueToday": True,
            "dueStatus": "unrecorded",
        }
    )

    assert state.plant_id == 4
    assert state.last_watered_at is None
    assert state.next_watering_date is None
    assert state.is_due_today is True
    assert state.due_status == "unrecorded"


def test_watering_heatmap_schema_serializes_empty_day_with_camel_case_and_no_owner_fields():
    heatmap = WateringHeatmapRead(
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 1),
        days=[
            WateringHeatmapDayRead(
                date=date(2026, 5, 1),
                plant_count=0,
                level=0,
                plants=[],
            )
        ],
    )

    payload = heatmap.model_dump(mode="json", by_alias=True)

    assert payload == {
        "startDate": "2026-05-01",
        "endDate": "2026-05-01",
        "days": [
            {
                "date": "2026-05-01",
                "plantCount": 0,
                "level": 0,
                "plants": [],
            }
        ],
    }
    dumped_text = str(payload)
    assert "owner" not in dumped_text
    assert "auth" not in dumped_text
    assert "ownerUserId" not in dumped_text


def test_watering_heatmap_schema_represents_multiple_current_plant_names():
    day = WateringHeatmapDayRead(
        date=date(2026, 5, 2),
        plant_count=2,
        level=2,
        plants=[
            WateringHeatmapPlantRead(plant_id=10, name="窓辺のポトス"),
            WateringHeatmapPlantRead(plant_id=11, name="リビングのモンステラ"),
        ],
    )

    payload = day.model_dump(mode="json", by_alias=True)

    assert payload == {
        "date": "2026-05-02",
        "plantCount": 2,
        "level": 2,
        "plants": [
            {"plantId": 10, "name": "窓辺のポトス"},
            {"plantId": 11, "name": "リビングのモンステラ"},
        ],
    }
    assert [plant["name"] for plant in payload["plants"]] == [
        "窓辺のポトス",
        "リビングのモンステラ",
    ]


def test_watering_heatmap_schema_accepts_camel_case_and_rejects_invalid_level():
    heatmap = WateringHeatmapRead.model_validate(
        {
            "startDate": "2026-05-01",
            "endDate": "2026-05-02",
            "days": [
                {
                    "date": "2026-05-02",
                    "plantCount": 1,
                    "level": 1,
                    "plants": [{"plantId": 12, "name": "寝室のフィカス"}],
                }
            ],
        }
    )

    assert heatmap.start_date == date(2026, 5, 1)
    assert heatmap.end_date == date(2026, 5, 2)
    assert heatmap.days[0].plant_count == 1
    assert heatmap.days[0].plants[0].plant_id == 12
    assert heatmap.days[0].plants[0].name == "寝室のフィカス"

    try:
        WateringHeatmapDayRead(
            date=date(2026, 5, 3),
            plant_count=5,
            level=5,
            plants=[],
        )
    except ValueError as exc:
        assert "level" in str(exc)
    else:
        raise AssertionError("level must be constrained to 0-4")

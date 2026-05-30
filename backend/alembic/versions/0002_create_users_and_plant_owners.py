"""create users and plant owners

Revision ID: 0002_create_users_and_plant_owners
Revises: 0001_create_plants
Create Date: 2026-05-30 00:00:00.000000
"""

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy import text

from app.core.config import get_settings

revision: str = "0002_create_users_and_plant_owners"
down_revision: str | None = "0001_create_plants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _legacy_owner_backfill_user_id() -> str | None:
    settings = context.get_context().config.attributes.get("settings")
    if settings is None:
        settings = get_settings()
    return settings.legacy_owner_backfill_user_id


def _plant_count() -> int:
    bind = op.get_bind()
    return int(bind.execute(text("SELECT COUNT(*) FROM plants")).scalar_one())


def _create_legacy_backfill_user(owner_user_id: str) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    op.execute(
        text(
            """
            INSERT OR IGNORE INTO users (
                id, clerk_user_id, status, primary_email, display_name, avatar_url, created_at, updated_at
            ) VALUES (
                :id, :clerk_user_id, 'active', NULL, NULL, NULL, :created_at, :updated_at
            )
            """
        ).bindparams(
            id=owner_user_id,
            clerk_user_id=f"legacy-backfill:{owner_user_id}",
            created_at=now,
            updated_at=now,
        )
    )


def upgrade() -> None:
    plant_count = _plant_count()
    legacy_owner_id = _legacy_owner_backfill_user_id()
    if plant_count > 0 and not legacy_owner_id:
        raise RuntimeError(
            "LEGACY_OWNER_BACKFILL_USER_ID is required before migrating existing plants"
        )

    op.create_table(
        "users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("clerk_user_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("primary_email", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'deleted')",
            name="ck_users_status_allowed",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ux_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)

    op.add_column("plants", sa.Column("owner_user_id", sa.Text(), nullable=True))

    if legacy_owner_id:
        _create_legacy_backfill_user(legacy_owner_id)
        op.execute(
            text("UPDATE plants SET owner_user_id = :owner_user_id WHERE owner_user_id IS NULL")
            .bindparams(owner_user_id=legacy_owner_id)
        )

    with op.batch_alter_table("plants", recreate="always") as batch_op:
        batch_op.alter_column("owner_user_id", existing_type=sa.Text(), nullable=False)
        batch_op.create_foreign_key(
            "fk_plants_owner_user_id_users",
            "users",
            ["owner_user_id"],
            ["id"],
        )
        batch_op.create_index("ix_plants_owner_user_id_id", ["owner_user_id", "id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("plants", recreate="always") as batch_op:
        batch_op.drop_index("ix_plants_owner_user_id_id")
        batch_op.drop_constraint("fk_plants_owner_user_id_users", type_="foreignkey")
        batch_op.drop_column("owner_user_id")

    op.drop_index("ux_users_clerk_user_id", table_name="users")
    op.drop_table("users")

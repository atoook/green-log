"""create watering records

Revision ID: 0003_create_watering_records
Revises: 0002_create_users_and_plant_owners
Create Date: 2026-05-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_create_watering_records"
down_revision: str | None = "0002_create_users_and_plant_owners"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plants", sa.Column("last_watered_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_plants_owner_user_id_last_watered_at",
        "plants",
        ["owner_user_id", "last_watered_at"],
        unique=False,
    )

    op.create_table(
        "watering_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Text(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("watered_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_watering_records_owner_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.id"],
            name="fk_watering_records_plant_id_plants",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_watering_records_owner_user_id_plant_id_watered_at",
        "watering_records",
        ["owner_user_id", "plant_id", "watered_at"],
        unique=False,
    )
    op.create_index(
        "ix_watering_records_owner_user_id_watered_at",
        "watering_records",
        ["owner_user_id", "watered_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_watering_records_owner_user_id_watered_at",
        table_name="watering_records",
    )
    op.drop_index(
        "ix_watering_records_owner_user_id_plant_id_watered_at",
        table_name="watering_records",
    )
    op.drop_table("watering_records")

    op.drop_index("ix_plants_owner_user_id_last_watered_at", table_name="plants")
    with op.batch_alter_table("plants", recreate="always") as batch_op:
        batch_op.drop_column("last_watered_at")

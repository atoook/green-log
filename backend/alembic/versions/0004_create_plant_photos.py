"""create plant photos

Revision ID: 0004_create_plant_photos
Revises: 0003_create_watering_records
Create Date: 2026-06-01 12:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_create_plant_photos"
down_revision: str | None = "0003_create_watering_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plants", sa.Column("cover_photo_id", sa.Integer(), nullable=True))
    op.drop_column("plants", "image_url")
    op.create_index(
        "ix_plants_cover_photo_id",
        "plants",
        ["cover_photo_id"],
        unique=False,
    )

    op.create_table(
        "plant_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Text(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("taken_date", sa.Date(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_plant_photos_owner_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["plant_id"],
            ["plants.id"],
            name="fk_plant_photos_plant_id_plants",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_plant_photos_owner_user_id_plant_id_created_at",
        "plant_photos",
        ["owner_user_id", "plant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_plant_photos_owner_user_id_plant_id_taken_date",
        "plant_photos",
        ["owner_user_id", "plant_id", "taken_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_plants_cover_photo_id", table_name="plants")

    op.drop_index(
        "ix_plant_photos_owner_user_id_plant_id_taken_date",
        table_name="plant_photos",
    )
    op.drop_index(
        "ix_plant_photos_owner_user_id_plant_id_created_at",
        table_name="plant_photos",
    )
    op.drop_table("plant_photos")

    op.add_column("plants", sa.Column("image_url", sa.Text(), nullable=True))
    op.drop_column("plants", "cover_photo_id")

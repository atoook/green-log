"""create plants

Revision ID: 0001_create_plants
Revises:
Create Date: 2026-05-28 13:39:39.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_create_plants"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("acquired_date", sa.Date(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("watering_cycle_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("watering_cycle_days >= 1", name="ck_plants_watering_cycle_days_min"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plants_name", "plants", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_plants_name", table_name="plants")
    op.drop_table("plants")

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'deleted')",
            name="ck_users_status_allowed",
        ),
    )

    id: str = Field(sa_column=sa.Column(sa.Text(), primary_key=True, nullable=False))
    clerk_user_id: str = Field(sa_column=sa.Column(sa.Text(), unique=True, nullable=False))
    status: str = Field(
        default="active",
        sa_column=sa.Column(sa.Text(), nullable=False, server_default="active"),
    )
    primary_email: str | None = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True))
    display_name: str | None = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True))
    avatar_url: str | None = Field(default=None, sa_column=sa.Column(sa.Text(), nullable=True))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)

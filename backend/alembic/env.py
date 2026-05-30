from logging.config import fileConfig

from alembic import context
from sqlmodel import SQLModel

from app.core.config import get_settings
from app.db.engine import create_database_engine, normalize_database_url
from app.models.plant import Plant  # noqa: F401
from app.models.user import User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_migration_settings():
    return config.attributes.get("settings") or get_settings()


def get_url() -> str:
    return normalize_database_url(get_migration_settings().resolved_database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_database_engine(get_migration_settings())

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

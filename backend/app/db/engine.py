from sqlalchemy import Engine, create_engine

from app.core.config import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> Engine:
    resolved = settings or get_settings()
    database_url = resolved.resolved_database_url
    connect_args: dict[str, object] = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    if database_url.startswith("sqlite+libsql") and resolved.turso_auth_token:
        connect_args["auth_token"] = resolved.turso_auth_token

    return create_engine(database_url, connect_args=connect_args)


engine = create_database_engine()

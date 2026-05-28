from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("libsql://"):
        database_url = f"sqlite+libsql://{database_url.removeprefix('libsql://')}"

    if database_url.startswith("sqlite+libsql://"):
        url = make_url(database_url)
        if url.host and "secure" not in url.query:
            database_url = f"{database_url}{'&' if '?' in database_url else '?'}secure=true"

    return database_url


def create_database_engine(settings: Settings | None = None) -> Engine:
    resolved = settings or get_settings()
    database_url = normalize_database_url(resolved.resolved_database_url)
    connect_args: dict[str, object] = {}

    if database_url.startswith("sqlite") and not database_url.startswith("sqlite+libsql"):
        connect_args["check_same_thread"] = False

    if database_url.startswith("sqlite+libsql") and resolved.turso_auth_token:
        connect_args["auth_token"] = resolved.turso_auth_token

    return create_engine(database_url, connect_args=connect_args)


engine = create_database_engine()

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings

LIBSQL_URL_PREFIX = "libsql://"
SQLITE_LIBSQL_URL_PREFIX = "sqlite+libsql://"
SQLITE_URL_PREFIX = "sqlite"


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith(LIBSQL_URL_PREFIX):
        database_url = (
            f"{SQLITE_LIBSQL_URL_PREFIX}{database_url.removeprefix(LIBSQL_URL_PREFIX)}"
        )

    if database_url.startswith(SQLITE_LIBSQL_URL_PREFIX):
        url = make_url(database_url)
        if url.host and "secure" not in url.query:
            database_url = f"{database_url}{'&' if '?' in database_url else '?'}secure=true"

    return database_url


def create_database_engine(settings: Settings | None = None) -> Engine:
    resolved = settings or get_settings()
    database_url = normalize_database_url(resolved.resolved_database_url)
    connect_args: dict[str, object] = {}
    engine_options: dict[str, object] = {}

    if database_url.startswith(SQLITE_URL_PREFIX) and not database_url.startswith(
        SQLITE_LIBSQL_URL_PREFIX
    ):
        connect_args["check_same_thread"] = False

    if database_url.startswith(SQLITE_LIBSQL_URL_PREFIX) and resolved.turso_auth_token_value:
        connect_args["auth_token"] = resolved.turso_auth_token_value

    if database_url.startswith(SQLITE_LIBSQL_URL_PREFIX):
        engine_options["poolclass"] = NullPool

    return create_engine(database_url, connect_args=connect_args, **engine_options)


engine = create_database_engine()

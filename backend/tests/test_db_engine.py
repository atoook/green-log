from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.db.engine import (
    create_database_engine,
    normalize_database_url,
)


def test_normalize_database_url_converts_turso_libsql_url_to_sqlalchemy_dialect():
    assert normalize_database_url("libsql://green-log.example.turso.io") == (
        "sqlite+libsql://green-log.example.turso.io?secure=true"
    )


def test_normalize_database_url_preserves_existing_secure_query():
    assert normalize_database_url(
        "sqlite+libsql://green-log.example.turso.io?secure=false"
    ) == "sqlite+libsql://green-log.example.turso.io?secure=false"


def test_create_database_engine_disables_pooling_for_turso_libsql():
    engine = create_database_engine(
        Settings(
            turso_database_url="libsql://green-log.example.turso.io",
            turso_auth_token="dummy-token",
        )
    )

    assert isinstance(engine.pool, NullPool)


def test_create_database_engine_disables_pooling_for_local_libsql():
    engine = create_database_engine(
        Settings(
            database_url="sqlite+libsql:///private/tmp/green-log-libsql-engine-test.db",
            turso_database_url=None,
            turso_auth_token=None,
        )
    )

    assert isinstance(engine.pool, NullPool)


def test_create_database_engine_keeps_default_pool_for_local_sqlite():
    engine = create_database_engine(
        Settings(
            database_url="sqlite:////private/tmp/green-log-engine-test.db",
            turso_database_url=None,
            turso_auth_token=None,
        )
    )

    assert not isinstance(engine.pool, NullPool)

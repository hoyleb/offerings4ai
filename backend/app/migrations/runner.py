from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Connection, Engine, inspect, text

from app.db import Base

SCHEMA_MIGRATION_LOCK_ID = 9_416_031
SCHEMA_MIGRATIONS_TABLE = "schema_migrations"


@dataclass(frozen=True)
class Migration:
    revision: str
    description: str
    upgrade: Callable[[Connection], None]


def _upgrade_initial_schema(connection: Connection) -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=connection)


def _upgrade_email_verification_columns(connection: Connection) -> None:
    inspector = inspect(connection)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "email_verified_at" not in existing_columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP"))
        connection.execute(
            text("UPDATE users SET email_verified_at = created_at WHERE email_verified_at IS NULL")
        )
    if "email_verification_token_hash" not in existing_columns:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN email_verification_token_hash VARCHAR(64)")
        )
    if "email_verification_sent_at" not in existing_columns:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN email_verification_sent_at TIMESTAMP")
        )
    if "email_verification_expires_at" not in existing_columns:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN email_verification_expires_at TIMESTAMP")
        )


def _upgrade_password_reset_columns(connection: Connection) -> None:
    inspector = inspect(connection)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "password_reset_token_hash" not in existing_columns:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN password_reset_token_hash VARCHAR(64)")
        )
    if "password_reset_sent_at" not in existing_columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN password_reset_sent_at TIMESTAMP"))
    if "password_reset_expires_at" not in existing_columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN password_reset_expires_at TIMESTAMP"))


MIGRATIONS = (
    Migration(
        revision="20260308_0001_initial_schema",
        description="Create the initial Offering4AI schema.",
        upgrade=_upgrade_initial_schema,
    ),
    Migration(
        revision="20260310_0002_email_verification_columns",
        description="Backfill email verification fields onto existing user records.",
        upgrade=_upgrade_email_verification_columns,
    ),
    Migration(
        revision="20260328_0003_password_reset_columns",
        description="Add password reset fields onto existing user records.",
        upgrade=_upgrade_password_reset_columns,
    ),
)


def latest_revision() -> str:
    return MIGRATIONS[-1].revision


def apply_pending_migrations(engine: Engine) -> list[str]:
    applied_revisions: list[str] = []
    with engine.begin() as connection:
        _ensure_schema_migrations_table(connection)
        _lock_schema_migrations(connection)
        try:
            existing = _applied_revision_set(connection)
            for migration in MIGRATIONS:
                if migration.revision in existing:
                    continue
                migration.upgrade(connection)
                connection.execute(
                    text(
                        "INSERT INTO schema_migrations (revision, description, applied_at) "
                        "VALUES (:revision, :description, :applied_at)"
                    ),
                    {
                        "revision": migration.revision,
                        "description": migration.description,
                        "applied_at": datetime.now(UTC),
                    },
                )
                applied_revisions.append(migration.revision)
        finally:
            _unlock_schema_migrations(connection)
    return applied_revisions


def schema_is_current(engine: Engine) -> bool:
    with engine.begin() as connection:
        if not _schema_migrations_table_exists(connection):
            return False
        return _applied_revision_set(connection) == {migration.revision for migration in MIGRATIONS}


def reset_sqlite_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        Base.metadata.drop_all(bind=connection)
        connection.execute(text("DROP TABLE IF EXISTS schema_migrations"))


def _ensure_schema_migrations_table(connection: Connection) -> None:
    connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "revision VARCHAR(64) PRIMARY KEY, "
            "description VARCHAR(255) NOT NULL, "
            "applied_at TIMESTAMP NOT NULL"
            ")"
        )
    )


def _schema_migrations_table_exists(connection: Connection) -> bool:
    inspector = inspect(connection)
    return SCHEMA_MIGRATIONS_TABLE in inspector.get_table_names()


def _applied_revision_set(connection: Connection) -> set[str]:
    rows = connection.execute(text("SELECT revision FROM schema_migrations")).all()
    return {row[0] for row in rows}


def _lock_schema_migrations(connection: Connection) -> None:
    if connection.dialect.name == "postgresql":
        connection.execute(
            text("SELECT pg_advisory_lock(:lock_id)"),
            {"lock_id": SCHEMA_MIGRATION_LOCK_ID},
        )


def _unlock_schema_migrations(connection: Connection) -> None:
    if connection.dialect.name == "postgresql":
        connection.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": SCHEMA_MIGRATION_LOCK_ID},
        )

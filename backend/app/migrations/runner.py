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


def _upgrade_reviewed_status(connection: Connection) -> None:
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    if "ideas" not in existing_tables:
        return

    if connection.dialect.name == "postgresql":
        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM pg_type t
                        JOIN pg_enum e ON e.enumtypid = t.oid
                        WHERE t.typname = 'ideastatus' AND e.enumlabel = 'REJECTED'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM pg_type t
                        JOIN pg_enum e ON e.enumtypid = t.oid
                        WHERE t.typname = 'ideastatus' AND e.enumlabel = 'REVIEWED'
                    ) THEN
                        ALTER TYPE ideastatus RENAME VALUE 'REJECTED' TO 'REVIEWED';
                    END IF;
                END
                $$;
                """
            )
        )
        connection.execute(
            text(
                "UPDATE ideas SET status = CAST('REVIEWED' AS ideastatus) "
                "WHERE status::text = 'REJECTED'"
            )
        )
    else:
        connection.execute(
            text("UPDATE ideas SET status = 'REVIEWED' WHERE CAST(status AS TEXT) IN ('REJECTED', 'rejected')")
        )

    if "evaluations" in existing_tables:
        connection.execute(
            text(
                "UPDATE evaluations SET decision = 'reviewed' "
                "WHERE decision IN ('reject', 'rejected')"
            )
        )


def _reviewed_status_is_current(connection: Connection) -> bool:
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    if "ideas" not in existing_tables:
        return True

    if connection.dialect.name == "postgresql":
        has_reviewed_label = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_type t
                    JOIN pg_enum e ON e.enumtypid = t.oid
                    WHERE t.typname = 'ideastatus' AND e.enumlabel = 'REVIEWED'
                )
                """
            )
        ).scalar_one()
        if not has_reviewed_label:
            return False

    legacy_idea_status_exists = connection.execute(
        text("SELECT EXISTS (SELECT 1 FROM ideas WHERE CAST(status AS TEXT) IN ('REJECTED', 'rejected'))")
    ).scalar_one()
    if legacy_idea_status_exists:
        return False

    if "evaluations" not in existing_tables:
        return True

    legacy_decision_exists = connection.execute(
        text("SELECT EXISTS (SELECT 1 FROM evaluations WHERE decision IN ('reject', 'rejected'))")
    ).scalar_one()
    return not legacy_decision_exists


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
    Migration(
        revision="20260407_0004_reviewed_status",
        description="Rename low-score idea status from rejected to reviewed.",
        upgrade=_upgrade_reviewed_status,
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
            _upgrade_reviewed_status(connection)
        finally:
            _unlock_schema_migrations(connection)
    return applied_revisions


def schema_is_current(engine: Engine) -> bool:
    with engine.begin() as connection:
        if not _schema_migrations_table_exists(connection):
            return False
        return _applied_revision_set(connection) == {
            migration.revision for migration in MIGRATIONS
        } and _reviewed_status_is_current(connection)


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

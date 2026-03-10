from collections.abc import Generator

from sqlalchemy import Connection, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

SCHEMA_INIT_LOCK_ID = 4_204_208


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine_kwargs: dict[str, object] = {}
if settings.database_url.startswith("postgresql+psycopg"):
    engine_kwargs["connect_args"] = {"prepare_threshold": None}

engine = create_engine(settings.database_url, future=True, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_db_and_tables() -> None:
    """Purpose: Create the application schema once per deployment.

    Args:
        None.

    Returns:
        None.

    Raises:
        Any database exception raised by the underlying engine connection.
    """

    from app import models  # noqa: F401

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text("SELECT pg_advisory_lock(:lock_id)"),
                {"lock_id": SCHEMA_INIT_LOCK_ID},
            )
        try:
            Base.metadata.create_all(bind=connection)
            _ensure_runtime_user_columns(connection)
        finally:
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": SCHEMA_INIT_LOCK_ID},
                )


def _ensure_runtime_user_columns(connection: Connection) -> None:
    """Purpose: Backfill runtime-managed columns until proper migrations exist.

    Args:
        connection: Open SQLAlchemy connection inside the schema init transaction.

    Returns:
        None.
    """

    inspector = inspect(connection)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "email_verified_at" not in existing_columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP"))
        # Existing creators predate verification, so treat them as already trusted.
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

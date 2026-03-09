from collections.abc import Generator

from sqlalchemy import create_engine, text
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
        finally:
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": SCHEMA_INIT_LOCK_ID},
                )

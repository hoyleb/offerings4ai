from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


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


def ensure_current_schema() -> None:
    """Purpose: Fail fast when the database schema has not been migrated.

    Args:
        None.

    Returns:
        None.

    Raises:
        RuntimeError: Raised when the schema is missing required migrations.
    """
    from app.migrations.runner import latest_revision, schema_is_current

    if schema_is_current(engine):
        return

    raise RuntimeError(
        "Database schema is outdated. Run `python -m app.migrations.cli upgrade` "
        f"until revision {latest_revision()} is applied before starting the API or worker."
    )

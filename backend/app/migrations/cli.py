from __future__ import annotations

import sys

from app.db import engine
from app.migrations.runner import apply_pending_migrations, latest_revision, schema_is_current


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    command = args[0] if args else "upgrade"

    if command == "upgrade":
        applied = apply_pending_migrations(engine)
        if applied:
            print(f"Applied migrations: {', '.join(applied)}")
        else:
            print(f"Schema already current at {latest_revision()}")
        return 0

    if command == "current":
        status = "current" if schema_is_current(engine) else "outdated"
        print(f"{status}:{latest_revision()}")
        return 0

    print(f"Unsupported migration command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

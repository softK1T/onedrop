"""Migration consistency check.

Compares the tables declared by the SQLAlchemy models with the tables that exist
in the migrated database. Any drift fails with a non-zero exit code, so CI
catches a model added without a migration.

Run with: `python scripts/check_migrations.py`
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from onedrop.config import get_settings
from onedrop.db import models  # noqa: F401  (imported so metadata is populated)
from onedrop.db.base import Base
from onedrop.db.session import dispose_engine, get_engine

ALEMBIC_TABLE = "alembic_version"


async def existing_tables() -> set[str]:
    engine = get_engine()
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        return {str(row[0]) for row in result.all()}


async def main() -> int:
    settings = get_settings()
    declared = set(Base.metadata.tables)
    try:
        present = await existing_tables()
    finally:
        await dispose_engine()

    has_alembic_table = ALEMBIC_TABLE in present
    present.discard(ALEMBIC_TABLE)
    missing = sorted(declared - present)
    extra = sorted(present - declared)

    print(f"environment: {settings.app_env}")
    print(f"declared tables: {len(declared)}")
    print(f"database tables: {len(present)}")

    if not has_alembic_table:
        print("alembic_version table is missing: migrations were not applied")
        return 1

    if missing:
        print("tables declared by models but missing in the database:")
        for name in missing:
            print(f"  - {name}")
    if extra:
        print("tables present in the database but not declared by models:")
        for name in extra:
            print(f"  - {name}")

    if missing or extra:
        print("migration drift detected")
        return 1

    print("models and migrations are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

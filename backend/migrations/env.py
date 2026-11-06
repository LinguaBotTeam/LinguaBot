"""Explicit async migrations; no schema changes at application startup."""

import asyncio
from importlib import import_module
from typing import Any

from alembic import context
from alembic.util import CommandError
from sqlalchemy import event, inspect, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from linguabot.core.config import settings
from linguabot.db.base import Base
from migrations.legacy_schema import validate_legacy_schema


for module_name in (
    "linguabot.modules.users.models",
    "linguabot.modules.dialogues.models",
    "linguabot.modules.assessment.models",
):
    import_module(module_name)


def run_migrations(connection: Connection) -> None:
    legacy = context.get_x_argument(as_dictionary=True).get(
        "legacy_baseline"
    ) == "true"
    with connection.begin():
        tables = inspect(connection).get_table_names()
        if legacy:
            if context.get_revision_argument() != "0001_existing_schema":
                raise CommandError("Legacy adoption can stamp baseline only.")
            validate_legacy_schema(connection)
        elif tables and "alembic_version" not in tables:
            raise CommandError(
                "Unversioned database: back up and validate legacy baseline "
                "before upgrade; see migrations/README.md."
            )
        context.configure(
            connection=connection, target_metadata=Base.metadata,
            transactional_ddl=True, compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(
        settings.database_url, poolclass=pool.NullPool
    )
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine.sync_engine, "connect")
        def configure_sqlite(dbapi: Any, _record: Any) -> None:
            # Explicit BEGIN makes SQLite DDL transactional too.
            dbapi.isolation_level = None
            cursor = dbapi.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        @event.listens_for(engine.sync_engine, "begin")
        def begin_sqlite(connection: Connection) -> None:
            connection.exec_driver_sql("BEGIN")
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise CommandError("Use online migrations; schema validation needs a DB.")
else:
    asyncio.run(run_online())

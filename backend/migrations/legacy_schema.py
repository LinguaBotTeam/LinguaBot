"""Frozen pre-project schema and read-only validation before adoption."""

from sqlalchemy import (
    JSON, Column, DateTime, ForeignKey, Integer, MetaData, String, Table,
    Text, func, inspect,
)
from sqlalchemy.engine import Connection
from sqlalchemy.schema import DefaultClause


def legacy_metadata() -> MetaData:
    """Do not import current ORM models: this baseline must stay frozen."""
    metadata = MetaData()
    Table(
        "users", metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(120), nullable=False),
        Column("email", String(255), nullable=False, unique=True, index=True),
        Column("password_hash", String(255), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False,
               server_default=func.now()),
    )
    Table(
        "dialogues", metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer,
               ForeignKey("users.id", ondelete="CASCADE"),
               nullable=False, index=True),
        Column("title", String(160), nullable=False),
        Column("scenario", String(64), nullable=False),
        Column("status", String(16), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False,
               server_default=func.now()),
        Column("updated_at", DateTime(timezone=True), nullable=False,
               server_default=func.now()),
    )
    Table(
        "messages", metadata,
        Column("id", Integer, primary_key=True),
        Column("dialogue_id", Integer,
               ForeignKey("dialogues.id", ondelete="CASCADE"),
               nullable=False, index=True),
        Column("role", String(16), nullable=False),
        Column("content", Text, nullable=False),
        Column("correction", Text),
        Column("created_at", DateTime(timezone=True), nullable=False,
               server_default=func.now()),
    )
    Table(
        "test_results", metadata,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer,
               ForeignKey("users.id", ondelete="CASCADE"),
               nullable=False, index=True),
        Column("score", Integer, nullable=False),
        Column("level", String(24), nullable=False),
        Column("cefr", String(4)),
        Column("details", JSON),
        Column("taken_at", DateTime(timezone=True), nullable=False,
               server_default=func.now()),
    )
    return metadata


def _default(value: object) -> str:
    return str(value or "").upper().strip(" ()'\"")


def validate_legacy_schema(connection: Connection) -> None:
    """Compare structure only. Never read user rows or stamp a version."""
    inspector = inspect(connection)
    expected = legacy_metadata()
    mismatch = "Legacy schema mismatch; baseline stamp was not applied."
    if set(inspector.get_table_names()) != set(expected.tables):
        raise ValueError(mismatch)
    if inspector.get_view_names():
        raise ValueError(mismatch)
    for table in expected.tables.values():
        columns = {c["name"]: c for c in inspector.get_columns(table.name)}
        if set(columns) != set(table.columns.keys()):
            raise ValueError(mismatch)
        for column in table.columns:
            actual = columns[column.name]
            default = None
            if isinstance(column.server_default, DefaultClause):
                argument = column.server_default.arg
                default = (
                    argument if isinstance(argument, str)
                    else argument.compile(dialect=connection.dialect)
                )
            if (
                str(actual["type"]) != str(column.type)
                or actual["nullable"] != column.nullable
                or _default(actual.get("default")) != _default(default)
            ):
                raise ValueError(mismatch)
        primary = inspector.get_pk_constraint(table.name)
        if set(primary["constrained_columns"]) != {
            c.name for c in table.primary_key.columns
        }:
            raise ValueError(mismatch)
        indexes = {
            (index["name"], tuple(index["column_names"]),
             bool(index["unique"]))
            for index in inspector.get_indexes(table.name)
        }
        expected_indexes = {
            (index.name, tuple(c.name for c in index.columns),
             bool(index.unique))
            for index in table.indexes
        }
        if indexes != expected_indexes:
            raise ValueError(mismatch)
        if inspector.get_unique_constraints(table.name):
            raise ValueError(mismatch)
        foreign_keys = {
            (tuple(key["constrained_columns"]), key["referred_table"],
             tuple(key["referred_columns"]),
             key.get("options", {}).get("ondelete"))
            for key in inspector.get_foreign_keys(table.name)
        }
        expected_foreign_keys = {
            (tuple(c.parent.name for c in key.elements),
             key.referred_table.name,
             tuple(c.column.name for c in key.elements), key.ondelete)
            for key in table.foreign_key_constraints
        }
        if foreign_keys != expected_foreign_keys:
            raise ValueError(mismatch)

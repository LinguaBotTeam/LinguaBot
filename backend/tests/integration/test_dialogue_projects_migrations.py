"""Migration checks use independent legacy DDL and synthetic data only."""

import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


BACKEND = Path(__file__).resolve().parents[2]
BASELINE = "0001_existing_schema"
HEAD = "0002_dialogue_projects"
LEGACY = """
CREATE TABLE users (
 id INTEGER NOT NULL PRIMARY KEY, name VARCHAR(120) NOT NULL,
 email VARCHAR(255) NOT NULL, password_hash VARCHAR(255) NOT NULL,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL);
CREATE UNIQUE INDEX ix_users_email ON users(email);
CREATE TABLE dialogues (
 id INTEGER NOT NULL PRIMARY KEY, user_id INTEGER NOT NULL,
 title VARCHAR(160) NOT NULL, scenario VARCHAR(64) NOT NULL,
 status VARCHAR(16) NOT NULL,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
 updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE INDEX ix_dialogues_user_id ON dialogues(user_id);
CREATE TABLE messages (
 id INTEGER NOT NULL PRIMARY KEY, dialogue_id INTEGER NOT NULL,
 role VARCHAR(16) NOT NULL, content TEXT NOT NULL, correction TEXT,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
 FOREIGN KEY(dialogue_id) REFERENCES dialogues(id) ON DELETE CASCADE);
CREATE INDEX ix_messages_dialogue_id ON messages(dialogue_id);
CREATE TABLE test_results (
 id INTEGER NOT NULL PRIMARY KEY, user_id INTEGER NOT NULL,
 score INTEGER NOT NULL, level VARCHAR(24) NOT NULL, cefr VARCHAR(4),
 details JSON, taken_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE INDEX ix_test_results_user_id ON test_results(user_id);
"""


def legacy_database(path):
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(LEGACY)
        connection.executemany(
            "INSERT INTO users(id,name,email,password_hash) VALUES (?,?,?,?)",
            [(10, "Synthetic owner", "owner@example.com", "unused"),
             (20, "Synthetic other", "other@example.com", "unused")],
        )
        connection.execute(
            "INSERT INTO dialogues(id,user_id,title,scenario,status) "
            "VALUES (100,10,'Synthetic cafe','cafe','active')"
        )
        connection.executemany(
            "INSERT INTO messages(id,dialogue_id,role,content,correction) "
            "VALUES (?,100,?,?,?)",
            [(1000, "user", "I is hungry.", "I am hungry."),
             (1001, "assistant", "What would you like?", None)],
        )
        connection.execute(
            "INSERT INTO test_results(id,user_id,score,level,cefr,details) "
            "VALUES (500,10,8,'beginner','A1','{}')"
        )


def migrate(path, *arguments, expect_success=True):
    environment = os.environ.copy()
    environment["DATABASE_URL"] = "sqlite+aiosqlite:///" + path.as_posix()
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND, env=environment, capture_output=True, text=True,
    )
    if expect_success:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
    return result


def snapshot(connection):
    return {
        table: connection.execute(
            f"SELECT * FROM {table} ORDER BY id"
        ).fetchall()
        for table in ("users", "messages", "test_results")
    }


def test_legacy_upgrade_preserves_rows_and_history(tmp_path):
    database = tmp_path / "legacy.db"
    legacy_database(database)
    with sqlite3.connect(database) as connection:
        before = snapshot(connection)
        dialogue = connection.execute("SELECT * FROM dialogues").fetchone()
        rootpage = connection.execute(
            "SELECT rootpage FROM sqlite_master WHERE name='dialogues'"
        ).fetchone()
    migrate(database, "-x", "legacy_baseline=true", "stamp", BASELINE)
    migrate(database, "upgrade", "head")
    migrate(database, "upgrade", "head")
    with sqlite3.connect(database) as connection:
        assert snapshot(connection) == before
        current = connection.execute("SELECT * FROM dialogues").fetchone()
        assert current == (*dialogue, None)
        assert connection.execute(
            "SELECT rootpage FROM sqlite_master WHERE name='dialogues'"
        ).fetchone() == rootpage
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == (HEAD,)
        assert connection.execute(
            "SELECT count(*) FROM dialogue_projects"
        ).fetchone() == (0,)


def test_new_database_upgrade_matches_registered_models(tmp_path):
    from sqlalchemy import create_engine
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from linguabot.db.base import Base

    database = tmp_path / "new.db"
    migrate(database, "upgrade", "head")
    engine = create_engine("sqlite:///" + database.as_posix())

    def include_object(obj, _name, type_, _reflected, _compare_to):
        # SQLite reflection omits inline REFERENCES options. Check that FK
        # independently through PRAGMA below, rather than comparing lost data.
        return not (
            type_ == "foreign_key_constraint"
            and obj.table.name == "dialogues"
            and [c.name for c in obj.columns] == ["project_id"]
        )

    try:
        with engine.connect() as connection:
            differences = compare_metadata(
                MigrationContext.configure(
                    connection, opts={"include_object": include_object}
                ), Base.metadata,
            )
            assert differences == []
            actual = next(
                row for row in connection.exec_driver_sql(
                    "PRAGMA foreign_key_list(dialogues)"
                ) if row[3] == "project_id"
            )
            expected = next(iter(
                Base.metadata.tables["dialogues"].c.project_id.foreign_keys
            ))
            assert (actual[2], actual[4], actual[6]) == (
                expected.column.table.name, expected.column.name,
                expected.ondelete,
            )
    finally:
        engine.dispose()


def test_project_link_enforces_fk_and_set_null(tmp_path):
    database = tmp_path / "foreign-keys.db"
    legacy_database(database)
    migrate(database, "-x", "legacy_baseline=true", "stamp", BASELINE)
    migrate(database, "upgrade", "head")
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        before = snapshot(connection)
        connection.execute(
            "INSERT INTO dialogue_projects(id,user_id,name) "
            "VALUES (7,10,'Synthetic trip')"
        )
        connection.execute("UPDATE dialogues SET project_id=7 WHERE id=100")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE dialogues SET project_id=999 WHERE id=100"
            )
        connection.execute("DELETE FROM dialogue_projects WHERE id=7")
        assert connection.execute(
            "SELECT project_id FROM dialogues WHERE id=100"
        ).fetchone() == (None,)
        assert snapshot(connection) == before


@pytest.mark.parametrize("mutation", [
    "DROP INDEX ix_dialogues_user_id",
    "ALTER TABLE users ADD COLUMN unexpected TEXT",
    "CREATE TABLE unexpected (id INTEGER)",
])
def test_mismatched_schema_cannot_be_stamped(tmp_path, mutation):
    database = tmp_path / "mismatch.db"
    legacy_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(mutation)
        before = snapshot(connection)
    migrate(database, "-x", "legacy_baseline=true", "stamp", BASELINE,
            expect_success=False)
    with sqlite3.connect(database) as connection:
        assert snapshot(connection) == before
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name='alembic_version'"
        ).fetchone() is None


def test_unversioned_database_requires_explicit_baseline(tmp_path):
    database = tmp_path / "unversioned.db"
    legacy_database(database)
    migrate(database, "upgrade", "head", expect_success=False)
    with sqlite3.connect(database) as connection:
        assert "project_id" not in {
            row[1]
            for row in connection.execute("PRAGMA table_info(dialogues)")
        }
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name='dialogue_projects'"
        ).fetchone() is None


def test_downgrade_preserves_dialogues_and_messages(tmp_path):
    database = tmp_path / "rollback.db"
    legacy_database(database)
    migrate(database, "-x", "legacy_baseline=true", "stamp", BASELINE)
    migrate(database, "upgrade", "head")
    with sqlite3.connect(database) as connection:
        before = snapshot(connection)
        connection.execute(
            "INSERT INTO dialogue_projects(id,user_id,name) "
            "VALUES (7,10,'Synthetic trip')"
        )
        connection.execute("UPDATE dialogues SET project_id=7 WHERE id=100")
    migrate(database, "downgrade", BASELINE)
    with sqlite3.connect(database) as connection:
        assert snapshot(connection) == before
        assert connection.execute("SELECT id FROM dialogues").fetchall() == [
            (100,)
        ]
        assert "project_id" not in {
            row[1]
            for row in connection.execute("PRAGMA table_info(dialogues)")
        }

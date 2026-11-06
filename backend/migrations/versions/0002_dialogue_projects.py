"""Add optional project folders without rewriting existing dialogues."""

from alembic import op
from alembic.util import CommandError
import sqlalchemy as sa


revision = "0002_dialogue_projects"
down_revision = "0001_existing_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if (
        connection.dialect.name == "sqlite"
        and connection.dialect.server_version_info < (3, 35)
    ):
        raise CommandError("Projects migrations require SQLite 3.35 or newer.")
    op.create_table(
        "dialogue_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_dialogue_projects_user_id", "dialogue_projects",
                    ["user_id"])
    if connection.dialect.name == "sqlite":
        # SQLite accepts nullable inline REFERENCES with existing rows.
        # Avoid a batch rebuild of the parent of messages (ON DELETE CASCADE).
        op.execute(
            "ALTER TABLE dialogues ADD COLUMN project_id INTEGER "
            "CONSTRAINT fk_dialogues_project_id "
            "REFERENCES dialogue_projects(id) ON DELETE SET NULL"
        )
    else:
        op.add_column(
            "dialogues", sa.Column(
                "project_id", sa.Integer(),
                sa.ForeignKey("dialogue_projects.id", ondelete="SET NULL",
                              name="fk_dialogues_project_id"),
                nullable=True,
            ),
        )
    op.create_index("ix_dialogues_project_id", "dialogues", ["project_id"])


def downgrade() -> None:
    connection = op.get_bind()
    op.drop_index("ix_dialogues_project_id", table_name="dialogues")
    if connection.dialect.name == "sqlite":
        op.execute("ALTER TABLE dialogues DROP COLUMN project_id")
    else:
        op.drop_constraint("fk_dialogues_project_id", "dialogues",
                           type_="foreignkey")
        op.drop_column("dialogues", "project_id")
    op.drop_index(
        "ix_dialogue_projects_user_id", table_name="dialogue_projects"
    )
    op.drop_table("dialogue_projects")

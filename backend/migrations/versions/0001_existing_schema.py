"""Baseline matching the existing users, chat and assessment schema."""

from alembic import op
from alembic.util import CommandError

from migrations.legacy_schema import legacy_metadata


revision = "0001_existing_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    legacy_metadata().create_all(op.get_bind(), checkfirst=False)


def downgrade() -> None:
    raise CommandError("Dropping the original application schema is disabled.")

"""index transfer record destination paths

Revision ID: e2f3a4b5c6d7
Revises: c9d0e1f2a3b4
Create Date: 2026-11-10 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_transrecords_destpath ON transrecords (destpath)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_transrecords_destpath")

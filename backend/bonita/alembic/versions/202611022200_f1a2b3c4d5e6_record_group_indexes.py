"""index the joins used by the record group view

Revision ID: f1a2b3c4d5e6
Revises: c5d6e7f8a9b0
Create Date: 2026-11-02 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_transrecords_srcpath ON transrecords (srcpath)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_extrainfo_filepath ON extrainfo (filepath)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_extrainfo_number_key ON extrainfo (upper(trim(number)))")
    op.execute("CREATE INDEX IF NOT EXISTS ix_metadata_number_key ON metadata (upper(trim(number)))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_metadata_number_key")
    op.execute("DROP INDEX IF EXISTS ix_extrainfo_number_key")
    op.execute("DROP INDEX IF EXISTS ix_extrainfo_filepath")
    op.execute("DROP INDEX IF EXISTS ix_transrecords_srcpath")

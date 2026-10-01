"""record optional output folder

Revision ID: b3c4d5e6f7a8
Revises: e7f8a9b0c1d2
Create Date: 2026-10-01 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transrecords", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "output_folder",
                sa.String(),
                nullable=True,
                server_default="",
                comment="可选输出目录",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("transrecords", schema=None) as batch_op:
        batch_op.drop_column("output_folder")

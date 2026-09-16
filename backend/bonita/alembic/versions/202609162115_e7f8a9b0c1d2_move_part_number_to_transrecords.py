"""move part number from extrainfo to transrecords

Revision ID: e7f8a9b0c1d2
Revises: d8e9f0a1b2c3
Create Date: 2026-09-16 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transrecords", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "part_number",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="部次",
            )
        )

    op.execute(
        sa.text(
            """
            UPDATE transrecords
            SET part_number = (
                SELECT extrainfo."partNumber"
                FROM extrainfo
                WHERE extrainfo.filepath = transrecords.srcpath
                  AND extrainfo."partNumber" IS NOT NULL
                  AND extrainfo."partNumber" > 0
            )
            WHERE EXISTS (
                SELECT 1 FROM extrainfo
                WHERE extrainfo.filepath = transrecords.srcpath
                  AND extrainfo."partNumber" IS NOT NULL
                  AND extrainfo."partNumber" > 0
            )
            """
        )
    )

    with op.batch_alter_table("extrainfo", schema=None) as batch_op:
        batch_op.drop_column("partNumber")


def downgrade() -> None:
    with op.batch_alter_table("extrainfo", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("partNumber", sa.Integer(), nullable=True, comment="分集数")
        )

    op.execute(
        sa.text(
            """
            UPDATE extrainfo
            SET "partNumber" = (
                SELECT transrecords.part_number
                FROM transrecords
                WHERE transrecords.srcpath = extrainfo.filepath
                  AND transrecords.part_number IS NOT NULL
                  AND transrecords.part_number > 0
            )
            WHERE EXISTS (
                SELECT 1 FROM transrecords
                WHERE transrecords.srcpath = extrainfo.filepath
                  AND transrecords.part_number IS NOT NULL
                  AND transrecords.part_number > 0
            )
            """
        )
    )

    with op.batch_alter_table("transrecords", schema=None) as batch_op:
        batch_op.drop_column("part_number")

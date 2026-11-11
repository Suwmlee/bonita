"""drop unique on actoralias.name to allow homonyms

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-11 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("actoralias", schema=None) as batch_op:
        batch_op.drop_constraint("uq_actoralias_name", type_="unique")


def downgrade() -> None:
    with op.batch_alter_table("actoralias", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_actoralias_name", ["name"])

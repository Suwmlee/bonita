"""store emby item id on collection members

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-08-29 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("collectionitem", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("emby_item_id", sa.String(), nullable=True, comment="对应的 Emby 条目 Id，回写时用")
        )
        batch_op.create_index(
            batch_op.f("ix_collectionitem_emby_item_id"),
            ["emby_item_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("collectionitem", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_collectionitem_emby_item_id"))
        batch_op.drop_column("emby_item_id")

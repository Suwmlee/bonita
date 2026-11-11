"""add metadata_actor credit table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f8
Create Date: 2026-11-11 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metadata_actor",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("metadata_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("credit_name", sa.String(), nullable=False, comment="这部片子的刮削出演名"),
        sa.Column("sort", sa.Integer(), nullable=False, comment="写出顺序"),
        sa.Column("createtime", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.ForeignKeyConstraint(["actor_id"], ["actor.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["metadata_id"], ["metadata.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metadata_id", "actor_id", name="uq_metadata_actor"),
    )
    with op.batch_alter_table("metadata_actor", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_metadata_actor_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_metadata_actor_metadata_id"), ["metadata_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_metadata_actor_actor_id"), ["actor_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("metadata_actor", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_metadata_actor_actor_id"))
        batch_op.drop_index(batch_op.f("ix_metadata_actor_metadata_id"))
        batch_op.drop_index(batch_op.f("ix_metadata_actor_id"))
    op.drop_table("metadata_actor")

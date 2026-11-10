"""add actor and actor alias tables

Revision ID: a1b2c3d4e5f8
Revises: e2f3a4b5c6d7
Create Date: 2026-11-10 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "actor",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, comment="主名（写出用）"),
        sa.Column("photo", sa.String(), nullable=True, comment="头像 URL，展示时按需缓存"),
        sa.Column("birth_date", sa.Date(), nullable=True, comment="出生日期"),
        sa.Column("outline", sa.String(), nullable=True, comment="概要"),
        sa.Column("createtime", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updatetime", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("actor", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_actor_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_actor_name"), ["name"], unique=False)

    op.create_table(
        "actoralias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, comment="别名或主名"),
        sa.Column("createtime", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.ForeignKeyConstraint(["actor_id"], ["actor.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_actoralias_name"),
    )
    with op.batch_alter_table("actoralias", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_actoralias_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_actoralias_actor_id"), ["actor_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_actoralias_name"), ["name"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("actoralias", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_actoralias_name"))
        batch_op.drop_index(batch_op.f("ix_actoralias_actor_id"))
        batch_op.drop_index(batch_op.f("ix_actoralias_id"))
    op.drop_table("actoralias")
    with op.batch_alter_table("actor", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_actor_name"))
        batch_op.drop_index(batch_op.f("ix_actor_id"))
    op.drop_table("actor")

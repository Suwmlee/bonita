"""add collection whitelist tables

Revision ID: a1b2c3d4e5f6
Revises: c4e8f1a90b2d
Create Date: 2026-08-29 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c4e8f1a90b2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("emby_id", sa.String(), nullable=False, comment="Emby BoxSet Id"),
        sa.Column("name", sa.String(), nullable=False, comment="合集名称"),
        sa.Column("image_tag", sa.String(), nullable=True, comment="Emby 海报 ImageTag"),
        sa.Column("item_count", sa.Integer(), nullable=True, comment="Emby 成员数"),
        sa.Column("matched_count", sa.Integer(), nullable=True, comment="对上本地媒体项的数量"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True, comment="上次同步成员时间"),
        sa.Column("createtime", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updatetime", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("collection", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_collection_emby_id"), ["emby_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_collection_id"), ["id"], unique=False)

    op.create_table(
        "collectionitem",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("media_item_id", sa.Integer(), nullable=False),
        sa.Column("createtime", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.ForeignKeyConstraint(["collection_id"], ["collection.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_item_id"], ["mediaitem.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "media_item_id", name="uq_collection_media_item"),
    )
    with op.batch_alter_table("collectionitem", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_collectionitem_collection_id"), ["collection_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_collectionitem_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_collectionitem_media_item_id"), ["media_item_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("collectionitem", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_collectionitem_media_item_id"))
        batch_op.drop_index(batch_op.f("ix_collectionitem_id"))
        batch_op.drop_index(batch_op.f("ix_collectionitem_collection_id"))
    op.drop_table("collectionitem")
    with op.batch_alter_table("collection", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_collection_id"))
        batch_op.drop_index(batch_op.f("ix_collection_emby_id"))
    op.drop_table("collection")

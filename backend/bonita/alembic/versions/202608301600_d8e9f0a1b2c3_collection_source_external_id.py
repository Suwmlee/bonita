"""collection source + generalize emby ids

Revision ID: d8e9f0a1b2c3
Revises: b7c8d9e0f1a2
Create Date: 2026-08-30 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "collection",
        sa.Column(
            "source",
            sa.String(),
            nullable=False,
            server_default="emby",
            comment="媒体源 emby/jellyfin",
        ),
    )
    op.drop_index("ix_collection_emby_id", table_name="collection")
    op.execute(sa.text("ALTER TABLE collection RENAME COLUMN emby_id TO external_id"))
    op.create_index("ix_collection_source", "collection", ["source"], unique=False)
    op.create_index("ix_collection_external_id", "collection", ["external_id"], unique=False)
    op.create_index(
        "uq_collection_source_external_id",
        "collection",
        ["source", "external_id"],
        unique=True,
    )

    op.drop_index("ix_collectionitem_emby_item_id", table_name="collectionitem")
    op.execute(sa.text("ALTER TABLE collectionitem RENAME COLUMN emby_item_id TO external_item_id"))
    op.create_index(
        "ix_collectionitem_external_item_id",
        "collectionitem",
        ["external_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_collectionitem_external_item_id", table_name="collectionitem")
    op.execute(sa.text("ALTER TABLE collectionitem RENAME COLUMN external_item_id TO emby_item_id"))
    op.create_index("ix_collectionitem_emby_item_id", "collectionitem", ["emby_item_id"], unique=False)

    op.drop_index("uq_collection_source_external_id", table_name="collection")
    op.drop_index("ix_collection_external_id", table_name="collection")
    op.drop_index("ix_collection_source", table_name="collection")
    op.execute(sa.text("ALTER TABLE collection RENAME COLUMN external_id TO emby_id"))
    op.create_index("ix_collection_emby_id", "collection", ["emby_id"], unique=True)
    op.drop_column("collection", "source")

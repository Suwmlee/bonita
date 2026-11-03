"""link transfer records to media items

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-11-03 23:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transrecords", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("media_item_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index(
            "ix_transrecords_media_item_id",
            ["media_item_id"],
        )
        batch_op.create_foreign_key(
            "fk_transrecords_media_item_id",
            "mediaitem",
            ["media_item_id"],
            ["id"],
        )

    op.execute(
        """
        UPDATE mediaitem
        SET media_type = 'number'
        WHERE media_type = 'movie'
          AND number IS NOT NULL
          AND length(trim(number)) > 0
        """
    )
    op.execute(
        """
        INSERT INTO mediaitem (
            media_type, number, title, season_number, episode_number, createtime, updatetime
        )
        SELECT
            'number',
            upper(trim(m.number)),
            CASE
                WHEN trim(COALESCE(m.title, '')) = '' THEN upper(trim(m.number))
                ELSE m.title
            END,
            -1,
            -1,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM metadata m
        INNER JOIN (
            SELECT upper(trim(number)) AS number_key, MAX(id) AS metadata_id
            FROM metadata
            WHERE number IS NOT NULL AND length(trim(number)) > 0
            GROUP BY upper(trim(number))
        ) latest ON m.id = latest.metadata_id
        WHERE NOT EXISTS (
            SELECT 1 FROM mediaitem mi
            WHERE upper(trim(COALESCE(mi.number, ''))) = latest.number_key
              AND mi.media_type IN ('number', 'movie')
              AND length(trim(COALESCE(mi.number, ''))) > 0
        )
        """
    )
    op.execute(
        """
        UPDATE transrecords
        SET media_item_id = (
            SELECT mi.id
            FROM mediaitem mi
            INNER JOIN extrainfo e
                ON upper(trim(e.number)) = upper(trim(mi.number))
            INNER JOIN metadata md
                ON upper(trim(md.number)) = upper(trim(mi.number))
            WHERE e.filepath = transrecords.srcpath
              AND mi.media_type = 'number'
              AND length(trim(COALESCE(mi.number, ''))) > 0
            ORDER BY mi.id DESC
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1
            FROM mediaitem mi
            INNER JOIN extrainfo e
                ON upper(trim(e.number)) = upper(trim(mi.number))
            INNER JOIN metadata md
                ON upper(trim(md.number)) = upper(trim(mi.number))
            WHERE e.filepath = transrecords.srcpath
              AND mi.media_type = 'number'
              AND length(trim(COALESCE(mi.number, ''))) > 0
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE mediaitem
        SET media_type = 'movie'
        WHERE media_type = 'number'
        """
    )
    with op.batch_alter_table("transrecords", schema=None) as batch_op:
        batch_op.drop_constraint("fk_transrecords_media_item_id", type_="foreignkey")
        batch_op.drop_index("ix_transrecords_media_item_id")
        batch_op.drop_column("media_item_id")

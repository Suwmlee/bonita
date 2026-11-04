"""subtitle preferred copy and media item link

Revision ID: c9d0e1f2a3b4
Revises: a7b8c9d0e1f2
Create Date: 2026-11-04 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _stamp(value, row_id: int):
    if value is None:
        text = ""
    elif hasattr(value, "isoformat"):
        text = value.isoformat()
    else:
        text = str(value)
    return (text, row_id)


def upgrade() -> None:
    with op.batch_alter_table("subtitle", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("preferred", sa.Boolean(), nullable=True, server_default="0", comment="当前投递这一份")
        )
        batch_op.add_column(
            sa.Column("delivered_paths", sa.Text(), nullable=True, server_default="", comment="上次写到影片旁边的路径")
        )
        batch_op.add_column(sa.Column("media_item_id", sa.Integer(), nullable=True, comment="关联的媒体项"))
        batch_op.create_index("ix_subtitle_media_item_id", ["media_item_id"])
        batch_op.create_foreign_key(
            "fk_subtitle_media_item_id",
            "mediaitem",
            ["media_item_id"],
            ["id"],
            ondelete="SET NULL",
        )
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, identity_key, language, part_number, updatetime FROM subtitle")
    ).fetchall()
    best = {}
    item_ids = {}
    for row in rows:
        key = (row.identity_key or "").strip().upper()
        if not key:
            continue
        if key not in item_ids:
            found = connection.execute(
                sa.text(
                    """
                    SELECT id FROM mediaitem
                    WHERE upper(trim(number)) = :key
                      AND media_type IN ('number', 'movie')
                    ORDER BY CASE WHEN media_type = 'number' THEN 0 ELSE 1 END, id DESC
                    LIMIT 1
                    """
                ),
                {"key": key},
            ).first()
            item_ids[key] = found[0] if found else None
        if item_ids[key]:
            connection.execute(
                sa.text("UPDATE subtitle SET media_item_id = :item_id WHERE id = :id"),
                {"item_id": item_ids[key], "id": row.id},
            )
        group = (key, row.language or "", int(row.part_number or 0))
        rank = _stamp(row.updatetime, row.id)
        current = best.get(group)
        if current is None or rank >= current[0]:
            best[group] = (rank, row.id)
    for _rank, subtitle_id in best.values():
        connection.execute(
            sa.text("UPDATE subtitle SET preferred = 1 WHERE id = :id"),
            {"id": subtitle_id},
        )
    with op.batch_alter_table("subtitle", schema=None) as batch_op:
        batch_op.drop_index("ix_subtitle_identity_key")
        batch_op.drop_index("ix_subtitle_identity_type")
        batch_op.drop_column("identity_key")
        batch_op.drop_column("identity_type")


def downgrade() -> None:
    with op.batch_alter_table("subtitle", schema=None) as batch_op:
        batch_op.add_column(sa.Column("identity_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("identity_key", sa.String(), nullable=True))
        batch_op.create_index("ix_subtitle_identity_type", ["identity_type"])
        batch_op.create_index("ix_subtitle_identity_key", ["identity_key"])
        batch_op.drop_constraint("fk_subtitle_media_item_id", type_="foreignkey")
        batch_op.drop_index("ix_subtitle_media_item_id")
        batch_op.drop_column("media_item_id")
        batch_op.drop_column("delivered_paths")
        batch_op.drop_column("preferred")

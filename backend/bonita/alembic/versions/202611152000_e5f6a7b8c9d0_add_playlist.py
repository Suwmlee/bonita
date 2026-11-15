"""add playlist whitelist tables for plex music

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "playlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, comment="媒体源 plex"),
        sa.Column("external_id", sa.String(), nullable=False, comment="稳定远端 Id，优先 playlist guid"),
        sa.Column("rating_key", sa.String(), nullable=True, comment="当前 Plex ratingKey 缓存（拉取源）"),
        sa.Column(
            "write_rating_key",
            sa.String(),
            nullable=True,
            comment="回写目标 ratingKey；smart 时为「原名 · 同步」普通列表",
        ),
        sa.Column("name", sa.String(), nullable=False, comment="播放列表名称"),
        sa.Column(
            "is_smart",
            sa.Boolean(),
            nullable=True,
            server_default="0",
            comment="是否 Plex smart 列表",
        ),
        sa.Column("item_count", sa.Integer(), nullable=True, comment="远端成员数"),
        sa.Column("matched_count", sa.Integer(), nullable=True, comment="本地成员快照数"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True, comment="上次同步成员时间"),
        sa.Column("createtime", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updatetime", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_playlist_source_external_id"),
    )
    with op.batch_alter_table("playlist", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_playlist_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_playlist_source"), ["source"], unique=False)
        batch_op.create_index(batch_op.f("ix_playlist_external_id"), ["external_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_playlist_rating_key"), ["rating_key"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_playlist_write_rating_key"),
            ["write_rating_key"],
            unique=False,
        )

    op.create_table(
        "playlistitem",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("playlist_id", sa.Integer(), nullable=False),
        sa.Column("media_item_id", sa.Integer(), nullable=True, comment="可选，对上本地媒体项时填写"),
        sa.Column("external_item_id", sa.String(), nullable=True, comment="远端 track ratingKey"),
        sa.Column("external_guid", sa.String(), nullable=True, comment="远端 track guid"),
        sa.Column("playlist_item_id", sa.String(), nullable=True, comment="Plex playlistItemID，删成员用"),
        sa.Column("path", sa.String(), nullable=True, comment="音轨文件路径"),
        sa.Column("title", sa.String(), nullable=True, comment="曲名"),
        sa.Column("artist", sa.String(), nullable=True, comment="艺人"),
        sa.Column("album", sa.String(), nullable=True, comment="专辑"),
        sa.Column("sort_index", sa.Integer(), nullable=True, comment="列表内顺序"),
        sa.Column("createtime", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlist.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_item_id"], ["mediaitem.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("playlistitem", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_playlistitem_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_playlistitem_playlist_id"), ["playlist_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_playlistitem_media_item_id"), ["media_item_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_playlistitem_external_item_id"), ["external_item_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_playlistitem_external_guid"), ["external_guid"], unique=False)
        batch_op.create_index(batch_op.f("ix_playlistitem_playlist_item_id"), ["playlist_item_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("playlistitem", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_playlistitem_playlist_item_id"))
        batch_op.drop_index(batch_op.f("ix_playlistitem_external_guid"))
        batch_op.drop_index(batch_op.f("ix_playlistitem_external_item_id"))
        batch_op.drop_index(batch_op.f("ix_playlistitem_media_item_id"))
        batch_op.drop_index(batch_op.f("ix_playlistitem_playlist_id"))
        batch_op.drop_index(batch_op.f("ix_playlistitem_id"))
    op.drop_table("playlistitem")
    with op.batch_alter_table("playlist", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_playlist_write_rating_key"))
        batch_op.drop_index(batch_op.f("ix_playlist_rating_key"))
        batch_op.drop_index(batch_op.f("ix_playlist_external_id"))
        batch_op.drop_index(batch_op.f("ix_playlist_source"))
        batch_op.drop_index(batch_op.f("ix_playlist_id"))
    op.drop_table("playlist")

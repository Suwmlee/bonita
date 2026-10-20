"""add subtitle library

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
Create Date: 2026-10-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subtitle",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identity_type", sa.String(), nullable=True, comment="标识类型"),
        sa.Column("identity_key", sa.String(), nullable=True, comment="标识值，番号大写"),
        sa.Column("language", sa.String(), nullable=True, comment="语言"),
        sa.Column("part_number", sa.Integer(), server_default="0", nullable=True, comment="部次，0 表示无分集"),
        sa.Column("original_name", sa.String(), nullable=True, comment="上传时的文件名"),
        sa.Column("stored_path", sa.String(), nullable=True, comment="相对字幕目录的存储路径"),
        sa.Column("file_extension", sa.String(), nullable=True, comment="扩展名，含点"),
        sa.Column("createtime", sa.DateTime(), nullable=True, comment="创建时间"),
        sa.Column("updatetime", sa.DateTime(), nullable=True, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subtitle_id"), "subtitle", ["id"], unique=False)
    op.create_index(op.f("ix_subtitle_identity_type"), "subtitle", ["identity_type"], unique=False)
    op.create_index(op.f("ix_subtitle_identity_key"), "subtitle", ["identity_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_subtitle_identity_key"), table_name="subtitle")
    op.drop_index(op.f("ix_subtitle_identity_type"), table_name="subtitle")
    op.drop_index(op.f("ix_subtitle_id"), table_name="subtitle")
    op.drop_table("subtitle")

"""normalize downloads.filepath to ASSETS-relative paths

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-12 16:00:00.000000

"""
from __future__ import annotations

import os
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from bonita.core.config import settings


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    assets_root = os.path.abspath(settings.ASSETS_LOCATION)
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id, filepath FROM downloads")).fetchall()
    for row in rows:
        row_id, filepath = row[0], row[1]
        text_path = (filepath or "").strip()
        if not text_path:
            continue
        if not os.path.isabs(text_path):
            normalized = text_path.replace("\\", "/").strip("/")
            if normalized and normalized != text_path:
                conn.execute(
                    text("UPDATE downloads SET filepath = :fp WHERE id = :id"),
                    {"fp": normalized, "id": row_id},
                )
            continue
        abs_fp = os.path.abspath(text_path)
        try:
            if os.path.commonpath([abs_fp, assets_root]) != assets_root:
                continue
        except ValueError:
            continue
        relative = os.path.relpath(abs_fp, assets_root).replace("\\", "/")
        if relative != text_path:
            conn.execute(
                text("UPDATE downloads SET filepath = :fp WHERE id = :id"),
                {"fp": relative, "id": row_id},
            )


def downgrade() -> None:
    assets_root = os.path.abspath(settings.ASSETS_LOCATION)
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id, filepath FROM downloads")).fetchall()
    for row in rows:
        row_id, filepath = row[0], row[1]
        text_path = (filepath or "").strip()
        if not text_path or os.path.isabs(text_path):
            continue
        absolute = os.path.abspath(os.path.join(assets_root, text_path))
        conn.execute(
            text("UPDATE downloads SET filepath = :fp WHERE id = :id"),
            {"fp": absolute, "id": row_id},
        )

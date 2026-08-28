"""update metadata crop

Revision ID: c4e8f1a90b2d
Revises: 3aadc460e69a
Create Date: 2026-08-28 23:00:00.000000

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8f1a90b2d'
down_revision: Union[str, None] = '3aadc460e69a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NO_CROP_PREFIXES = (
    'FC2', 'HEYZO', 'SIRO', 'SUKE', 'NTK', 'SCUTE',
    'MKD', 'GANA', 'MIUM', 'MAAN', 'GACHI', 'ARA',
)


def _need_crop(number: str) -> bool:
    """Keep in sync with bonita.modules.scraping.scraping.need_crop."""
    if not number:
        return True
    number_upper = number.upper()
    for prefix in _NO_CROP_PREFIXES:
        if number_upper.startswith(prefix):
            return False
    if re.match(r'^\d{6}[-_]\d+$', number):
        return False
    if re.match(r'^N\d{4}$', number_upper):
        return False
    return True


def upgrade() -> None:
    with op.batch_alter_table('metadata', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'crop',
                sa.Boolean(),
                nullable=True,
                server_default=sa.text('1'),
                comment='是否裁切poster',
            )
        )

    conn = op.get_bind()
    metadata_table = sa.table(
        'metadata',
        sa.column('id', sa.Integer),
        sa.column('number', sa.String),
        sa.column('crop', sa.Boolean),
    )
    extrainfo_table = sa.table(
        'extrainfo',
        sa.column('id', sa.Integer),
        sa.column('number', sa.String),
        sa.column('crop', sa.Boolean),
    )

    extras = conn.execute(
        sa.select(extrainfo_table.c.id, extrainfo_table.c.number, extrainfo_table.c.crop)
    ).fetchall()
    crop_by_number = {}
    for extra_id, number, crop in extras:
        if not number or crop is None:
            continue
        key = number.upper()
        prev = crop_by_number.get(key)
        if prev is None or extra_id > prev[0]:
            crop_by_number[key] = (extra_id, bool(crop))

    rows = conn.execute(sa.select(metadata_table.c.id, metadata_table.c.number)).fetchall()
    false_ids = []
    for metadata_id, number in rows:
        if number:
            extra = crop_by_number.get(number.upper())
            crop_val = extra[1] if extra else _need_crop(number)
        else:
            crop_val = True
        if not crop_val:
            false_ids.append(metadata_id)

    if false_ids:
        conn.execute(
            metadata_table.update()
            .where(metadata_table.c.id.in_(false_ids))
            .values(crop=False)
        )


def downgrade() -> None:
    with op.batch_alter_table('metadata', schema=None) as batch_op:
        batch_op.drop_column('crop')

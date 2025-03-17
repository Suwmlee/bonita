"""update

Revision ID: 062f620c65b4
Revises: 07c8c5cb55d1
Create Date: 2025-03-17 10:30:48.751219

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '062f620c65b4'
down_revision: Union[str, None] = '07c8c5cb55d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('mediaitem', schema=None) as batch_op:
        batch_op.drop_index('ix_mediaitem_douban_id')
        batch_op.drop_column('poster')
        batch_op.drop_column('year')
        batch_op.drop_column('douban_id')

    with op.batch_alter_table('watchhistory', schema=None) as batch_op:
        batch_op.add_column(sa.Column('favorite', sa.Boolean(), nullable=True, comment='是否喜爱'))
        batch_op.drop_column('source')
        batch_op.drop_column('external_id')

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('watchhistory', schema=None) as batch_op:
        batch_op.add_column(sa.Column('external_id', sa.VARCHAR(), nullable=False))
        batch_op.add_column(sa.Column('source', sa.VARCHAR(), nullable=False))
        batch_op.drop_column('favorite')

    with op.batch_alter_table('mediaitem', schema=None) as batch_op:
        batch_op.add_column(sa.Column('douban_id', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('year', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('poster', sa.VARCHAR(), nullable=True))
        batch_op.create_index('ix_mediaitem_douban_id', ['douban_id'], unique=False)

    # ### end Alembic commands ###

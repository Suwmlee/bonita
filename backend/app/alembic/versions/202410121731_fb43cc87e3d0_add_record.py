"""add record

Revision ID: fb43cc87e3d0
Revises: d39dc4d06e81
Create Date: 2024-10-12 17:31:38.378414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb43cc87e3d0'
down_revision: Union[str, None] = 'd39dc4d06e81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('transrecords',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('srcname', sa.String(), nullable=True),
    sa.Column('srcpath', sa.String(), nullable=True),
    sa.Column('srcfolder', sa.String(), nullable=True),
    sa.Column('ignored', sa.Boolean(), nullable=True),
    sa.Column('locked', sa.Boolean(), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('forced_name', sa.String(), nullable=True, comment='forced name'),
    sa.Column('top_folder', sa.String(), nullable=True),
    sa.Column('second_folder', sa.String(), nullable=True),
    sa.Column('isepisode', sa.Boolean(), nullable=True),
    sa.Column('season', sa.Integer(), nullable=True),
    sa.Column('episode', sa.Integer(), nullable=True),
    sa.Column('linkpath', sa.String(), nullable=True),
    sa.Column('destpath', sa.String(), nullable=True),
    sa.Column('updatetime', sa.DateTime(), nullable=True),
    sa.Column('deadtime', sa.DateTime(), nullable=True, comment='time to delete files'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('transfertask', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('transfertask', schema=None) as batch_op:
        batch_op.drop_column('deleted')

    op.drop_table('transrecords')
    # ### end Alembic commands ###

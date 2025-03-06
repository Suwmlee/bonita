"""recordd with task id

Revision ID: 5499b19d0194
Revises: 4e1deb8ef1bc
Create Date: 2025-03-06 16:39:22.488099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5499b19d0194'
down_revision: Union[str, None] = '4e1deb8ef1bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('transrecords', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_id', sa.Integer(), server_default='0', nullable=True, comment='任务ID'))

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('transrecords', schema=None) as batch_op:
        batch_op.drop_column('task_id')

    # ### end Alembic commands ###

"""update

Revision ID: d2fdac025143
Revises: bf7080c679d7
Create Date: 2024-08-31 22:34:01.997754

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2fdac025143'
down_revision: Union[str, None] = 'bf7080c679d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('library',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('lib_type', sa.Integer(), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=True),
    sa.Column('auto_watch', sa.Boolean(), nullable=True, comment='开启自动监测'),
    sa.Column('link_type', sa.Integer(), nullable=True),
    sa.Column('source_folder', sa.String(), nullable=True),
    sa.Column('output_folder', sa.String(), nullable=True),
    sa.Column('failed_folder', sa.String(), nullable=True),
    sa.Column('escape_folder', sa.String(), nullable=True),
    sa.Column('escape_literals', sa.String(), nullable=True),
    sa.Column('escape_size', sa.Integer(), nullable=True),
    sa.Column('threads_num', sa.Integer(), nullable=True),
    sa.Column('sc_enabled', sa.Boolean(), nullable=True, comment='启用刮削'),
    sa.Column('sc_id', sa.String(), nullable=True, comment='使用的刮削配置'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_library_id'), 'library', ['id'], unique=False)
    op.create_table('metadata',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('number', sa.String(), nullable=True),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('studio', sa.String(), nullable=True),
    sa.Column('release', sa.String(), nullable=True),
    sa.Column('year', sa.String(), nullable=True),
    sa.Column('outline', sa.String(), nullable=True),
    sa.Column('director', sa.String(), nullable=True),
    sa.Column('actor', sa.String(), nullable=True),
    sa.Column('actor_photo', sa.String(), nullable=True),
    sa.Column('cover', sa.String(), nullable=True),
    sa.Column('cover_small', sa.String(), nullable=True),
    sa.Column('extrafanart', sa.String(), nullable=True),
    sa.Column('trailer', sa.String(), nullable=True),
    sa.Column('tag', sa.String(), nullable=True),
    sa.Column('label', sa.String(), nullable=True),
    sa.Column('series', sa.String(), nullable=True),
    sa.Column('userrating', sa.String(), nullable=True),
    sa.Column('uservotes', sa.String(), nullable=True),
    sa.Column('detailurl', sa.String(), nullable=True),
    sa.Column('site', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_metadata_id'), 'metadata', ['id'], unique=False)
    op.create_table('scrapingconfig',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('save_metadata', sa.Boolean(), nullable=True),
    sa.Column('scraping_sites', sa.String(), nullable=True),
    sa.Column('location_rule', sa.String(), nullable=True),
    sa.Column('naming_rule', sa.String(), nullable=True),
    sa.Column('max_title_len', sa.Integer(), nullable=True),
    sa.Column('morestoryline', sa.Boolean(), nullable=True),
    sa.Column('extrafanart_enabled', sa.Boolean(), nullable=True),
    sa.Column('extrafanart_folder', sa.String(), nullable=True),
    sa.Column('watermark_enabled', sa.Boolean(), nullable=True),
    sa.Column('watermark_size', sa.Integer(), nullable=True),
    sa.Column('watermark_location', sa.Integer(), nullable=True),
    sa.Column('transalte_enabled', sa.Boolean(), nullable=True),
    sa.Column('transalte_to_sc', sa.Boolean(), nullable=True),
    sa.Column('transalte_values', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scrapingconfig_id'), 'scrapingconfig', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_scrapingconfig_id'), table_name='scrapingconfig')
    op.drop_table('scrapingconfig')
    op.drop_index(op.f('ix_metadata_id'), table_name='metadata')
    op.drop_table('metadata')
    op.drop_index(op.f('ix_library_id'), table_name='library')
    op.drop_table('library')
    # ### end Alembic commands ###

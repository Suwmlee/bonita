"""watch history

Revision ID: b0305c88a31f
Revises: f6497e8754c9
Create Date: 2025-03-13 22:40:44.096884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'b0305c88a31f'
down_revision: Union[str, None] = 'f6497e8754c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name):
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###

    # 检查表是否已存在，如果存在则跳过创建
    if not table_exists('mediaitem'):
        op.create_table('mediaitem',
                        sa.Column('id', sa.Integer(), nullable=False),
                        sa.Column('media_type', sa.String(), nullable=False, comment='媒体类型: movie, episode, special'),
                        sa.Column('imdb_id', sa.String(), nullable=True, comment='IMDB ID'),
                        sa.Column('tmdb_id', sa.String(), nullable=True, comment='TMDB ID'),
                        sa.Column('tvdb_id', sa.String(), nullable=True, comment='TVDB ID'),
                        sa.Column('douban_id', sa.String(), nullable=True, comment='豆瓣ID'),
                        sa.Column('number', sa.String(), nullable=True, comment='番号'),
                        sa.Column('title', sa.String(), nullable=False, comment='标题'),
                        sa.Column('original_title', sa.String(), nullable=True, comment='原始标题'),
                        sa.Column('year', sa.Integer(), nullable=True, comment='发行年份'),
                        sa.Column('poster', sa.String(), nullable=True, comment='海报图片URL'),
                        sa.Column('series_id', sa.Integer(), nullable=True, comment='关联的剧集ID'),
                        sa.Column('season_number', sa.Integer(), nullable=True, comment='季数'),
                        sa.Column('episode_number', sa.Integer(), nullable=True, comment='集数'),
                        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
                        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
                        sa.ForeignKeyConstraint(['series_id'], ['mediaitem.id'], ),
                        sa.PrimaryKeyConstraint('id')
                        )
        with op.batch_alter_table('mediaitem', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_mediaitem_douban_id'), ['douban_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_mediaitem_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_mediaitem_imdb_id'), ['imdb_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_mediaitem_number'), ['number'], unique=False)
            batch_op.create_index(batch_op.f('ix_mediaitem_tmdb_id'), ['tmdb_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_mediaitem_tvdb_id'), ['tvdb_id'], unique=False)

    if not table_exists('watchhistory'):
        op.create_table('watchhistory',
                        sa.Column('id', sa.Integer(), nullable=False),
                        sa.Column('media_item_id', sa.Integer(), nullable=False),
                        sa.Column('source', sa.String(), nullable=False,
                                  comment='观看历史来源(trakt, emby, jellyfin, douban等)'),
                        sa.Column('external_id', sa.String(), nullable=False, comment='来源系统中的ID'),
                        sa.Column('played_at', sa.DateTime(), nullable=True, comment='观看时间'),
                        sa.Column('play_count', sa.Integer(), nullable=True, comment='观看次数'),
                        sa.Column('play_progress', sa.Float(), nullable=True, comment='播放进度百分比'),
                        sa.Column('duration', sa.Integer(), nullable=True, comment='时长(秒)'),
                        sa.Column('rating', sa.Float(), nullable=True, comment='用户评分(1-10)'),
                        sa.Column('has_rating', sa.Boolean(), nullable=True, comment='是否有评分'),
                        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
                        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
                        sa.ForeignKeyConstraint(['media_item_id'], ['mediaitem.id'], ),
                        sa.PrimaryKeyConstraint('id')
                        )
        with op.batch_alter_table('watchhistory', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_watchhistory_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_watchhistory_media_item_id'), ['media_item_id'], unique=False)

    # 检查metadata表是否存在media_item_id列，如果不存在则添加
    with op.batch_alter_table('metadata', schema=None) as batch_op:
        # 检查列是否存在
        bind = op.get_bind()
        inspector = inspect(bind)
        columns = [col['name'] for col in inspector.get_columns('metadata')]

        if 'media_item_id' not in columns:
            batch_op.add_column(sa.Column('media_item_id', sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f('ix_metadata_media_item_id'), ['media_item_id'], unique=False)
            batch_op.create_foreign_key('fk_metadata_media_item_id_mediaitem', 'mediaitem', ['media_item_id'], ['id'])

        # 检查number列是否已经有索引
        indexes = inspector.get_indexes('metadata')
        has_number_index = any(idx['name'] == 'ix_metadata_number' for idx in indexes)
        if not has_number_index:
            batch_op.create_index(batch_op.f('ix_metadata_number'), ['number'], unique=False)

        # 尝试修改number列的可空性，但这可能会失败，所以我们捕获异常
        try:
            batch_op.alter_column('number', existing_type=sa.VARCHAR(), nullable=True)
        except Exception as e:
            print(f"Warning: Could not alter 'number' column: {e}")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('metadata', schema=None) as batch_op:
        batch_op.drop_constraint('fk_metadata_media_item_id_mediaitem', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_metadata_number'))
        batch_op.drop_index(batch_op.f('ix_metadata_media_item_id'))
        batch_op.alter_column('number',
                              existing_type=sa.VARCHAR(),
                              nullable=False)
        batch_op.drop_column('media_item_id')

    with op.batch_alter_table('watchhistory', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_watchhistory_media_item_id'))
        batch_op.drop_index(batch_op.f('ix_watchhistory_id'))

    op.drop_table('watchhistory')
    with op.batch_alter_table('mediaitem', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_mediaitem_tvdb_id'))
        batch_op.drop_index(batch_op.f('ix_mediaitem_tmdb_id'))
        batch_op.drop_index(batch_op.f('ix_mediaitem_number'))
        batch_op.drop_index(batch_op.f('ix_mediaitem_imdb_id'))
        batch_op.drop_index(batch_op.f('ix_mediaitem_id'))
        batch_op.drop_index(batch_op.f('ix_mediaitem_douban_id'))

    op.drop_table('mediaitem')
    # ### end Alembic commands ###

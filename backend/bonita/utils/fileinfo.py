import os
import logging
import re

from bonita.utils.regex import extractEpNum, matchEpPart, matchSeries, simpleMatchEp

logger = logging.getLogger(__name__)


class BasicFileInfo():
    """ 基础文件信息
    包含相对root路径的中间信息，解析后不再更新
    """

    def __init__(self, filepath):
        """初始化文件信息对象

        Args:
            filepath (str): 文件的完整路径
        """
        self.full_path = filepath
        self.parent_folder = os.path.dirname(self.full_path)
        self.basefolder = os.path.basename(self.parent_folder)
        self.filename = os.path.basename(self.full_path)
        self.basename, self.file_extension = os.path.splitext(self.filename)

        # 文件路径相关属性
        self.root_folder = ''
        self.top_folder = ''
        self.second_folder = ''

        # 剧集相关属性
        self.is_episode: bool = False
        self.original_episode_marker: str = ''
        self.season_number: int = -1
        self.episode_number: int = -1
        # 解析剧集信息
        self.parse_episode_info()

    def set_root_folder(self, root_folder):
        """设置根文件夹并解析相对路径

        Args:
            root_folder (str): 根文件夹路径
        """
        self.root_folder = root_folder
        tmp_parent = os.path.dirname(self.full_path)
        relative_path = tmp_parent.replace(root_folder, '').lstrip('\\/')
        segments = os.path.normpath(relative_path).split(os.path.sep)
        # 确保文件夹名不是 '.'
        self.top_folder = segments[0] if segments and segments[0] != '.' else ''
        self.second_folder = segments[1] if len(segments) > 1 and segments[1] != '.' else ''

    def parse_episode_info(self):
        """解析文件名中的剧集信息"""
        # 尝试匹配标准剧集格式
        season, episode = matchSeries(self.basename)
        if isinstance(season, int) and season > -1 and isinstance(episode, int) and episode > -1:
            self.is_episode = True
            self.season_number = season
            self.episode_number = episode
            self.original_episode_marker = 'Pass'
            return

        # 尝试匹配非标准剧集格式
        episode_marker = matchEpPart(self.basename)
        if episode_marker:
            episode_mark = extractEpNum(episode_marker)
            if episode_mark:
                # episode_mark 可能的值 01、01(video)、01v2
                self.is_episode = True
                self.original_episode_marker = episode_marker
                try:
                    self.episode_number = simpleMatchEp(episode_mark)
                except ValueError:
                    self.episode_number = -1


class TargetFileInfo():
    """ 目标文件信息 """

    def __init__(self, root_folder):
        self.root_folder: str = root_folder
        self.filename: str = ''
        self.basename: str = ''
        self.file_extension: str = ''

        self.is_episode: bool = False
        self.forced_season: bool = False
        self.season_number: int = -1
        self.forced_episode: bool = False
        self.episode_number: int = -1

        self.forced_top_folder: bool = False
        self.top_folder: str = ''
        self.second_folder: str = ''
        # 最终文件路径
        self.full_path: str = ''

    def force_update_episode(self, is_episode: bool, season_number: int, episode_number: int):
        """ 强制更新剧集信息 """
        # 如果 record 中定义了剧集信息，则使用 record 中的信息
        if is_episode:
            self.is_episode = True
            if season_number > -1:
                self.forced_season = True
                self.season_number = season_number
            if episode_number > -1:
                self.forced_episode = True
                self.episode_number = episode_number

    def force_update_top_folder(self, top_folder: str):
        """ 强制更新 top_folder """
        self.forced_top_folder = True
        self.top_folder = top_folder

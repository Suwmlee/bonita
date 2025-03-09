

import os
import logging

from bonita.utils.regex import extractEpNum, matchEpPart, matchSeries, simpleMatchEp

logger = logging.getLogger(__name__)


# class FileInfo():

#     realpath = ''
#     realfolder = ''
#     realname = ''
#     folders = []

#     midfolder = ''
#     topfolder = ''
#     secondfolder = ''
#     name = ''
#     ext = ''

#     isepisode = False
#     locked = False
#     forcedseason = False
#     originep = ''
#     season = None
#     epnum = None
#     forcedname = ''

#     finalpath = ''
#     finalfolder = ''

#     def __init__(self, filepath):
#         self.realpath = filepath
#         (filefolder, filename) = os.path.split(filepath)
#         self.realfolder = filefolder
#         self.realname = filename
#         (name, ext) = os.path.splitext(filename)
#         self.name = name
#         self.ext = ext

#     def updateMidFolder(self, mid):
#         self.midfolder = mid
#         folders = os.path.normpath(mid).split(os.path.sep)
#         self.folders = folders
#         self.topfolder = folders[0]
#         if len(folders) > 1:
#             self.secondfolder = folders[1]

#     def fixMidFolder(self):
#         temp = self.folders
#         temp[0] = self.topfolder
#         if self.secondfolder != '':
#             if len(temp) > 1:
#                 temp[1] = self.secondfolder
#             else:
#                 temp.append(self.secondfolder)
#         return os.path.join(*temp)

#     def updateForcedname(self, name):
#         self.forcedname = name

#     def fixFinalName(self):
#         if self.forcedname != "":
#             return self.forcedname + self.ext
#         else:
#             return self.name + self.ext

#     def updateFinalPath(self, path):
#         self.finalpath = path
#         self.finalfolder = os.path.dirname(path)

#     def parse(self):
#         # 正确的剧集命名
#         season, ep = matchSeries(self.name)
#         if isinstance(season, int) and season > -1 and isinstance(ep, int) and ep > -1:
#             self.isepisode = True
#             self.season = season
#             self.epnum = ep
#             self.originep = 'Pass'
#             return
#         # 是否是需要修正的剧集命名
#         originep = matchEpPart(self.name)
#         if originep:
#             epresult = extractEpNum(originep)
#             if epresult:
#                 self.isepisode = True
#                 self.originep = originep
#                 self.epnum = epresult

#     def fixEpName(self, season):
#         if not self.epnum and self.forcedseason:
#             logger.debug("强制`season`后,尝试获取`ep`")
#             sep = simpleMatchEp(self.name)
#             if sep:
#                 self.epnum = sep
#                 self.originep = 'Pass'
#             else:
#                 return
#         if isinstance(self.epnum, int):
#             prefix = "S%02dE%02d" % (season, self.epnum)
#         else:
#             prefix = "S%02dE" % (season) + self.epnum

#         if self.originep == 'Pass':
#             if prefix in self.name:
#                 return
#             else:
#                 self.name = prefix
#         else:
#             if self.originep[0] == '.':
#                 renum = "." + prefix + "."
#             elif self.originep[0] == '[':
#                 renum = " " + prefix + " "
#             else:
#                 renum = " " + prefix + " "
#             logger.debug("替换内容:" + renum)
#             newname = self.name.replace(self.originep, renum)
#             self.name = newname
#             logger.info("替换后:   {}".format(newname))


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
        self.parent_folder, self.filename = os.path.split(filepath)
        self.base_name, self.file_extension = os.path.splitext(self.filename)

        # 文件路径相关属性
        self.root_folder = ''
        self.folder_segments = []
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
        relative_path = self.parent_folder.replace(root_folder, '').lstrip('\\/')
        self.folder_segments = os.path.normpath(relative_path).split(os.path.sep)
        self.top_folder = self.folder_segments[0] if self.folder_segments else ''
        self.second_folder = self.folder_segments[1] if len(self.folder_segments) > 1 else ''

    def parse_episode_info(self):
        """解析文件名中的剧集信息"""
        # 尝试匹配标准剧集格式
        season, episode = matchSeries(self.base_name)
        if isinstance(season, int) and season > -1 and isinstance(episode, int) and episode > -1:
            self.is_episode = True
            self.season_number = season
            self.episode_number = episode
            self.original_episode_marker = 'Pass'
            return

        # 尝试匹配非标准剧集格式
        episode_marker = matchEpPart(self.base_name)
        if episode_marker:
            episode_num = extractEpNum(episode_marker)
            if episode_num:
                self.is_episode = True
                self.original_episode_marker = episode_marker
                self.episode_number = episode_num


class TargetFileInfo():
    """ 目标文件信息 """

    def __init__(self, root_folder):
        self.root_folder: str = root_folder
        self.filename: str = ''
        self.base_name: str = ''
        self.file_extension: str = ''

        self.is_episode: bool = False
        self.forced_season: bool = False
        self.season_number: int = -1
        self.forced_episode: bool = False
        self.episode_number: int = -1

        self.top_folder: str = ''
        self.second_folder: str = ''
        # 最终文件路径
        self.full_path: str = ''

    def ForcedUpdate(self, is_episode: bool, season_number: int, episode_number: int):
        """ 强制更新 """
        # 如果 record 中定义了剧集信息，则使用 record 中的信息
        if is_episode:
            self.is_episode = True
            if season_number > -1:
                self.forced_season = True
                self.season_number = season_number
            if episode_number > -1:
                self.forced_episode = True
                self.episode_number = episode_number

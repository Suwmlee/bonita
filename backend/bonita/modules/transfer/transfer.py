# -*- coding: utf-8 -*-
'''
'''
import os
import logging

from bonita.utils.fileinfo import BasicFileInfo, TargetFileInfo
from bonita.utils.regex import matchSeason, simpleMatchEp
from bonita.utils.filehelper import OperationMethod, linkFile, video_type, ext_type, replaceRegex, replaceCJK, cleanbyNameSuffix, moveSubs

logger = logging.getLogger(__name__)


def findAllVideos(root, src_folder, escape_folder, mode=1):
    """ find all videos
    :param root: 递归的根目录
    :param src_folder: 源目录
    :param escape_folder: 跳过目录
    :param mode: 1 返回 BasicFileInfo 合集 2 返回 realPath 合集
    """
    if os.path.basename(root) in escape_folder:
        return []
    total = []
    dirs = os.listdir(root)
    for entry in dirs:
        f = os.path.join(root, entry)
        if os.path.isdir(f):
            total += findAllVideos(f, src_folder, escape_folder, mode)
        elif os.path.splitext(f)[1].lower() in video_type:
            if mode == 1:
                fi = BasicFileInfo(f)
                fi.set_root_folder(src_folder)
                total.append(fi)
            elif mode == 2:
                total.append(f)
    return total


def _handle_group_naming(original_file: BasicFileInfo, target_file: TargetFileInfo, file_list: list):
    """处理特殊组的视频文件命名
    :param original_file: 当前处理的文件信息
    :param target_file: 输出文件信息
    :param file_list: 所有待处理的文件列表
    """
    # CMCT组视频文件命名通常比文件夹命名更规范
    if 'CMCT' not in original_file.top_folder:
        return
    epfiles = [x for x in file_list if x.is_episode]
    if epfiles:
        # 如果有剧集标记则返回
        return
    namingfiles = [x for x in file_list if 'CMCT' in x.basename]
    if len(namingfiles) == 1:
        # 非剧集情况下使用文件名作为文件夹名
        target_file.top_folder = namingfiles[0].basename
        logger.debug(f"[-] handling cmct midfolder [{target_file.top_folder}]")


def _simplify_folder_name(original: str):
    """简化文件夹名称
    1. 替换CJK字符
    2. 处理特殊模式
    3. 移除常见标签词
    """
    minlen = 20
    tempmid = replaceCJK(original)
    tempmid = replaceRegex(tempmid, "^s(\\d{2})-s(\\d{2})")
    # 处理常见标签词 TODO 可增加过滤词
    grouptags = ['cmct', 'wiki', 'frds', '1080p', 'x264', 'x265']
    for gt in grouptags:
        if gt in tempmid.lower():
            minlen += len(gt)
    if len(tempmid) > minlen:
        logger.debug(f"[-] replace CJK [{tempmid}]")
        return tempmid
    return original


def _fix_series_naming(original_file: BasicFileInfo, target_file: TargetFileInfo):
    """ 修正剧集命名
    处理季数和集数的命名规范化
    :param original_file: 原始文件信息
    :param target_file: 目标文件信息
    """
    logger.debug("[-] fix series name")
    tmp_season = target_file.season_number if target_file.forced_season else original_file.season_number
    tmp_episode = target_file.episode_number if target_file.forced_episode else original_file.episode_number
    tmp_secondfolder = original_file.second_folder
    tmp_filename = original_file.basename
    tmp_original_marker = original_file.original_episode_marker
    # 如果已有有效的季数和集数记录，直接使用
    if tmp_season > -1 and tmp_episode > -1:
        marker = f"S{tmp_season:02d}E{tmp_episode:02d}"
        if marker not in tmp_filename:
            tmp_filename = marker
    # 没有完整的季数和集数
    # 季数最重要，季数涉及到中间的文件夹，集数可以使用自身的名称
    elif tmp_season > -1 and tmp_episode == -1:
        tmp_filename, tmp_episode = fix_episode_name(tmp_filename, tmp_season, tmp_episode, tmp_original_marker)
    else:
        find_season = matchSeason(original_file.basefolder)
        if find_season:
            tmp_season = find_season
            tmp_filename, tmp_episode = fix_episode_name(tmp_filename, find_season, tmp_episode, tmp_original_marker)
        else:
            # 父级未发现season标记，二级目录为空则可能为单季，默认第一季
            if tmp_secondfolder == '':
                tmp_season = 1
                tmp_filename, tmp_episode = fix_episode_name(tmp_filename, tmp_season, tmp_episode, tmp_original_marker)
            else:
                # 存在一些特殊标记，可能为特典
                special_tags = ['花絮', '特典', '特辑', '特典', 'extra', 'special', '[sp]']
                if any(x in tmp_secondfolder for x in special_tags):
                    tmp_season = 0
                    tmp_filename, tmp_episode = fix_episode_name(
                        tmp_filename, tmp_season, tmp_episode, tmp_original_marker)

    target_file.season_number = tmp_season
    target_file.episode_number = tmp_episode
    target_file.second_folder = "Specials" if tmp_season == 0 else f"Season {tmp_season}"
    target_file.basename = tmp_filename
    return


def fix_episode_name(name: str, season: int, episode: int, original_marker: str):
    """ 修正单集命名

    Args:
        name: 文件名
        season: 季数(必须 > -1)
        episode: 集数(可能为-1)
        original_marker: 匹配时的原始字符串

    Returns:
        str: 修正后的文件名
    """
    if episode == -1:
        logger.debug("没有`episode`，尝试获取")
        sep = simpleMatchEp(name)
        if sep:
            episode = sep
            original_marker = "Pass"
        else:
            return name, episode

    # 此时 episode 肯定有值
    marker = f"S{season:02d}E{episode:02d}"
    if original_marker == "Pass":
        if marker in name:
            return name, episode
        else:
            return marker, episode
    else:
        # 原始匹配的 marker 是 [S01E01] 这种格式
        # 修正替换
        if original_marker[0] == ".":
            renum = "." + marker + "."
        elif original_marker[0] == "[":
            renum = " " + marker + " "
        else:
            renum = " " + marker + " "
        logger.debug("替换内容:" + renum)
        newname = name.replace(original_marker, renum)
        logger.info("替换后:   {}".format(newname))
        return newname, episode


def transferfile(original_file: BasicFileInfo,
                 target_file: TargetFileInfo,
                 optimize_name_tag: bool, series_tag: bool,
                 file_list: list, linktype: OperationMethod):
    """
    转移文件
    """
    target_file.top_folder = original_file.top_folder
    target_file.second_folder = original_file.second_folder
    target_file.basename = original_file.basename
    target_file.file_extension = original_file.file_extension

    _handle_group_naming(original_file, target_file, file_list)
    if optimize_name_tag:
        target_file.top_folder = _simplify_folder_name(original_file.top_folder)

    # 当前设置类型是剧集
    if series_tag and (target_file.is_episode or original_file.is_episode):
        _fix_series_naming(original_file, target_file)

    target_file.filename = target_file.basename + target_file.file_extension

    folder_path = os.path.join(target_file.root_folder, target_file.top_folder, target_file.second_folder)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    cleanbyNameSuffix(folder_path, target_file.basename, ext_type)
    target_file.full_path = transSingleFile(original_file, folder_path, target_file.basename, linktype)

    return target_file


def transSingleFile(original_file: BasicFileInfo, output_folder, target_filename, linktype: OperationMethod):
    """ 转移单个文件
    """
    dest_path = os.path.join(output_folder, target_filename + original_file.file_extension)
    linkFile(original_file.full_path, dest_path, linktype)
    moveSubs(original_file.parent_folder, output_folder, original_file.basename, target_filename)

    return dest_path

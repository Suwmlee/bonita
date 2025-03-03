# -*- coding: utf-8 -*-
'''
'''
import os
import re
import time
import logging

from bonita.modules.transfer.fileinfo import FileInfo
from bonita.utils.regex import extractEpNum, matchSeason, matchEpPart, matchSeries, simpleMatchEp
from bonita.utils.filehelper import OperationMethod, linkFile, video_type, ext_type, replaceRegex, cleanFolderWithoutSuffix, \
    replaceCJK, cleanbyNameSuffix, cleanExtraMedia, moveSubs

logger = logging.getLogger(__name__)


def findAllVideos(root, src_folder, escape_folder, mode=1):
    """ find all videos
    mode:
    :1  返回 FileInfo 合集
    :2  返回 realPath 合集
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
                fi = FileInfo(f)
                midfolder = fi.realfolder.replace(src_folder, '').lstrip("\\").lstrip("/")
                fi.updateMidFolder(midfolder)
                if fi.topfolder != '.':
                    fi.parse()
                total.append(fi)
            elif mode == 2:
                total.append(f)
    return total


def transfer(src_folder, dest_folder,
             linktype, prefix,
             specified_files='',
             escape_folders="",
             clean_others_tag=True,
             simplify_tag=False,
             fixseries_tag=False
             ):
    """
    如果 specified_files 有值，则使用 specified_files 过滤文件且不清理其他文件
    """

    try:
        movie_list = []

        if not specified_files or specified_files == '':
            movie_list = findAllVideos(src_folder, src_folder, re.split("[,，]", escape_folders))
        else:
            if not os.path.exists(specified_files):
                specified_files = os.path.join(src_folder, specified_files)
                if not os.path.exists(specified_files):
                    logger.error("[!] specified_files not exists")
                    return False
            clean_others_tag = False
            if os.path.isdir(specified_files):
                movie_list = findAllVideos(specified_files, src_folder, re.split("[,，]", escape_folders))
            else:
                tf = FileInfo(specified_files)
                midfolder = tf.realfolder.replace(src_folder, '').lstrip("\\").lstrip("/")
                tf.updateMidFolder(midfolder)
                if tf.topfolder != '.':
                    tf.parse()
                movie_list.append(tf)
        count = 0
        total = str(len(movie_list))
        logger.debug('[+] Find  ' + total+'  movies')

        # 硬链接直接使用源目录
        if linktype == 1:
            prefix = src_folder
        # 清理目标目录下的文件:视频 字幕
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        if clean_others_tag:
            dest_list = findAllVideos(dest_folder, '', [], 2)
        else:
            dest_list = []

        for currentfile in movie_list:
            if not isinstance(currentfile, FileInfo):
                continue
            # task = taskService.getTask('transfer')
            # task = dict()
            # if task.status == 0:
            #     return False
            count += 1
            logger.debug('[!] - ' + str(count) + '/' + total + ' -')
            logger.debug("[+] start check [{}] ".format(currentfile.realpath))

            # 修正后给链接使用的源地址
            link_path = os.path.join(src_folder, currentfile.midfolder, currentfile.realname)

            # currentrecord = transrecordService.add(currentfile.realpath)
            # 根据历史记录进行预处理，标记、锁定、剧集

            # 优化命名
            naming(currentfile, movie_list, simplify_tag, fixseries_tag)

            if currentfile.topfolder == '.':
                newpath = os.path.join(dest_folder, currentfile.fixFinalName())
            else:
                newpath = os.path.join(dest_folder, currentfile.fixMidFolder(), currentfile.fixFinalName())
            currentfile.updateFinalPath(newpath)
            if linktype == 0:
                linkFile(link_path, newpath, 1)
            else:
                linkFile(link_path, newpath, 2)

            # 使用最终的文件名
            cleanbyNameSuffix(currentfile.finalfolder, currentfile.name, ext_type)
            oldname = os.path.splitext(currentfile.realname)[0]
            moveSubs(currentfile.realfolder, currentfile.finalfolder, oldname, currentfile.name)

            # if os.path.exists(currentrecord.destpath) and newpath != currentrecord.destpath:
            #     # 清理之前转移的文件
            #     transrecordService.deleteRecordFiles(currentrecord, False)

            if newpath in dest_list:
                dest_list.remove(newpath)

            logger.info("[-] transfered [{}]".format(newpath))
            # need rest 100ms
            time.sleep(0.1)

        if clean_others_tag:
            for torm in dest_list:
                logger.info("[!] remove other file: [{}]".format(torm))
                os.remove(torm)
            cleanExtraMedia(dest_folder)
            cleanFolderWithoutSuffix(dest_folder, video_type)

        logger.info("transfer finished")
    except Exception as e:
        logger.error(e)

    return True


def naming(currentfile: FileInfo, movie_list: list, simplify_tag, fixseries_tag):
    """处理文件命名优化
    Args:
        currentfile (FileInfo): 当前处理的文件信息
        movie_list (list): 所有待处理的文件列表
        simplify_tag (bool): 是否简化文件夹名称
        fixseries_tag (bool): 是否修正剧集命名
    """
    if not currentfile.locked:
        _handle_group_naming(currentfile, movie_list)
        if simplify_tag:
            _simplify_folder_name(currentfile)

    if fixseries_tag and currentfile.isepisode:
        _fix_series_naming(currentfile)


def _handle_group_naming(currentfile: FileInfo, movie_list: list):
    """处理特殊组的视频文件命名
    """
    # CMCT组视频文件命名通常比文件夹命名更规范
    if 'CMCT' not in currentfile.topfolder:
        return

    matches = [x for x in movie_list if x.topfolder == currentfile.topfolder]
    if not matches:
        return

    # 检测是否有剧集标记
    epfiles = [x for x in matches if x.isepisode]
    if epfiles:
        return

    namingfiles = [x for x in matches if 'CMCT' in x.name]
    if len(namingfiles) == 1:
        # 非剧集情况下使用文件名作为文件夹名
        for m in matches:
            m.topfolder = namingfiles[0].name
        logger.debug("[-] handling cmct midfolder [{}]".format(currentfile.midfolder))


def _simplify_folder_name(currentfile: FileInfo):
    """简化文件夹名称
    1. 替换CJK字符
    2. 处理特殊模式
    3. 移除常见标签词
    """
    minlen = 20
    tempmid = currentfile.topfolder
    tempmid = replaceCJK(tempmid)
    tempmid = replaceRegex(tempmid, "^s(\\d{2})-s(\\d{2})")

    # 处理常见标签词
    grouptags = ['cmct', 'wiki', 'frds', '1080p', 'x264', 'x265']
    for gt in grouptags:
        if gt in tempmid.lower():
            minlen += len(gt)

    if len(tempmid) > minlen:
        logger.debug("[-] replace CJK [{}]".format(tempmid))
        currentfile.topfolder = tempmid


def _fix_series_naming(currentfile: FileInfo):
    """修正剧集命名
    处理季数和集数的命名规范化
    """
    logger.debug("[-] fix series name")

    # 如果已有有效的季数和集数记录，直接使用
    if _has_valid_season_episode(currentfile):
        _apply_season_folder(currentfile)
        return

    # 尝试从现有信息获取季数
    seasonnum = _get_season_number(currentfile)
    if seasonnum:
        _apply_season_number(currentfile, seasonnum)
    else:
        _handle_default_season(currentfile)


def _has_valid_season_episode(currentfile: FileInfo):
    """检查是否有有效的季数和集数记录"""
    return (isinstance(currentfile.season, int) and isinstance(currentfile.epnum, int)
            and currentfile.season > -1 and currentfile.epnum > -1)


def _apply_season_folder(currentfile: FileInfo):
    """应用季文件夹命名"""
    if currentfile.season == 0:
        currentfile.secondfolder = "Specials"
    else:
        currentfile.secondfolder = "Season " + str(currentfile.season)
    try:
        currentfile.fixEpName(currentfile.season)
    except:
        currentfile.name = "S%02dE%02d" % (currentfile.season, currentfile.epnum)


def _get_season_number(currentfile: FileInfo):
    """获取季数
    1. 优先使用已有season
    2. 尝试从目录名解析
    """
    if isinstance(currentfile.season, int) and currentfile.season > -1:
        return currentfile.season

    # 检测视频上级目录是否有season标记
    dirfolder = currentfile.folders[len(currentfile.folders)-1]
    return matchSeason(dirfolder)


def _apply_season_number(currentfile: FileInfo, seasonnum: int):
    """应用季数信息"""
    currentfile.season = seasonnum
    currentfile.secondfolder = "Season " + str(seasonnum)
    currentfile.fixEpName(seasonnum)


def _handle_default_season(currentfile: FileInfo):
    """处理默认季数情况"""
    if currentfile.secondfolder == '':
        # 如果检测不到seasonnum可能是多季，默认第一季
        currentfile.season = 1
        currentfile.secondfolder = "Season " + str(1)
        currentfile.fixEpName(1)
    else:
        try:
            # 处理特典/花絮
            dirfolder = currentfile.folders[len(currentfile.folders)-1]
            if '花絮' in dirfolder and currentfile.topfolder != '.':
                currentfile.secondfolder = "Specials"
                currentfile.season = 0
                currentfile.fixEpName(0)
        except Exception as ex:
            logger.error(ex)


def transferfile(currentfile: FileInfo, src_folder, simplify_tag, fixseries_tag, dest_folder,
                 movie_list, linktype):
    """
    转移文件
    """
    destpath = ""

    # 修正后给链接使用的源地址
    link_path = os.path.join(src_folder, currentfile.midfolder, currentfile.realname)

    # currentrecord = transrecordService.add(currentfile.realpath)
    # 根据历史记录进行预处理，标记、锁定、剧集

    # 优化命名
    naming(currentfile, movie_list, simplify_tag, fixseries_tag)

    if currentfile.topfolder == '.':
        destpath = os.path.join(dest_folder, currentfile.fixFinalName())
    else:
        destpath = os.path.join(dest_folder, currentfile.fixMidFolder(), currentfile.fixFinalName())
    currentfile.updateFinalPath(destpath)
    linkFile(link_path, destpath, linktype)

    # 使用最终的文件名
    cleanbyNameSuffix(currentfile.finalfolder, currentfile.name, ext_type)
    oldname = os.path.splitext(currentfile.realname)[0]
    moveSubs(currentfile.realfolder, currentfile.finalfolder, oldname, currentfile.name)

    return destpath


def transSingleFile(currentfile: FileInfo, output_folder, prefilename, linktype: OperationMethod):
    """ 转移单个文件
    """
    dest_path = os.path.join(output_folder, prefilename + currentfile.ext)
    linkFile(currentfile.realpath, dest_path, linktype)
    oldname = os.path.splitext(currentfile.realname)[0]
    moveSubs(currentfile.realfolder, output_folder, oldname, prefilename)

    return dest_path

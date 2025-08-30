# -*- coding: utf-8 -*-
import os
import pathlib
import re
import errno
import shutil
import stat
import logging
from enum import Enum as PyEnum

video_type = set(['.mp4', '.avi', '.rmvb', '.wmv', '.strm',
                  '.mov', '.mkv', '.flv', '.ts', '.m2ts', '.webm', '.iso'])
subext_type = set(['.ass', '.srt', '.sub', '.ssa', '.smi', '.idx', '.sup',
                   '.psb', '.usf', '.xss', '.ssf', '.rt', '.lrc', '.sbv', '.vtt', '.ttml'])

video_filter = set(['*.mp4', '*.avi', '*.rmvb', '*.wmv', '*.strm',
                    '*.mov', '*.mkv', '*.flv', '*.ts', '*.m2ts', '*.webm', '*.iso'])
ext_filter = set(['*.ass', '*.srt', '*.sub', '*.ssa', '*.smi', '*.idx', '*.sup',
                  '*.psb', '*.usf', '*.xss', '*.ssf', '*.rt', '*.lrc', '*.sbv', '*.vtt', '*.ttml'])

logger = logging.getLogger(__name__)


class OperationMethod(PyEnum):
    """ 操作类型: 1. 硬链接 2. 软链接 3. 移动 4. 复制
    """
    HARD_LINK = 1
    SYMLINK = 2
    MOVE = 3
    COPY = 4


def findAllFilesWithSuffix(root, suffix, escape_folder: list[str] = [], escape_file: list[str] = []):
    """ 查找root目录下的所有文件
    :param root: 根目录
    :param suffix: 后缀列表
    :param escape_folder: 跳过目录列表
    :param escape_file: 跳过文件列表
    """
    default_exclude_folder = ['@eaDir']
    default_exclude_file = ['.DS_Store', '.drive_sync']
    escape_folder.extend(default_exclude_folder)
    escape_file.extend(default_exclude_file)
    escape_folder = set(escape_folder)
    escape_file = set(escape_file)

    suffix = set(s.lower() for s in suffix)
    result = []
    try:
        for path, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in escape_folder]
            for file in files:
                if file in escape_file:
                    continue
                file_suffix = os.path.splitext(file)[1].lower()
                if file_suffix in suffix:
                    result.append(os.path.join(path, file))
    except Exception as e:
        logger.error(f"[!] findAllFilesWithSuffix failed {root}")
        logger.error(e)
    return result


def has_video_files(directory_path: str) -> bool:
    """检查目录中是否存在视频文件

    Args:
        directory_path: 要检查的目录路径

    Returns:
        bool: 如果目录中存在视频文件返回True，否则返回False
    """
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        logger.warning(f"Directory does not exist or is not a directory: {directory_path}")
        return False
    try:
        video_files = findAllFilesWithSuffix(directory_path, video_type)
        return len(video_files) > 0
    except Exception as e:
        logger.error(f"Error checking for video files in directory {directory_path}: {str(e)}")
        # 如果检查出错，默认返回True以防止误删
        return True


def cleanFilebyNameSuffix(root, basename, suffixes):
    """ 删除指定目录下文件名以basename开头且后缀匹配的文件
    :param root: 根目录路径
    :param basename: 文件名前缀
    :param suffixes: 文件后缀，可以是单一字符串或字符串集合
    """
    try:
        for file in os.scandir(root):
            path = file.path
            if file.is_dir():
                cleanFilebyNameSuffix(path, basename, suffixes)
            elif file.is_file():
                fname, ext = os.path.splitext(file.name)
                if ext.lower() in suffixes and fname.startswith(basename):
                    logger.debug(f"Removing file: {path}")
                    os.remove(path)
    except PermissionError as e:
        logger.warning(f"Permission denied: {e}")
    except OSError as e:
        logger.error(f"OS error occurred: {e}")


def cleanFolderWithoutSuffix(root, suffixes):
    """ 删除指定目录下不包含指定后缀文件的目录及其子目录
    :param root: 根目录路径
    :param suffixes: 文件后缀集合
    """
    has_suffix = False
    try:
        for entry in os.scandir(root):
            path = entry.path
            if entry.is_dir():
                if cleanFolderWithoutSuffix(path, suffixes):
                    has_suffix = True
            elif entry.is_file():
                _, ext = os.path.splitext(entry.name)
                if ext.lower() in suffixes:
                    has_suffix = True
                    break
        if not has_suffix:
            logger.info(f"Removing folder without target suffixes: {root}")
            shutil.rmtree(root, ignore_errors=True)
    except PermissionError as e:
        logger.warning(f"Permission denied: {e}")
        return True
    except OSError as e:
        logger.error(f"OS error occurred: {e}")
        return True
    return has_suffix


def cleanFilebyFilter(root, filter):
    """ 根据过滤名删除文件

    只当前目录,不递归删除
    未含分集标识的filter不能删除带有分集标识的文件
    """
    try:
        dirs = os.scandir(root)
        for file in dirs:
            filename = file.name
            fullpath = file.path
            if file.is_file():
                if filename.startswith(filter):
                    # 未分集到分集 重复删除分集内容
                    if '-CD' in filename.upper():
                        if '-CD' in filter.upper():
                            logger.info("clean file [{}]".format(fullpath))
                            os.remove(fullpath)
                    else:
                        logger.info("clean file [{}]".format(fullpath))
                        os.remove(fullpath)
    except Exception as e:
        logger.error(f"[-] cleanFilebyFilter failed {root} {filter}")
        logger.error(e)


def moveSubs(srcfolder, destfolder, basename, newname, saved=True):
    """ 移动字幕
    :param saved    True: 复制字幕  False: 移动字幕
    """
    dirs = os.scandir(srcfolder)
    for file in dirs:
        filename = file.name
        filepath = file.path
        if file.is_dir():
            continue
        (path, ext) = os.path.splitext(filename)
        if ext.lower() in subext_type and path.startswith(basename):
            newpath = path.replace(basename, newname)
            logger.debug("[-] - copy sub  " + filepath)
            newfile = os.path.join(destfolder, newpath + ext)
            if saved:
                shutil.copyfile(filepath, newfile)
            else:
                shutil.move(filepath, newfile)
            # modify permission
            os.chmod(newfile, stat.S_IRWXU | stat.S_IRGRP |
                     stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)


def forceSymlink(srcpath, dstpath):
    """ create symlink
    https://stackoverflow.com/questions/8299386/modifying-a-symlink-in-python
    """
    try:
        os.symlink(srcpath, dstpath)
    except OSError as e:
        if e.errno == errno.EEXIST:
            os.remove(dstpath)
            os.symlink(srcpath, dstpath)
        else:
            raise e


def forceHardlink(srcpath, dstpath):
    """ create hard link
    """
    try:
        os.link(srcpath, dstpath)
    except OSError as e:
        if e.errno == errno.EEXIST:
            os.remove(dstpath)
            os.link(srcpath, dstpath)
        else:
            raise e


def checkFileExists(filepath):
    """ 检测文件是否存在
    软/硬链接
    """
    if os.path.exists(filepath):
        return True
    elif pathlib.Path(filepath).is_symlink():
        return True
    else:
        return False


def linkFile(srcpath, dstpath, operation: OperationMethod):
    """ 链接文件
    params: linktype: 操作方式

    https://stackoverflow.com/questions/41941401/how-to-find-out-if-a-folder-is-a-hard-link-and-get-its-real-path
    """
    if os.path.exists(dstpath) and os.path.samefile(srcpath, dstpath) and operation == OperationMethod.HARD_LINK:
        logger.debug("[!] same file already exists")
    elif pathlib.Path(dstpath).is_symlink() and os.readlink(dstpath) == srcpath and operation == OperationMethod.SYMLINK:
        logger.debug("[!] link file already exists")
    else:
        dstfolder = os.path.dirname(dstpath)
        if not os.path.exists(dstfolder):
            os.makedirs(dstfolder)
        logger.debug("[-] create link from [{}] to [{}]".format(srcpath, dstpath))
        if operation == OperationMethod.SYMLINK:
            forceSymlink(srcpath, dstpath)
        elif operation == OperationMethod.HARD_LINK:
            forceHardlink(srcpath, dstpath)
        elif operation == OperationMethod.MOVE:
            shutil.move(srcpath, dstpath)
        elif operation == OperationMethod.COPY:
            shutil.copyfile(srcpath, dstpath)


def replaceCJK(base: str):
    """ 尝试替换 CJK 字符
    https://stackoverflow.com/questions/1366068/whats-the-complete-range-for-chinese-characters-in-unicode

    https://www.unicode.org/charts/charindex.html

    eg: 你好  [4k修复] (实例1)
    """
    tmp = base
    for n in re.findall(r'[\(\[\（](.*?)[\)\]\）]', base):
        if re.findall(r'[\u3000-\u33FF\u4e00-\u9fff]+', n):
            try:
                # Escape special regex characters in 'n'
                escaped_n = re.escape(n)
                cop = re.compile(r"[\(\[\（]" + escaped_n + r"[\)\]\）]")
                tmp = cop.sub('', tmp)
            except Exception as e:
                print(f"replaceCJK error occurred: {e}")
                pass
    tmp = re.sub(r'[\u3000-\u33FF\u4e00-\u9fff]+', '', tmp)
    tmp = cleanParentheses(tmp)
    tmp = re.sub(r'(\W)\1+', r'\1', tmp).lstrip(' !?@#$.:：]）)').rstrip(' !?@#$.:：[(（')
    return tmp


def cleanParentheses(text: str) -> str:
    """清理多余的括号"""
    while '()' in text or '[]' in text or '（）' in text:
        text = text.replace('()', '').replace('[]', '').replace('（）', '')
    return text


def replaceRegex(base: str, regex: str):
    cop = re.compile(regex, re.IGNORECASE | re.X | re.S)
    base = cop.sub('', base)
    base = re.sub(r'(\W)\1+', r'\1', base).lstrip(' !?@#$.:：]）)').rstrip(' !?@#$.:：[(（')
    return base


def is_video_file(filepath: str) -> bool:
    """Check if the file is a video file"""
    ext = os.path.splitext(filepath)[1].lower()
    is_video = ext in video_type
    if not is_video:
        logger.debug(f"File {filepath} is not a video file")
    return is_video

def sanitize_path(name: str) -> str:
    """
    清理字符串，使其可以作为合法的文件名或目录名。
    将Windows和Linux/macOS上非法的字符替换为下划线。
    """
    if not name:
        return ""
    # 替换在路径中非法的字符
    return re.sub(r'[\\/:*?"<>|]', '_', name)
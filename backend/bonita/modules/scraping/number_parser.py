import os
import re
import logging

G_spat = re.compile(
    r"^\w+\.(cc|com|net|me|club|jp|tv|xyz|biz|wiki|info|tw|us|de)@|^22-sht\.me|"
    r"^(fhd|hd|sd|1080p|720p|4K)(-|_)|"
    r"(-|_)(fhd|hd|sd|1080p|720p|4K|x264|x265|uncensored|hack|leak)",
    re.IGNORECASE)

# 预编译常用正则表达式
# -EP01 是分集命名，编号固定补零到两位
RE_EPISODE_PART = re.compile(r"(?:-|_)ep(\d{2,})(?![a-z0-9])", re.IGNORECASE)
RE_NUMBER_PART = re.compile(r"(?:-|_)(\d{1,2})$", re.IGNORECASE | re.X | re.S)
RE_OUMEI = re.compile(r'[a-zA-Z]+\.\d{2}\.\d{2}\.\d{2}')
RE_FILENAME = re.compile(r'[\w\-_]+', re.A)
RE_SUB_C = re.compile(r"(-|_)c$", re.IGNORECASE)
RE_CH_CHECK = re.compile(r"\d+ch$", re.I)
RE_BASENAME_SEARCH = re.compile(r'([^<>/\\\\|:""\\*\\?]+)\\.\\w+$')
RE_BASENAME_FINDALL = re.compile(r'(.+?)\.')
RE_UNCENSORED_CHECK = re.compile(
    r'[\d-]{4,}|\d{6}_\d{2,3}|(cz|gedo|k|n|red-|se)\d{2,4}|heyzo.+|xxx-av-.+|heydouga-.+|x-art\.\d{2}\.\d{2}\.\d{2}',
    re.I
)


# 旁边字幕：没写语言，或写成这些中文标记，才算中文字幕。ja、en 以及其他标记都不算。
_SIDECAR_CHINESE = re.compile(
    r"(?:^|[.\-_])(?:zh[-_]?hant|zh[-_]?hans|zh[-_]?tw|zh[-_]?cn|zhs|zht|chs|cht|chi|chn|chinese|sc|tc|zh|cn|c|中文|字幕)(?=$|[.\-_])",
    re.I,
)
# -U、-UC、-hack 是独立的一段。uncut、UHDrip 里的 u 不算破解。
_HACK_MARKER = re.compile(r"(?:^|[.\-_])(?:hack|uc|u)(?=$|[.\-_])|破解", re.I)


def _sidecar_has_chinese(filepath: str) -> bool:
    """ 视频旁边没写语言，或写了中文标记的同名字幕，算有中文字幕。 """
    folder = os.path.dirname(filepath) or ""
    basename = os.path.splitext(os.path.basename(filepath))[0]
    if not folder or not basename or not os.path.isdir(folder):
        return False
    from bonita.utils.filehelper import subext_type

    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                if not entry.is_file():
                    continue
                stem, ext = os.path.splitext(entry.name)
                if ext.lower() not in subext_type or not stem.startswith(basename):
                    continue
                rest = stem[len(basename):]
                if rest and rest[0] not in ".-_":
                    continue
                if rest == "" or _SIDECAR_CHINESE.search(rest):
                    return True
    except OSError:
        return False
    return False


def format_part_suffix(part_number) -> str:
    """ 生成分集后缀，如 -EP01

    -CD1 需要每部影片独占目录才会被 Emby/Jellyfin 合并，实际命中率低；
    改用集数形式让每个分片成为独立条目，EP 前缀比单个 E 更不易误匹配
    """
    try:
        part_number = int(part_number)
    except (TypeError, ValueError):
        return ''
    if part_number <= 0:
        return ''
    return f"-EP{part_number:02d}"


class FileNumInfo():
    """ 解析文件番号信息
    """

    def __init__(self, filepath: str):
        if not filepath:
            self.num = None
            return

        self.num = get_number(filepath)

        # 初始化所有标签
        self.chs_tag = False        # 中文字幕
        self.uncensored_tag = False  # 番号本身是无码
        self.filename_uncensored = False  # 文件名里写了 uncensored
        self.leak_tag = False       # 流出
        self.hack_tag = False       # 破解
        self.partNumber = 0         # 部分编号

        # 检查番号是否存在及是否无码
        if not self.num:
            return

        if is_uncensored(self.num):
            self.uncensored_tag = True

        # 转为小写以便检查
        filepath_lower = filepath.lower()

        # 流出只看 leak / 流出。uncensored 是无码，其中的 -u 不能再记成破解
        if any(term in filepath_lower for term in ['流出', '-leak', '_leak']):
            self.leak_tag = True
        if 'uncensored' in filepath_lower:
            self.filename_uncensored = True

        if _has_hack_marker(filepath_lower):
            self.hack_tag = True

        # 检查是否有中文字幕
        cn_indicators = ['中文', '字幕', '-c.', '_c.', '_c_', '-c-', '-uc', '_uc']
        if any(indicator in filepath_lower for indicator in cn_indicators) or \
           re.search(r'[-_]C(\.\w+$|-\w+)|\d+ch(\.\w+$|-\w+)', filepath_lower, re.I):
            self.chs_tag = True
        elif _sidecar_has_chinese(filepath):
            self.chs_tag = True

        self.partNumber = self.checkPart(os.path.basename(filepath))

    def version(self):
        """ 一份文件只保留一个版本。番号本身是无码时，不再采纳流出和破解。 """
        if not getattr(self, "num", None):
            return None
        if getattr(self, "uncensored_tag", False):
            return "uncensored"
        if getattr(self, "leak_tag", False):
            return "leak"
        if getattr(self, "hack_tag", False):
            return "hack"
        if getattr(self, "filename_uncensored", False):
            return "uncensored"
        return None

    def version_suffix(self) -> str:
        return version_suffix_for(self.version())

    def release_tags(self):
        """ 文件名识别出的字幕，以及互斥后的那一个版本标记。 """
        if not getattr(self, "num", None):
            return []
        tags = []
        if getattr(self, "chs_tag", False):
            tags.append("中文字幕")
        label = {"uncensored": "无码", "leak": "流出", "hack": "破解"}.get(self.version() or "")
        if label:
            tags.append(label)
        return tags

    @staticmethod
    def checkPart(filename):
        """ 解析文件名中的分集编号，非多集文件返回 0 """
        try:
            bname = os.path.splitext(filename)[0]
            for regex in (RE_EPISODE_PART, RE_NUMBER_PART):
                result = regex.search(bname)
                if result:
                    return int(result.group(1))
        except Exception:
            pass
        return 0


def get_number(file_path: str) -> str:
    """ 获取番号
    """
    try:
        basename = os.path.basename(file_path)
        file_subpath = os.path.dirname(file_path)
        file_subpath = os.path.basename(file_subpath)
        (filename, ext) = os.path.splitext(basename)
        file_number = rules_parser(filename)
        if file_number is None:
            # 文件名不包含，查看文件夹
            file_number = rules_parser(file_subpath)
        if file_number:
            return file_number

        if '字幕组' in filename or 'SUB' in filename.upper() or re.match(r'[\u30a0-\u30ff]+', filename):
            filename = G_spat.sub("", filename)
            filename = re.sub(r"\[.*?\]", "", filename)
            filename = filename.replace(".chs", "").replace(".cht", "")
            file_number = str(re.findall(r'(.+?)\.', filename)).strip(" [']")
            return file_number
        elif '-' in filename or '_' in filename:  # 普通提取番号 主要处理包含减号-和_的番号
            filename = G_spat.sub("", filename)
            filename = str(re.sub(r"\[\d{4}-\d{1,2}-\d{1,2}\] - ", "", filename))  # 去除文件名中时间
            filename = re.sub(r"[-_]ep\d{2,}(?![a-z0-9])", "", filename, flags=re.IGNORECASE)
            if not re.search("-|_", filename):  # 去掉分集后缀之后再无-的情况，例如n1012-EP01.wmv
                return str(re.search(r'\w+', filename[:filename.find('.')], re.A).group())
            file_number = os.path.splitext(filename)
            filename_match = RE_FILENAME.search(filename)
            if filename_match:
                file_number = str(filename_match.group())
            else:
                file_number = file_number[0]
            file_number = RE_SUB_C.sub("", file_number)
            if RE_CH_CHECK.search(file_number):
                file_number = file_number[:-2]
            return file_number.upper()
        else:  # 提取不含减号-的番号，FANZA CID
            # 欧美番号匹配规则
            oumei = RE_OUMEI.search(basename)
            if oumei:
                return oumei.group()
            try:
                return str(
                    RE_BASENAME_FINDALL.findall(
                        str(RE_BASENAME_SEARCH.search(basename).group()))).strip(
                    "['']").replace('_', '-')
            except:
                return str(RE_BASENAME_FINDALL.search(basename)[0])
    except Exception as e:
        logging.getLogger().error(e)
        return


# 预编译规则中的正则表达式
# 数字格式: 123456-123
RE_RULE_NUMERIC = re.compile(r'\d{6}(-|_)\d{2,3}', re.I)
# x-art日期格式: x-art.22.01.01
RE_RULE_XART = re.compile(r'x-art\.\d{2}\.\d{2}\.\d{2}', re.I)
# xxx-av系列: xxx-av-12345
RE_RULE_XXXAV = re.compile(r'xxx-av[^\d]*(\d{3,5})[^\d]*', re.I)
# heydouga系列: heydouga-1234-123
RE_RULE_HEYDOUGA = re.compile(r'(\d{4})[\-_](\d{3,4})[^\d]*', re.I)
# HEYZO系列: HEYZO-1234
RE_RULE_HEYZO = re.compile(r'heyzo[^\d]*(\d{4})', re.I)
# mdbk/mdtm系列: mdbk-123, mdtm-123
RE_RULE_MDX = re.compile(r'(mdbk|mdtm)(-|_)(\d{3,4})', re.I)
# s2mbd/s2m系列: s2mbd-123, s2m-123
RE_RULE_S2M = re.compile(r'(s2mbd|s2m)(-|_)(\d{3})', re.I)
# fc2系列: fc2-123456
RE_RULE_FC2 = re.compile(r'fc2(-|_)(\d{5,7})', re.I)
# 高清系列: carib-123456-123
RE_RULE_HD = re.compile(r'(carib|caribpr|1pon|pondo|10mu)[-_](\d{6})[-_](\d{3})', re.I)
# VR系列: h_1285vrkm-123
RE_RULE_VR = re.compile(r'(h_\d+vrkm)[-_](\d{3,4})', re.I)
# T28系列: t28-123
RE_RULE_T28 = re.compile(r't-?28[-_](\d{3})', re.I)
# 通用规则: 2-6个字母+3-4个数字 如: ABP-123
RE_RULE_GENERAL = re.compile(r'([A-Za-z]{2,6})\-?(\d{3,4})', re.I)

rules = [
    lambda x: RE_RULE_NUMERIC.search(x).group(),
    lambda x: RE_RULE_XART.search(x).group(),
    lambda x: ''.join(['xxx-av-', RE_RULE_XXXAV.findall(x)[0]]),
    lambda x: 'heydouga-' + '-'.join(RE_RULE_HEYDOUGA.findall(x)[0]),
    lambda x: 'HEYZO-' + RE_RULE_HEYZO.findall(x)[0],
    lambda x: RE_RULE_MDX.search(x).group(),
    lambda x: RE_RULE_S2M.search(x).group(),
    lambda x: RE_RULE_FC2.search(x).group(),
    lambda x: RE_RULE_HD.search(x).group(),
    lambda x: RE_RULE_VR.search(x).group(),
    lambda x: 'T28-' + RE_RULE_T28.search(x).group(1),
    lambda x: '-'.join(RE_RULE_GENERAL.search(x).groups()),
]


def rules_parser(filename: str):
    """解析文件名中的番号
    Args:
        filename: 文件名
    Returns:
        str: 提取的番号,未找到返回None
    """
    if not filename:
        return None

    filename = filename.upper()

    # 特殊处理FC2系列
    if 'FC2' in filename:
        filename = filename.replace('PPV', '').replace('--', '-').replace('_', '-').replace(' ', '')

    for rule in rules:
        try:
            file_number = rule(filename)
            if file_number:
                return file_number
        except Exception as e:
            # 静默失败，尝试下一个规则
            continue

    return None


class Cache_uncensored_conf:
    prefix = None

    def is_empty(self):
        return bool(self.prefix is None)

    def set(self, v: list):
        if not v or not len(v) or not len(v[0]):
            raise ValueError('input prefix list empty or None')
        s = v[0]
        if len(v) > 1:
            for i in v[1:]:
                s += f"|{i}.+"
        self.prefix = re.compile(s, re.I)

    def check(self, number):
        if self.prefix is None:
            raise ValueError('No init re compile')
        return self.prefix.match(number)


G_cache_uncensored_conf = Cache_uncensored_conf()


_NATIVE_UNCENSORED_NUMBER = re.compile(
    r"^(?:FC2-\d{5,7}|(?:CARIB|CARIBPR|1PON|PONDO|10MU)-\d{6}-\d{3})",
    re.I,
)

RELEASE_TAG_NAMES = {"中文字幕", "无码", "破解", "流出"}
_VERSION_LABELS = ("无码", "流出", "破解")
_LABEL_TO_VERSION = {"无码": "uncensored", "流出": "leak", "破解": "hack"}
_VERSION_TO_LABEL = {"uncensored": "无码", "leak": "流出", "hack": "破解"}


def version_suffix_for(version) -> str:
    return {"leak": "-leak", "hack": "-U"}.get(version or "", "")


def release_suffix(file_info, stored_tag) -> str:
    """出口用的版本后缀。ExtraInfo 里有版本时用它，否则用文件名识别。"""
    stored = version_from_stored_tags(stored_tag)
    if stored:
        return version_suffix_for(stored)
    if hasattr(file_info, "version_suffix"):
        return file_info.version_suffix()
    return ""


def render_scraped_name(metadata_mixed, scraping_conf, suffix: str) -> str:
    """按命名规则生成文件名。版本后缀只加在规则里的番号上。"""
    maxlen = scraping_conf.max_title_len
    context = dict(metadata_mixed.__dict__)
    number = context.get("number") or ""
    if suffix and number:
        context["number"] = f"{number}{suffix}"
    naming_rule = scraping_conf.naming_rule
    location_rule = scraping_conf.location_rule or ""
    extra_name = eval(naming_rule, context)
    if "actor" in location_rule and len(metadata_mixed.actor or "") > maxlen:
        extra_name = eval(naming_rule.replace("actor", "'多人作品'"), dict(context))
    title = metadata_mixed.title or ""
    if "title" in location_rule and title and len(title) > maxlen:
        extra_name = extra_name.replace(title, title[:maxlen])
    for char in ("<", ">", ":", '"', "|", "?", "*"):
        extra_name = extra_name.replace(char, "_")
    return extra_name


def version_labels(value) -> set:
    return {tag for tag in split_tags(value) if tag in _LABEL_TO_VERSION}


def version_from_stored_tags(value):
    """ExtraInfo 里已经写上的版本。多个同时在时按无码、流出、破解留一个。"""
    labels = version_labels(value)
    for label in _VERSION_LABELS:
        if label in labels:
            return _LABEL_TO_VERSION[label]
    return None


def split_tags(value) -> list:
    if not value:
        return []
    return [part.strip() for part in str(value).replace("，", ",").split(",") if part.strip()]


def merge_stored_tags(stored, release) -> str:
    """ 保留用户另外写的标签。ExtraInfo 里已有的版本优先于文件名识别。 """
    stored_version = version_from_stored_tags(stored)
    kept = [tag for tag in split_tags(stored) if tag not in RELEASE_TAG_NAMES]
    incoming = []
    for tag in release or []:
        if stored_version and tag in _LABEL_TO_VERSION:
            continue
        if tag not in incoming:
            incoming.append(tag)
    if stored_version:
        label = _VERSION_TO_LABEL[stored_version]
        if label not in incoming:
            incoming.append(label)
    for tag in incoming:
        if tag not in kept:
            kept.append(tag)
    return ", ".join(kept)


def release_tags_for(file_info, stored_tag) -> list:
    """文件名识别出的字幕。记录里已有的版本和中文字幕继续带着。"""
    detected = []
    if getattr(file_info, "num", None) and hasattr(file_info, "release_tags"):
        detected = list(file_info.release_tags())
    stored_version = version_from_stored_tags(stored_tag)
    if not stored_version:
        tags = detected
    else:
        tags = [tag for tag in detected if tag not in _LABEL_TO_VERSION]
        label = _VERSION_TO_LABEL[stored_version]
        if label not in tags:
            tags.append(label)
    if "中文字幕" in split_tags(stored_tag) and "中文字幕" not in tags:
        tags.append("中文字幕")
    return tags


def compose_output_tags(*sources, release=None, library_chinese=False) -> str:
    """ 站点标签保留。无码、破解、流出只留识别后的一个，字幕由文件名或字幕库决定。 """
    output = []
    for source in sources:
        for tag in split_tags(source):
            if tag in RELEASE_TAG_NAMES or tag in output:
                continue
            output.append(tag)
    for tag in release or []:
        if tag not in output:
            output.append(tag)
    if library_chinese and "中文字幕" not in output:
        output.append("中文字幕")
    return ", ".join(output)


def _has_hack_marker(filepath_lower: str) -> bool:
    return _HACK_MARKER.search(filepath_lower) is not None


def is_uncensored(number):
    if not number:
        return False
    if _NATIVE_UNCENSORED_NUMBER.match(str(number)):
        return True
    if RE_UNCENSORED_CHECK.match(number):
        return True
    uncensored_prefix = "S2M,BT,LAF,SMD,SMBD,SM3D2DBD,SKY-,SKYHD,CWP,CWDV,CWBD,CW3D2DBD,MKD,MKBD,MXBD,MK3D2DBD,MCB3DBD,MCBD,RHJ,MMDV"
    if G_cache_uncensored_conf.is_empty():
        G_cache_uncensored_conf.set(uncensored_prefix.split(','))
    return G_cache_uncensored_conf.check(number)


if __name__ == "__main__":
    # 测试
    test_path = [
        "/media/sdmua-001-c.mkv",
        "/media/kmhrs-023-C.mkv",
        "/media/sekao-023-C.mkv",
        "/media/sekao-023-leak.mkv",
        "/media/FC2-PPV-1234567.mkv",
        "/media/FC2PPV-1234567.mkv",
        "/meida/fc2-ppv-1234567-xxx.com.mp4",
        "/media/FC2-PPV-1111223/1111223.mp4",
        "/media/FC2-1123456-1.mp4",
        "/media/FC2PPV-1123457/FC2PPV-1123457-2.mp4",
        "/media/111234_123 女人/trailers/trailer.mp4",
        "/media/Miku Ohashi/調子に乗ったS嬢Ｘ苛められたM嬢 大橋未久(011015_780).mp4",
        "/meida/S2M-001-FHD/S2MBD-001.mp4",
        "/media/FC2-PPV-1112345/④えりか旅行本編.mp4",
        "/media/SIRO-1234-C.mkv",
        "/media/MXGS-1234-C.mkv",
        "/media/dv-1234-C.mkv",
        "/media/pred-1234-C.mkv",
    ]

    def convert_emoji(bool_tag):
        if bool_tag:
            return "✅"
        return "-"

    for t in test_path:
        fin = FileNumInfo(t)
        print(f"===============================")
        print(f"解析 {t} :")
        print(f"    番号: {fin.num}")
        print(f"    中文: {convert_emoji(fin.chs_tag)} 无码: {convert_emoji(fin.uncensored_tag)} 流出: {convert_emoji(fin.leak_tag)} 破解: {convert_emoji(fin.hack_tag)}")
        print(f"    分集: {getattr(fin, 'partNumber', 0)}")

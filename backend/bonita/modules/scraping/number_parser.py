import os
import re
import logging

G_spat = re.compile(
    r"^\w+\.(cc|com|net|me|club|jp|tv|xyz|biz|wiki|info|tw|us|de)@|^22-sht\.me|"
    r"^(fhd|hd|sd|1080p|720p|4K)(-|_)|"
    r"(-|_)(fhd|hd|sd|1080p|720p|4K|x264|x265|uncensored|hack|leak)",
    re.IGNORECASE)

# 预编译常用正则表达式
RE_CD_PART = re.compile(r"(?:-|_)cd\d{1,2}", re.IGNORECASE | re.X | re.S)
RE_NUMBER_PART = re.compile(r"(?:-|_)\d{1,2}$", re.IGNORECASE | re.X | re.S)
RE_SP_CHECK = re.compile(r"(?:-|_)sp(?:_|-|$)", re.IGNORECASE | re.X | re.S)
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
        self.uncensored_tag = False  # 无码
        self.leak_tag = False       # 流出
        self.hack_tag = False       # 破解
        self.multipart_tag = False  # 多部分
        self.special = False        # 特典
        self.part = ''              # 部分编号

        # 检查番号是否存在及是否无码
        if not self.num:
            return

        if is_uncensored(self.num):
            self.uncensored_tag = True

        # 转为小写以便检查
        filepath_lower = filepath.lower()

        # 检查是否破解/流出
        if any(term in filepath_lower for term in ['流出', '-leak', '_leak', '-uncensored', '_uncensored']):
            self.leak_tag = True

        if any(term in filepath_lower for term in ['破解', '-hack', '_hack', '-u', '_u']):
            self.hack_tag = True

        # 检查是否有中文字幕
        cn_indicators = ['中文', '字幕', '-c.', '_c.', '_c_', '-c-', '-uc', '_uc']
        if any(indicator in filepath_lower for indicator in cn_indicators) or \
           re.search(r'[-_]C(\.\w+$|-\w+)|\d+ch(\.\w+$|-\w+)', filepath_lower, re.I):
            self.chs_tag = True

        # 处理文件名
        basename = os.path.basename(filepath)
        self.originalname = os.path.splitext(basename)[0]

        # 检查是否为多部分
        self.part = self.checkPart(basename)
        if self.part:
            self.multipart_tag = True

        # 检查是否特典
        self.special = self.checkSp(basename)

    def fixedName(self):
        name = self.num
        if self.special:
            return self.originalname
        if self.uncensored_tag:
            name += '-uncensored'
        if self.leak_tag:
            name += '-leak'
        if self.hack_tag:
            name += '-hack'
        if self.chs_tag:
            name += '-C'
        if self.multipart_tag:
            name += self.part
        return name

    def updateCD(self, cdnum):
        self.multipart_tag = True
        self.part = '-CD' + str(cdnum)

    def isPartOneOrSingle(self):
        if not self.multipart_tag or self.part == '-CD1' or self.part == '-CD01':
            return True
        return False

    @staticmethod
    def checkPart(filename):
        try:
            if '_cd' in filename or '-cd' in filename:
                result = RE_CD_PART.findall(filename)
                if result:
                    part = str(result[0]).upper().replace('_', '-')
                    return part
            bname = os.path.splitext(filename)[0]
            result = RE_NUMBER_PART.findall(bname)
            if result:
                part = str(result[0]).upper().replace('_', '-')
                if 'CD' not in part:
                    part = part.replace('-', '-CD')
                return part
        except:
            return

    @staticmethod
    def checkSp(filename):
        try:
            bname = os.path.splitext(filename)[0]
            result = RE_SP_CHECK.findall(bname)
            if result and len(result) == 1:
                return True
        except:
            return False

    def tags(self):
        tags = []
        if self.chs_tag:
            tags.append('中文字幕')
        if self.uncensored_tag:
            tags.append('无码')
        if self.leak_tag:
            tags.append('流出')
        if self.hack_tag:
            tags.append('破解')
        return tags


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

        logging.getLogger().debug(f"[!] 特殊番号: {file_path}")
        if '字幕组' in filename or 'SUB' in filename.upper() or re.match(r'[\u30a0-\u30ff]+', filename):
            filename = G_spat.sub("", filename)
            filename = re.sub(r"\[.*?\]", "", filename)
            filename = filename.replace(".chs", "").replace(".cht", "")
            file_number = str(re.findall(r'(.+?)\.', filename)).strip(" [']")
            return file_number
        elif '-' in filename or '_' in filename:  # 普通提取番号 主要处理包含减号-和_的番号
            filename = G_spat.sub("", filename)
            filename = str(re.sub(r"\[\d{4}-\d{1,2}-\d{1,2}\] - ", "", filename))  # 去除文件名中时间
            filename = re.sub(r"[-_]cd\d{1,2}", "", filename, flags=re.IGNORECASE)
            if not re.search("-|_", filename):  # 去掉-CD1之后再无-的情况，例如n1012-CD1.wmv
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


def is_uncensored(number):
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
        print(f"    多集: {convert_emoji(fin.multipart_tag)} 特典: {convert_emoji(fin.special)}")

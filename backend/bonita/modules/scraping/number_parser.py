import os
import re
import logging

G_spat = re.compile(
    "^\w+\.(cc|com|net|me|club|jp|tv|xyz|biz|wiki|info|tw|us|de)@|^22-sht\.me|"
    "^(fhd|hd|sd|1080p|720p|4K)(-|_)|"
    "(-|_)(fhd|hd|sd|1080p|720p|4K|x264|x265|uncensored|hack|leak)",
    re.IGNORECASE)


class FileNumInfo():
    """ 解析文件番号信息
    """

    def __init__(self, filepath: str):
        self.num = get_number(filepath)

        self.chs_tag = False
        self.uncensored_tag = False
        self.leak_tag = False
        self.hack_tag = False
        self.multipart_tag = False
        self.special = False
        self.part = ''

        if self.num and is_uncensored(self.num):
            self.uncensored_tag = True
        filepath = filepath.lower()
        if '流出' in filepath or '-leak' in filepath or '_leak' in filepath \
                or '-uncensored' in filepath or '_uncensored' in filepath:
            self.leak_tag = True
        if '破解' in filepath or '-hack' in filepath or '_hack' in filepath or '-u' in filepath or '_u' in filepath:
            self.hack_tag = True

        cnlist = ['中文', '字幕', '-c.', '_c.', '_c_', '-c-', '-uc', '_uc']
        for single in cnlist:
            if single in filepath:
                self.chs_tag = True
                break
        if re.search(r'[-_]C(\.\w+$|-\w+)|\d+ch(\.\w+$|-\w+)', filepath, re.I):
            self.chs_tag = True

        basename = os.path.basename(filepath)
        self.originalname = os.path.splitext(basename)[0]
        self.part = self.checkPart(basename)
        if self.part:
            self.multipart_tag = True
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
                prog = re.compile("(?:-|_)cd\d{1,2}", re.IGNORECASE | re.X | re.S)
                result = prog.findall(filename)
                if result:
                    part = str(result[0]).upper().replace('_', '-')
                    return part
            prog = re.compile("(?:-|_)\d{1,2}$", re.IGNORECASE | re.X | re.S)
            bname = os.path.splitext(filename)[0]
            result = prog.findall(bname)
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
            prog = re.compile("(?:-|_)sp(?:_|-|$)", re.IGNORECASE | re.X | re.S)
            bname = os.path.splitext(filename)[0]
            result = prog.findall(bname)
            if result and len(result) == 1:
                return True
        except:
            return False


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
            filename = re.sub("\[.*?\]","",filename)
            filename = filename.replace(".chs", "").replace(".cht", "")
            file_number = str(re.findall(r'(.+?)\.', filename)).strip(" [']")
            return file_number
        elif '-' in filename or '_' in filename:  # 普通提取番号 主要处理包含减号-和_的番号
            filename = G_spat.sub("", filename)
            filename = str(re.sub("\[\d{4}-\d{1,2}-\d{1,2}\] - ", "", filename))  # 去除文件名中时间
            filename = re.sub("[-_]cd\d{1,2}", "", filename, flags=re.IGNORECASE)
            if not re.search("-|_", filename): # 去掉-CD1之后再无-的情况，例如n1012-CD1.wmv
                return str(re.search(r'\w+', filename[:filename.find('.')], re.A).group())
            file_number =  os.path.splitext(filename)
            filename = re.search(r'[\w\-_]+', filename, re.A)
            if filename:
                file_number = str(filename.group())
            else:
                file_number = file_number[0]
            file_number = re.sub("(-|_)c$", "", file_number, flags=re.IGNORECASE)
            if re.search("\d+ch$", file_number, flags=re.I):
                file_number = file_number[:-2]
            return file_number.upper()
        else:  # 提取不含减号-的番号，FANZA CID
            # 欧美番号匹配规则
            oumei = re.search(r'[a-zA-Z]+\.\d{2}\.\d{2}\.\d{2}', basename)
            if oumei:
                return oumei.group()
            try:
                return str(
                    re.findall(r'(.+?)\.',
                               str(re.search('([^<>/\\\\|:""\\*\\?]+)\\.\\w+$', basename).group()))).strip(
                    "['']").replace('_', '-')
            except:
                return str(re.search(r'(.+?)\.', basename)[0])
    except Exception as e:
        logging.getLogger().error(e)
        return


# 定义多个匹配规则
rules = [
    lambda x: re.search(r'\d{6}(-|_)\d{2,3}', x, re.I).group(),
    lambda x: re.search(r'x-art\.\d{2}\.\d{2}\.\d{2}', x, re.I).group(),
    lambda x: ''.join(['xxx-av-', re.findall(r'xxx-av[^\d]*(\d{3,5})[^\d]*', x, re.I)[0]]),
    lambda x: 'heydouga-' + '-'.join(re.findall(r'(\d{4})[\-_](\d{3,4})[^\d]*', x, re.I)[0]),
    lambda x: 'HEYZO-' + re.findall(r'heyzo[^\d]*(\d{4})', x, re.I)[0],
    lambda x: re.search(r'mdbk(-|_)(\d{4})', x, re.I).group(),
    lambda x: re.search(r'mdtm(-|_)(\d{4})', x, re.I).group(),
    lambda x: re.search(r's2mbd(-|_)(\d{3})', x, re.I).group(),
    lambda x: re.search(r's2m(-|_)(\d{3})', x, re.I).group(),
    lambda x: re.search(r'fc2(-|_)(\d{5,7})', x, re.I).group(),
    lambda x: re.search(r'([A-Za-z]{2,6}\-?\d{3,4})', x, re.I).group(),
]


def rules_parser(filename: str):
    """ lower filename
    """
    filename = filename.upper()
    for rule in rules:
        try:
            if 'FC2' in filename:
                filename = filename.replace('PPV', '').replace('--', '-').replace('_', '-').replace(' ', '')
            file_number = rule(filename)
            if file_number:
                return file_number
        except:
            pass
    return


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
    if re.match(
        r'[\d-]{4,}|\d{6}_\d{2,3}|(cz|gedo|k|n|red-|se)\d{2,4}|heyzo.+|xxx-av-.+|heydouga-.+|x-art\.\d{2}\.\d{2}\.\d{2}',
        number,
        re.I
    ):
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

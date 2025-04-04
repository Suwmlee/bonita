# -*- coding: utf-8 -*-

import re


def regexMatch(basename, reg):
    """ 正则匹配
    """
    prog = re.compile(reg, re.IGNORECASE | re.X | re.S)
    result = prog.findall(basename)
    return result


def matchSeason(filename: str):
    """匹配季度信息
    >>> matchSeason("Fights.Break.Sphere.2018.S02.WEB-DL.1080p.H264.AAC-TJUPT")
    2
    >>> matchSeason("疑犯追踪S01-S05.Person.of.Interest.2011-2016.1080p.Blu-ray.x265.AC3￡cXcY@FRDS") is None
    True
    >>> matchSeason("Yes.Prime.Minister.COMPLETE.PACK.DVD.x264-P2P") is None
    True
    >>> matchSeason("第二季.Friends.S02.1080p") 
    2
    >>> matchSeason("Friends Season 2 1080p")
    2
    >>> matchSeason("Breaking.Bad.Season.5.1080p.BluRay")
    5
    >>> matchSeason("Band.of.Brothers.2001.1080p.BluRay.x265.10bit.AC3") is None
    True
    >>> matchSeason("Friends.2019.1080p") is None
    True
    >>> matchSeason("Series.2019.S01E02.1080p") 
    1
    """
    # Skip ranges like S01-S05
    if re.search(r'S\d+-S\d+', filename, re.IGNORECASE):
        return None

    # Skip if it's a COMPLETE PACK or similar
    if re.search(r'COMPLETE.PACK|COMPLETE.SERIES|COMPLETE.COLLECTION', filename, re.IGNORECASE):
        return None

    # Check if it's a movie (year followed by resolution without season info)
    # But make sure it's not interfering with S01E02 type patterns
    if not re.search(r'S\d+|Season|第.季', filename, re.IGNORECASE) and re.search(r'(?:19|20)\d{2}.*(?:1080p|720p|480p|2160p)', filename):
        return None

    regexs = [
        r"[Ss](\d{1,2})(?!\d)(?!\-[Ss]\d+)(?:[Ee]\d+)?",    # Match S01 or s01 but not if part of a range S01-S05
        r"[Ss]eason[\s._]?(\d{1,2})(?!\d)",                 # Match Season 1 format
        r"第(\d{1,2})季",                                    # Match Chinese numeric season
        r"第([一二三四五六七八九十])季",                        # Match Chinese text numbers
    ]

    for regex in regexs:
        nameresult = regexMatch(filename, regex)
        if nameresult and len(nameresult) == 1:
            # Handle Chinese text numbers
            if nameresult[0] in "一二三四五六七八九十":
                chinese_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                                "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
                return chinese_nums.get(nameresult[0])
            return int(nameresult[0])
    return None


def matchEpisodePart(basename):
    """ 正则匹配集数的片段

    >>> matchEpisodePart("[Rip] SLAM DUNK [013]「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '013'
    >>> matchEpisodePart("[Rip] SLAM DUNK [13.5]「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '[13.'
    >>> matchEpisodePart("[Rip] SLAM DUNK [13v2]「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '13v2'
    >>> matchEpisodePart("[Rip] SLAM DUNK [13(OA)]「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '13(OA)'
    >>> matchEpisodePart("[Neon Genesis Evangelion][23(Video)][BDRIP][1440x1080][H264_FLACx2]")
    '23(Video)'
    >>> matchEpisodePart("[Studio] Fullmetal Alchemist꞉ Brotherhood [01][Ma10p_1080p][x265_flac]")
    '01'
    >>> matchEpisodePart("[raws][Code Geass Lelouch of the Rebellion R2][15][BDRIP][Hi10P FLAC][1920X1080]")
    '15'
    >>> matchEpisodePart("[raws][High School Of The Dead][01][BDRIP][HEVC Main10P FLAC][1920X1080]")
    '01'
    >>> matchEpisodePart("[Studio] Steins;Gate 0 [01][Ma10p_1080p].DDP.5.1.2Audio")
    '01'
    >>> matchEpisodePart("[AI-Raws&ANK-Raws] Initial D First Stage [05] (BDRip 960x720 x264 DTS-HD Hi10P)[044D7040]")
    '05'
    >>> matchEpisodePart("Evangelion.2021.E02(OA).1080p.WEB-DL.H264.AAC-PTerWEB")
    '.E02(OA).'
    >>> matchEpisodePart("Shadow.2021.E13v2.WEB-DL.4k.H265.60fps.DDP.5.1.2Audio")
    '.E13v2.'
    >>> matchEpisodePart("Shadow.2021.E14(OA).WEB-DL.4k.H265.60fps.DDP.7.1.2Audio")
    '.E14(OA).'
    >>> matchEpisodePart("Person.of.Interest.EP01.2013.1080p.Blu-ray.x265.10bit.AC3")
    '.EP01.'
    >>> matchEpisodePart("Shadow.2021.E11.WEB-DL.4k.H265.60fps.AAC.2Audio")
    '.E11.'
    >>> matchEpisodePart("Steins;Gate 2011 EP01 [BluRay 1920x1080p 23.976fps x264-Hi10P FLAC]")
    ' EP01 '
    >>> matchEpisodePart("Fate Stay Night [Unlimited Blade Works] 2014 - EP01 [BD 1920x1080 AVC-yuv444p10 FLAC PGSx2 Chap]")
    ' EP01 '
    >>> matchEpisodePart("Fate Zero EP01 [BluRay 1920x1080p 23.976fps x264-Hi10P FLAC PGSx2]")
    ' EP01 '
    >>> matchEpisodePart("Shadow 2021 E11 WEB-DL 4k H265 AAC 2Audio")
    ' E11 '
    >>> matchEpisodePart("Shadow.2021.第11集.WEB-DL.4k.H265.60fps.AAC.2Audio")
    '第11集'
    >>> matchEpisodePart("TV 节目 第1期 嘉宾张三")
    '第1期'
    >>> matchEpisodePart("[Rip] SLAM DUNK 第013話「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '第013話'
    >>> matchEpisodePart("Slam.Dunk.22.Ma10p.1080p.x265.flac")
    '.22.'
    >>> matchEpisodePart("[AI-Raws&ANK-Raws] Initial D First Stage 01 (BDRip 960x720 x264 DTS-HD Hi10P)[044D7040]")
    ' 01 '
    >>> matchEpisodePart("生徒会役員共＊ 09 (BDrip 1920x1080 HEVC-YUV420P10 FLAC)")
    ' 09 '
    >>> matchEpisodePart("Why.Poverty.1of8.Poor.Us.-.An.Animated.History.of.Poverty.1080p.WEB-DL.AVC.AAC")
    '.1of8.'
    >>> matchEpisodePart("PBS Simon Schama's Power of Art - Part 1of8, Van Gogh (2007.720p.HDTV.AC3-SoS)")
    ' 1of8,'
    >>> matchEpisodePart("Why.Poverty 1of8 Poor.Us.-.An.Animated.History.of.Poverty.1080p.WEB-DL.AVC.AAC")
    ' 1of8 '
    >>> matchEpisodePart("O.J.Made.In.America.Part2.2016.1080p.Blu-ray.x265.10bit.AC3")
    '.Part2.'
    >>> matchEpisodePart("Person.of.Interest.S03E01.2013.1080p.Blu-ray.x265.10bit.AC3")
    'E01'
    >>> matchEpisodePart("The.Office.S01E05.1080p.BluRay.DDP.5.1.x264")
    'E05'
    """
    # 先尝试匹配S01E05格式的E05部分
    sxxexx_match = re.search(r'[Ss]\d{1,2}([Ee]\d{1,3})', basename)
    if sxxexx_match:
        return sxxexx_match.group(1)

    regexs = [
        r"\[(\d{1,3}(?:\d+)?(?:v\d+)?(?:\(oa\)|\(video\))?)\]",
        r"[\[\. ]ep?[0-9\(\)videoa]*[\[\. ]",                       # 匹配空格+E+数字+空格
        r"[\[\. ]\d{1,3}(?:\.\d|v\d)?[\(\)videoa]*[\[\. ]",         # 匹配空格+数字(可能带小数或v2等版本)+空格
        r"(?<=[\.\s])[Ee]\d{1,3}(?=[\.\s])",                        # 匹配独立的 E05 (前后有点或空格)
        r"第\d*[話话集期]",                                         # 匹配中文集数标记
        r"(?<=[^a-zA-Z0-9])E\d{1,3}",                               # 匹配前面非字母数字的 E05
        r"[\[\. ]\d+of\d+[\]\. ,]",                                 # 匹配 .1of8. 格式
        r"[\[\. ]Part\d+[\[\. ]",                                   # 匹配 .Part2. 格式
    ]

    for regex in regexs:
        results = regexMatch(basename, regex)
        if results and len(results) == 1:
            return results[0]

    return None


def extractEpisodeNum(single: str):
    """ 提取集数片段内具体集数
    >>> extractEpisodeNum("第013話")
    (13, None)
    >>> extractEpisodeNum("第1期")
    (1, None)
    >>> extractEpisodeNum("第11集")
    (11, None)
    >>> extractEpisodeNum("01")
    (1, None)
    >>> extractEpisodeNum("01(video)")
    (1, 'video')
    >>> extractEpisodeNum("01v2")
    (1, 'v2')
    >>> extractEpisodeNum("ep01")
    (1, None)
    >>> extractEpisodeNum(".E02(OA).")
    (2, 'oa')
    >>> extractEpisodeNum("13.5")
    (13, '5')
    >>> extractEpisodeNum("'.Part2.'")
    (2, None)
    >>> extractEpisodeNum("1of8")
    (1, None)
    """
    if not single:
        return (-1, None)
    clean_str = single.strip("'\"[]., \t").lower()
    # 处理带括号的情况，如 01(video), E02(OA)
    if match := re.search(r"(?:第|ep|e)?(\d+)\(([^)]+)\)", clean_str):
        return (int(match.group(1)), match.group(2).lower())
    # 处理带小数点的情况，如 13.5
    if match := re.search(r"(?:第|ep|e)?(\d+)\.(\d+)", clean_str):
        return (int(match.group(1)), match.group(2))
    # 处理带v版本的情况，如 01v2
    if match := re.search(r"(?:第|ep|e)?(\d+)v(\d+)", clean_str):
        return (int(match.group(1)), f"v{match.group(2)}")
    # 处理Part格式: Part2
    if match := re.search(r"(?:part|部分)(\d+)", clean_str):
        return (int(match.group(1)), None)
    # 处理of格式: 1of8
    if match := re.search(r"(\d+)of\d+", clean_str):
        return (int(match.group(1)), None)
    # 处理标准格式: 第01集, 第013話, EP01, 01
    if match := re.search(r"(?:第|ep|e)?(\d+)(?:[期集話话])?$", clean_str):
        return (int(match.group(1)), None)
    # 最后尝试提取任何数字
    if match := re.search(r"\d+", clean_str):
        return (int(match.group(0)), None)
    return (-1, None)


def matchSeries(basename):
    """匹配季度和集数信息
    >>> matchSeries("The.Office.S03E05.1080p")
    (3, 5)
    >>> matchSeries("Friends.S01E22.1080p.BluRay")
    (1, 22)
    """
    regexs = [
        r"[Ss](\d{1,2})[Ee](\d{1,4})",            # 标准 S01E01 格式
        r"[Ss]eason[\s.]?(\d{1,2})[\s.]?[Ee]p(?:isode)?[\s.]?(\d{1,4})",  # Season 1 Episode 1
        r"第(\d{1,2})季第(\d{1,4})[集话期]",        # 中文格式
    ]

    for regstr in regexs:
        results = regexMatch(basename, regstr)
        if results and len(results) > 0:
            season = int(results[0][0])
            ep = int(results[0][1])
            return season, ep
    return None, None


def simpleMatchEp(basename: str):
    """ 针对已经强制season但未能正常解析出ep的名字

    >>> simpleMatchEp("01 呵呵呵")
    1
    >>> simpleMatchEp("02_哈哈哈")
    2
    >>> simpleMatchEp("03.嘿嘿嘿")
    3
    >>> simpleMatchEp("04. 嘿嘿嘿")
    4
    >>> simpleMatchEp("05 - 嘿嘿嘿")
    5
    >>> simpleMatchEp("06")
    6
    >>> simpleMatchEp("EP07")
    7
    >>> simpleMatchEp("e08")
    8
    >>> simpleMatchEp("第9集")
    9
    >>> simpleMatchEp("第10话")
    10
    >>> simpleMatchEp("01")
    1
    >>> simpleMatchEp("01(video)")
    1
    >>> simpleMatchEp("01v2")
    1
    """
    if basename.isdigit():
        return int(basename)

    # 匹配常见的几种集数格式
    regexs = [
        r"^(\d{1,3}) ?(_|-|.)? ?([^\W\d]+)",  # 数字开头后面跟分隔符和非数字内容
        r"^[Ee][Pp]?(\d{1,3})",              # EP01 或 E01 格式
        r"^第(\d{1,3})[集话期]",               # 中文集数表示
    ]

    for regstr in regexs:
        results = re.findall(regstr, basename)
        if results and len(results) >= 1:
            # 根据正则表达式的不同，提取相应位置的数字
            if '集' in regstr or '话' in regstr or '期' in regstr or '[Ee]' in regstr:
                epnum = int(results[0])
            else:
                epnum = int(results[0][0])
            return epnum

    return None


if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)

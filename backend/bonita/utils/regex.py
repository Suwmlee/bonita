# -*- coding: utf-8 -*-

import re


def regexMatch(basename, reg):
    """ 正则匹配
    """
    prog = re.compile(reg, re.IGNORECASE | re.X | re.S)
    result = prog.findall(basename)
    return result


def extractEpNum(single: str):
    """ 提取剧集编号
    1. 头尾匹配 空格 [] 第话
    2. 剔除头尾修饰字符
    3. 校验含有数字
    4. 如果不包含E,仍需校验是否是年份，个位数
    """
    left = single[0]
    right = single[-1:]
    if left == right or (left == '[' and right == ']') or (left == '第' and right in '話话集'):

        result = single.lstrip('第.EPep\[ ')
        result = result.rstrip('話话集]. ')

        if bool(re.search(r'\d', result)):
            if not bool(re.search(r'[Ee]', single)):
                if len(result) == 1:
                    return None
                match = re.match(r'.*([1-3][0-9]{3})', result)
                if match:
                    return None
                return result
            else:
                return result
    return None


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
    """
    # TODO 添加更多季度匹配模式
    regexs = [
        r"(?:s|season)[\s.]?(\d{1,2})",      # 匹配 S01 或 Season 1 格式
        r"第(\d{1,2})季",                     # 匹配中文季度表示
        r"第([一二三四五六七八九十])季",       # 匹配中文数字季度表示
        r"season[\s.](\d{1,2})",             # 匹配 Season 1 格式
    ]
    
    for regex in regexs:
        nameresult = regexMatch(filename, regex)
        if nameresult and len(nameresult) == 1:
            # 处理中文数字
            if nameresult[0] in "一二三四五六七八九十":
                chinese_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, 
                               "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
                return chinese_nums.get(nameresult[0])
            return int(nameresult[0])
    return None


def matchEpPart(basename):
    """ 正则匹配单集编号

    >>> matchEpPart("生徒会役員共＊ 09 (BDrip 1920x1080 HEVC-YUV420P10 FLAC)")
    ' 09 '
    >>> matchEpPart("[Rip] SLAM DUNK 第013話「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '第013話'
    >>> matchEpPart("[Rip] SLAM DUNK [013]「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '[013]'
    >>> matchEpPart("[Rip] SLAM DUNK [13.5]「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '[13.5]'
    >>> matchEpPart("[Rip] SLAM DUNK [13v2]「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '[13v2]'
    >>> matchEpPart("[Rip] SLAM DUNK [13(OA)]「湘北VS陵南 燃える主将!」(BDrip 1440x1080 H264 FLAC)")
    '[13(OA)]'
    >>> matchEpPart("[Neon Genesis Evangelion][23(Video)][BDRIP][1440x1080][H264_FLACx2]")
    '[23(Video)]'
    >>> matchEpPart("[Studio] Fullmetal Alchemist꞉ Brotherhood [01][Ma10p_1080p][x265_flac]")
    '[01]'
    >>> matchEpPart("[raws][Code Geass Lelouch of the Rebellion R2][15][BDRIP][Hi10P FLAC][1920X1080]")
    '[15]'
    >>> matchEpPart("[raws][High School Of The Dead][01][BDRIP][HEVC Main10P FLAC][1920X1080]")
    '[01]'
    >>> matchEpPart("[Studio] Steins;Gate 0 [01][Ma10p_1080p][x265_flac]")
    '[01]'
    >>> matchEpPart("Steins;Gate 2011 EP01 [BluRay 1920x1080p 23.976fps x264-Hi10P FLAC]")
    ' EP01 '
    >>> matchEpPart("Fate Stay Night [Unlimited Blade Works] 2014 - EP01 [BD 1920x1080 AVC-yuv444p10 FLAC PGSx2 Chap]")
    ' EP01 '
    >>> matchEpPart("Fate Zero EP01 [BluRay 1920x1080p 23.976fps x264-Hi10P FLAC PGSx2]")
    ' EP01 '
    >>> matchEpPart("[AI-Raws&ANK-Raws] Initial D First Stage 01 (BDRip 960x720 x264 DTS-HD Hi10P)[044D7040]")
    ' 01 '
    >>> matchEpPart("[AI-Raws&ANK-Raws] Initial D First Stage [05] (BDRip 960x720 x264 DTS-HD Hi10P)[044D7040]")
    '[05]'

    >>> matchEpPart("Shadow.2021.E11.WEB-DL.4k.H265.60fps.AAC.2Audio")
    '.E11.'
    >>> matchEpPart("Shadow 2021 E11 WEB-DL 4k H265 AAC 2Audio")
    ' E11 '
    >>> matchEpPart("Shadow.2021.第11集.WEB-DL.4k.H265.60fps.AAC.2Audio")
    '第11集'
    >>> matchEpPart("Shadow.2021.E13v2.WEB-DL.4k.H265.60fps.AAC.2Audio")
    '.E13v2.'
    >>> matchEpPart("Shadow.2021.E14(OA).WEB-DL.4k.H265.60fps.AAC.2Audio")
    '.E14(OA).'
    >>> matchEpPart("S03/Person.of.Interest.EP01.2013.1080p.Blu-ray.x265.10bit.AC3")
    '.EP01.'
    >>> matchEpPart("Slam.Dunk.22.Ma10p.1080p.x265.flac")
    '.22.'
    >>> matchEpPart("The.Office.S01E05.1080p.BluRay")
    'E05'
    >>> matchEpPart("TV 节目 第1期 嘉宾张三")
    '第1期'

    >>> matchEpPart("Person.of.Interest.S03E01.2013.1080p.Blu-ray.x265.10bit.AC3") is None
    False
    """
    regexs = [
        r"第\d*[話话集期]",                                # 匹配中文集数标记
        r"[ ]ep?[0-9.\(\)videoa]*[ ]",                   # 匹配空格+E+数字+空格
        r"\.ep?[0-9\(\)videoa]*\.",                      # 匹配点+E+数字+点
        r"\.\d{1,3}(?:v\d)?[\(\)videoa]*\.",             # 匹配点+数字(可能带v2等版本)+点
        r"[ ]\d{1,3}(?:\.\d|v\d)?[\(\)videoa]*[ ]",      # 匹配空格+数字(可能带小数或v2等版本)+空格
        r"\[(?:e|ep)?[0-9.v]*(?:\(oa\)|\(video\))?\]",   # 匹配[数字](可能带特殊标记)
        r"[Ss]\d{1,2}[Ee]\d{1,3}",                       # 匹配 S01E05 格式
        r"(?<=[\.\s])[Ee]\d{1,3}(?=[\.\s])",             # 匹配独立的 E05 (前后有点或空格)
        r"(?<=[^a-zA-Z0-9])E\d{1,3}",                    # 匹配前面非字母数字的 E05
    ]
    for regex in regexs:
        results = regexMatch(basename, regex)
        if results and len(results) == 1:
            return results[0]

    # 尝试匹配S01E05格式的E05部分
    sxxexx_match = re.search(r'[Ss]\d{1,2}([Ee]\d{1,3})', basename)
    if sxxexx_match:
        return sxxexx_match.group(1)

    return None


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

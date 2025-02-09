

import os
import logging

from bonita.utils.regex import extractEpNum, matchEpPart, matchSeries, simpleMatchEp

logger = logging.getLogger(__name__)


class FileInfo():

    realpath = ''
    realfolder = ''
    realname = ''
    folders = []

    midfolder = ''
    topfolder = ''
    secondfolder = ''
    name = ''
    ext = ''

    isepisode = False
    locked = False
    forcedseason = False
    originep = ''
    season = None
    epnum = None
    forcedname = ''

    finalpath = ''
    finalfolder = ''

    def __init__(self, filepath):
        self.realpath = filepath
        (filefolder, filename) = os.path.split(filepath)
        self.realfolder = filefolder
        self.realname = filename
        (name, ext) = os.path.splitext(filename)
        self.name = name
        self.ext = ext

    def updateMidFolder(self, mid):
        self.midfolder = mid
        folders = os.path.normpath(mid).split(os.path.sep)
        self.folders = folders
        self.topfolder = folders[0]
        if len(folders) > 1:
            self.secondfolder = folders[1]

    def fixMidFolder(self):
        temp = self.folders
        temp[0] = self.topfolder
        if self.secondfolder != '':
            if len(temp) > 1:
                temp[1] = self.secondfolder
            else:
                temp.append(self.secondfolder)
        return os.path.join(*temp)

    def updateForcedname(self, name):
        self.forcedname = name

    def fixFinalName(self):
        if self.forcedname != "":
            return self.forcedname + self.ext
        else:
            return self.name + self.ext

    def updateFinalPath(self, path):
        self.finalpath = path
        self.finalfolder = os.path.dirname(path)

    def parse(self):
        # 正确的剧集命名
        season, ep = matchSeries(self.name)
        if isinstance(season, int) and season > -1 and isinstance(ep, int) and ep > -1:
            self.isepisode = True
            self.season = season
            self.epnum = ep
            self.originep = 'Pass'
            return
        # 是否是需要修正的剧集命名
        originep = matchEpPart(self.name)
        if originep:
            epresult = extractEpNum(originep)
            if epresult:
                self.isepisode = True
                self.originep = originep
                self.epnum = epresult

    def fixEpName(self, season):
        if not self.epnum and self.forcedseason:
            logger.debug("强制`season`后,尝试获取`ep`")
            sep = simpleMatchEp(self.name)
            if sep:
                self.epnum = sep
                self.originep = 'Pass'
            else:
                return
        if isinstance(self.epnum, int):
            prefix = "S%02dE%02d" % (season, self.epnum)
        else:
            prefix = "S%02dE" % (season) + self.epnum

        if self.originep == 'Pass':
            if prefix in self.name:
                return
            else:
                self.name = prefix
        else:
            if self.originep[0] == '.':
                renum = "." + prefix + "."
            elif self.originep[0] == '[':
                renum = " " + prefix + " "
            else:
                renum = " " + prefix + " "
            logger.debug("替换内容:" + renum)
            newname = self.name.replace(self.originep, renum)
            self.name = newname
            logger.info("替换后:   {}".format(newname))

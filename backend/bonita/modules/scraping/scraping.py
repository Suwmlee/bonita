
import os
import logging
import shutil
from scrapinglib import search

from bonita import schemas
from bonita.db.models.extrainfo import ExtraInfo
from bonita.utils.downloader import download_file


logger = logging.getLogger(__name__)


def scraping(filepath, conf, extrainfo: ExtraInfo) -> schemas.MetadataBase:
    """ 开始刮削
    """
    c_sources = "javlibrary,javdb,javbus,airav,fanza,xcity,jav321,mgstage,fc2,avsox,dlsite,carib,madou,mv91,getchu,gcolle"

    json_data = search(extrainfo.number, c_sources,
                       specifiedSource=extrainfo.specifiedsource,
                       specifiedUrl=extrainfo.specifiedurl)
    # 将 metadata_json 转换为 MetadataBase
    metadata_base = schemas.MetadataBase(**json_data)

    return metadata_base



def process_cover(tmp_cover_path, prefilename, output_folder):
    """ Cover
    """
    fanartpath = os.path.join(output_folder, prefilename + '-fanart.jpg')
    thumbpath = os.path.join(output_folder, prefilename + '-thumb.jpg')
    shutil.copyfile(tmp_cover_path, fanartpath)
    shutil.copyfile(tmp_cover_path, thumbpath)

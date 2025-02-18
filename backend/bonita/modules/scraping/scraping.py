
import ast
import os
import logging
import shutil
from scrapinglib import search

from bonita import schemas


logger = logging.getLogger(__name__)


def scraping(number, sources=None, specifiedsource="", specifiedurl="") -> schemas.MetadataBase:
    """ 开始刮削
    """
    json_data = search(number,
                       sources=sources,
                       specifiedSource=specifiedsource,
                       specifiedUrl=specifiedurl)
    # 将 metadata_json 转换为 MetadataBase
    metadata_base = schemas.MetadataBase(**json_data)

    return metadata_base


def process_nfo_file(output_folder, prefilename, metadata_dict):
    """ 处理 NFO 文件
    """
    title = metadata_dict.get('title', '')
    studio = metadata_dict.get('studio', '')
    year = str(metadata_dict.get('year'))
    outline = metadata_dict.get('outline', '')
    runtime = metadata_dict.get('runtime', '')
    director = metadata_dict.get('director', '')
    release = str(metadata_dict.get('release'))
    number = metadata_dict.get('number', '')
    cover = metadata_dict.get('cover', '')
    trailer = metadata_dict.get('trailer', '')
    site = metadata_dict.get('site', '')
    series = metadata_dict.get('series', '')
    label = metadata_dict.get('label', '')

    filename = metadata_dict.get('extra_filename', '')
    actor_list = [word.strip() for word in metadata_dict.get('actor').split(',')]
    actor_photo = ast.literal_eval(metadata_dict.get('actor_photo'))
    tags = [word.strip() for word in metadata_dict.get('tag').split(',')]
    try:
        nfo_path = os.path.join(output_folder, prefilename + ".nfo")

        # KODI内查看影片信息时找不到number，配置naming_rule=number+'#'+title虽可解决
        # 但使得标题太长，放入时常为空的outline内会更适合，软件给outline留出的显示版面也较大
        outline = f"{number}#{outline}"
        with open(nfo_path, "wt", encoding='UTF-8') as code:
            print('<?xml version="1.0" encoding="UTF-8" ?>', file=code)
            print("<movie>", file=code)
            print("  <title><![CDATA[" + filename + "]]></title>", file=code)
            print("  <originaltitle><![CDATA[" + filename + "]]></originaltitle>", file=code)
            print("  <sorttitle><![CDATA[" + filename + "]]></sorttitle>", file=code)
            print("  <customrating>JP-18+</customrating>", file=code)
            print("  <mpaa>JP-18+</mpaa>", file=code)
            try:
                print("  <set>" + series + "</set>", file=code)
            except:
                print("  <set></set>", file=code)
            print("  <studio>" + studio + "</studio>", file=code)
            print("  <year>" + year + "</year>", file=code)
            print("  <outline><![CDATA[" + outline + "]]></outline>", file=code)
            print("  <plot><![CDATA[" + outline + "]]></plot>", file=code)
            print("  <runtime>" + runtime + "</runtime>", file=code)
            print("  <director>" + director + "</director>", file=code)
            print("  <poster>" + prefilename + "-poster.jpg</poster>", file=code)
            print("  <thumb>" + prefilename + "-thumb.jpg</thumb>", file=code)
            print("  <fanart>" + prefilename + '-fanart.jpg' + "</fanart>", file=code)
            try:
                for key in actor_list:
                    print("  <actor>", file=code)
                    print("    <name>" + key + "</name>", file=code)
                    try:
                        print("    <thumb>" + actor_photo.get(str(key)) + "</thumb>", file=code)
                    except:
                        pass
                    print("  </actor>", file=code)
            except:
                pass
            print("  <maker>" + studio + "</maker>", file=code)
            print("  <label>" + label + "</label>", file=code)
            # if numinfo.chs_tag:
            #     print("  <tag>中文字幕</tag>", file=code)
            # if numinfo.leak_tag:
            #     print("  <tag>流出</tag>", file=code)
            # if numinfo.uncensored_tag:
            #     print("  <tag>无码</tag>", file=code)
            # if numinfo.hack_tag:
            #     print("  <tag>破解</tag>", file=code)
            try:
                for i in tags:
                    print("  <tag>" + i + "</tag>", file=code)
                # print("  <tag>" + series + "</tag>", file=code)
            except:
                pass
            # if numinfo.chs_tag:
            #     print("  <genre>中文字幕</genre>", file=code)
            # if numinfo.leak_tag:
            #     print("  <genre>流出</genre>", file=code)
            # if numinfo.uncensored_tag:
            #     print("  <genre>无码</genre>", file=code)
            # if numinfo.hack_tag:
            #     print("  <genre>破解</genre>", file=code)
            try:
                for i in tags:
                    print("  <genre>" + i + "</genre>", file=code)
                # print("  <genre>" + series + "</genre>", file=code)
            except:
                pass
            print("  <num>" + number + "</num>", file=code)
            print("  <premiered>" + release + "</premiered>", file=code)
            print("  <releasedate>" + release + "</releasedate>", file=code)
            print("  <release>" + release + "</release>", file=code)
            try:
                if site == 'javdb' or site == 'javlibrary':
                    rating = metadata_dict.get('userrating')
                    votes = metadata_dict.get('uservotes')
                    if site == 'javdb':
                        toprating = 5
                    elif site == 'javlibrary':
                        toprating = 10
                    print(f"""  <rating>{round(rating * 10.0 / toprating, 1)}</rating>
  <criticrating>{round(rating * 100.0 / toprating, 1)}</criticrating>
  <ratings>
    <rating name="{site}" max="{toprating}" default="true">
      <value>{rating}</value>
      <votes>{votes}</votes>
    </rating>
  </ratings>""", file=code)
            except:
                pass
            print("  <cover>" + cover + "</cover>", file=code)
            print("  <trailer>" + trailer + "</trailer>", file=code)
            print("  <website>" + site + "</website>", file=code)
            print("</movie>", file=code)
            logger.info("[+]Wrote!            " + nfo_path)
            return True
    except Exception as e:
        logger.error("[-]Write NFO Failed!")
        logger.error(e)
        return False


def process_cover(tmp_cover_path, prefilename, output_folder):
    """ Cover
    """
    fanartpath = os.path.join(output_folder, prefilename + '-fanart.jpg')
    thumbpath = os.path.join(output_folder, prefilename + '-thumb.jpg')
    shutil.copyfile(tmp_cover_path, fanartpath)
    shutil.copyfile(tmp_cover_path, thumbpath)

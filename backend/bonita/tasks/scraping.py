import logging
import os
import uuid
from urllib.parse import urlparse

from celery import shared_task

from bonita import schemas
from bonita.db import SessionFactory
from bonita.db.models.extrainfo import ExtraInfo
from bonita.db.models.metadata import Metadata
from bonita.db.models.record import TransRecords
from bonita.modules.scraping.number_parser import FileNumInfo, format_part_suffix
from bonita.modules.scraping.scraping import load_all_NFO_from_folder, need_crop, scraping
from bonita.utils.downloader import update_cache_from_local

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='scraping:single')
def celery_scrapping(self, file_path, scraping_dict):
    logger.info(f"    ▸ [刮削] {os.path.basename(file_path)}")
    try:
        session = SessionFactory()
        scraping_conf = schemas.ScrapingConfigPublic(**scraping_dict)
        # 根据路径获取额外自定义信息
        fileNumInfo = FileNumInfo(file_path)
        transfer_record = session.query(TransRecords).filter(
            TransRecords.srcpath == file_path).first()
        extrainfo = session.query(ExtraInfo).filter(ExtraInfo.filepath == file_path).first()
        if not extrainfo:
            extrainfo = ExtraInfo(filepath=file_path)
            extrainfo.number = fileNumInfo.num
            if not need_crop(extrainfo.number):
                extrainfo.crop = False
            extrainfo.tag = ', '.join(map(str, fileNumInfo.tags()))
            extrainfo.create(session)
            # 首次刮削：与原先 ExtraInfo.partNumber 一样，从文件名写入转移记录
            if transfer_record and not transfer_record.part_number:
                transfer_record.part_number = fileNumInfo.partNumber or 0
        else:
            if extrainfo.crop is None:
                if need_crop(extrainfo.number):
                    extrainfo.crop = True
                else:
                    extrainfo.crop = False
        part_number = transfer_record.part_number if transfer_record else 0
        # 处理指定源/强制从网站更新
        metadata_record = None
        if extrainfo.specifiedurl:
            metadata_record = session.query(Metadata).filter(
                Metadata.number == extrainfo.number,
                Metadata.detailurl == extrainfo.specifiedurl).order_by(Metadata.id.desc()).first()
        elif extrainfo.specifiedsource:
            metadata_record = session.query(Metadata).filter(
                Metadata.number == extrainfo.number,
                Metadata.site == extrainfo.specifiedsource).order_by(Metadata.id.desc()).first()
        if not metadata_record:
            metadata_record = session.query(Metadata).filter(
                Metadata.number == extrainfo.number).order_by(Metadata.id.desc()).first()
        if metadata_record:
            logger.info(f"      ✓ 使用缓存: {metadata_record.number}")
            metadata_mixed = schemas.MetadataMixed(**metadata_record.to_dict())
        else:
            # 如果没有找到任何记录，则从网络抓取
            logger.info(f"      → 网络抓取: {extrainfo.number}")
            proxy = get_active_proxy(session)
            json_data = scraping(extrainfo.number,
                                 scraping_conf.scraping_sites,
                                 extrainfo.specifiedsource,
                                 extrainfo.specifiedurl,
                                 proxy
                                 )
            # Return if blank dict returned (data not found)
            if not json_data:
                logger.error("      ✗ 抓取失败")
                return None
            # 数据转换
            metadata_base = schemas.MetadataBase(**json_data)
            metadata_base.number = metadata_base.number.upper()
            filter_dict = Metadata.filter_dict(Metadata, metadata_base.__dict__)
            metadata_record = Metadata(**filter_dict)
            metadata_record.crop = (
                bool(extrainfo.crop) if extrainfo.crop is not None else need_crop(extrainfo.number)
            )
            if scraping_conf.save_metadata:
                metadata_record.create(session)
            metadata_mixed = schemas.MetadataMixed(**metadata_record.to_dict())

        # 根据规则生成文件夹和文件名
        maxlen = scraping_conf.max_title_len
        extra_folder = eval(scraping_conf.location_rule, metadata_mixed.__dict__)
        extra_name = eval(scraping_conf.naming_rule, metadata_mixed.__dict__)
        if 'actor' in scraping_conf.location_rule and len(metadata_mixed.actor) > maxlen:
            extra_folder = eval(scraping_conf.location_rule.replace("actor", "'多人作品'"), metadata_mixed.__dict__)
            extra_name = eval(scraping_conf.naming_rule.replace("actor", "'多人作品'"), metadata_mixed.__dict__)
        if 'title' in scraping_conf.location_rule and len(metadata_mixed.title) > maxlen:
            shorttitle = metadata_mixed.title[0:maxlen]
            extra_folder = extra_folder.replace(metadata_mixed.title, shorttitle)
            extra_name = extra_name.replace(metadata_mixed.title, shorttitle)

        # 清理和验证生成的路径
        # 移除路径中的非法字符
        illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in illegal_chars:
            extra_folder = extra_folder.replace(char, '_')
            extra_name = extra_name.replace(char, '_')
        # 确保路径不为空且不是绝对路径
        extra_folder = extra_folder.strip()
        if not extra_folder or extra_folder.startswith('/') or extra_folder.startswith('\\'):
            extra_folder = metadata_mixed.actor if metadata_mixed.actor else '未分类'
        # 移除路径开头的斜杠和点
        extra_folder = extra_folder.lstrip('/\\.')
        # 替换路径遍历字符
        extra_folder = extra_folder.replace('..', '_')

        metadata_mixed.extra_folder = extra_folder
        metadata_mixed.extra_filename = extra_name
        metadata_mixed.extra_crop = (
            metadata_record.crop if metadata_record.crop is not None else extrainfo.crop
        )

        # 将 extrainfo.tag 中的标签添加到 metadata_base.tag 中，过滤重复的标签
        existing_tags = set(metadata_mixed.tag.split(", ")) if metadata_mixed.tag else set()
        new_tags = set(extrainfo.tag.split(", ")) if extrainfo.tag else set()
        combined_tags = existing_tags.union(new_tags)
        # 过滤掉空字符串
        combined_tags = {tag for tag in combined_tags if tag.strip()}
        metadata_mixed.tag = ", ".join(combined_tags) if combined_tags else ''
        # 更新文件名称，part -C -EP01
        if part_number:
            metadata_mixed.extra_filename += format_part_suffix(part_number)
            metadata_mixed.extra_part = part_number

        return metadata_mixed
    except Exception as e:
        logger.error(e)
    finally:
        session.commit()
        session.close()
    return None

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3},
             name='import:nfo')
def celery_import_nfo(self, folder_path, option):
    logger.info(f"## [NFO导入] START - {folder_path}")
    try:
        metadata_list = load_all_NFO_from_folder(folder_path)
        # 过滤有效的nfo信息
        title_to_metadata = {}
        for nfo_dict in metadata_list:
            title = nfo_dict['nfo'].get('title', '')
            if title:
                if title not in title_to_metadata:
                    title_to_metadata[title] = []
                title_to_metadata[title].append(nfo_dict)
        # 处理重复的title，保留一个有cover_path的
        filtered_metadata_list = []
        for title, nfo_dicts in title_to_metadata.items():
            if len(nfo_dicts) == 1:
                filtered_metadata_list.append(nfo_dicts[0])
            else:
                has_cover = [nfo_dict for nfo_dict in nfo_dicts if nfo_dict['cover_path']]
                if has_cover:
                    filtered_metadata_list.append(has_cover[0])
                else:
                    filtered_metadata_list.append(nfo_dicts[0])

        # 用过滤后的列表替换原始列表
        metadata_list = filtered_metadata_list
        logger.info(f"  找到 {len(filtered_metadata_list)} 个有效 NFO 文件")
        for nfo_dict in metadata_list:
            nfo_data = nfo_dict['nfo']
            cover_path = nfo_dict['cover_path']

            # 确保 actor 字段不为空
            if not nfo_data.get('actor') or nfo_data.get('actor', '').strip() == '':
                nfo_data['actor'] = '佚名'

            try:
                metadata_base = schemas.MetadataBase(**nfo_data)
                # 如果 title 中包含 number，则删除 number
                if metadata_base.number in metadata_base.title:
                    metadata_base.title = metadata_base.title.replace(metadata_base.number, '').strip(' -')
            except Exception as e:
                logger.error(f"  ✗ NFO转换失败: {str(e)}")
                continue
            if metadata_base.site == "" and metadata_base.detailurl:
                # 从detailurl中提取域名作为site
                try:
                    parsed_url = urlparse(metadata_base.detailurl)
                    # 获取域名部分，去掉www.前缀
                    domain = parsed_url.netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    # 提取主域名部分
                    parts = domain.split('.')
                    if len(parts) >= 2:
                        metadata_base.site = parts[-2]  # 取主域名部分
                    else:
                        metadata_base.site = domain
                except Exception:
                    # 如果解析失败，直接使用完整URL
                    metadata_base.site = metadata_base.detailurl
            try:
                session = SessionFactory()
                metadata_record = session.query(Metadata).filter(
                    Metadata.number == metadata_base.number).order_by(Metadata.id.desc()).first()
                # 如果 metadata_record 存在，根据 option 决定是否更新
                if metadata_record:
                    if option == 'ignore':
                        # 忽略重复
                        continue
                    else:
                        # 强制更新
                        session.delete(metadata_record)
                # 从本地更新缓存图片
                if cover_path and os.path.exists(cover_path):
                    if not metadata_base.cover or metadata_base.cover == '':
                        metadata_base.cover = str(uuid.uuid4()).replace('-', '')
                    update_cache_from_local(session, cover_path, metadata_base.number, metadata_base.cover)
                filter_dict = Metadata.filter_dict(Metadata, metadata_base.__dict__)
                metadata_db = Metadata(**filter_dict)
                if metadata_base.number:
                    metadata_db.crop = need_crop(metadata_base.number)
                metadata_db.create(session)
            except Exception as e:
                logger.error(f"  ✗ 导入失败 {os.path.basename(nfo_dict['nfo_path'])}: {str(e)}")
                continue
            finally:
                session.close()
        logger.info("## [NFO导入] END")
    except Exception:
        logger.error("## [NFO导入] ✗ 失败: {str(e)}")
    return True

@shared_task(name="tools:reload_scrapinglib")
def celery_reload_scrapinglib():
    """在 Celery worker 中重新加载 scrapinglib，使工具页升级立即生效"""
    from bonita.utils.scrapinglib_pkg import (
        ensure_extra_site_packages,
        get_installed_version,
        reload_modules,
    )

    ensure_extra_site_packages()
    reload_modules()
    installed = get_installed_version()
    logger.info("Reloaded scrapinglib in celery worker, version=%s", installed)
    return installed

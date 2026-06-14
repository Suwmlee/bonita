import os
import logging
from threading import Thread
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import or_, desc, asc

from bonita.db.models.record import TransRecords
from bonita.db.models.extrainfo import ExtraInfo
from bonita.utils.filehelper import cleanFilebyFilter, cleanFolderWithoutSuffix, video_type

logger = logging.getLogger(__name__)


class RecordService:
    """转移记录服务，提供对转移记录的业务逻辑操作"""

    def __init__(self, session: Session):
        self.session = session
        self._downloader_service = None  # 延迟导入避免循环依赖

    def _get_downloader_service(self):
        """延迟导入 DownloaderService 避免循环依赖"""
        if self._downloader_service is None:
            from bonita.services.downloader_service import DownloaderService
            self._downloader_service = DownloaderService(self.session)
        return self._downloader_service

    def get_records(
        self,
        skip: int = 0,
        limit: int = 100,
        task_id: Optional[int] = None,
        search: Optional[str] = None,
        sort_by: str = "updatetime",
        sort_desc: bool = True
    ) -> Tuple[List[Tuple[TransRecords, Optional[ExtraInfo]]], int]:
        """获取转移记录和额外信息

        Args:
            skip: 跳过记录数
            limit: 限制返回记录数
            task_id: 任务ID过滤
            search: 搜索条件（匹配srcname和srcpath）
            sort_by: 排序字段
            sort_desc: 是否降序排序

        Returns:
            Tuple[List[Tuple[TransRecords, Optional[ExtraInfo]]], int]: 记录列表和总记录数
        """
        query = self.session.query(TransRecords, ExtraInfo).outerjoin(
            ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath)

        # 添加过滤条件
        if task_id is not None:
            query = query.filter(TransRecords.task_id == task_id)
        if search is not None:
            query = query.filter(
                or_(
                    TransRecords.srcname.like(f"%{search}%"),
                    TransRecords.srcpath.like(f"%{search}%")
                )
            )

        # 添加排序
        sort_field = getattr(TransRecords, sort_by, TransRecords.updatetime)
        if sort_desc:
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(asc(sort_field))

        # 应用分页
        records = query.offset(skip).limit(limit).all()

        # 获取总记录数时也要应用过滤条件
        count_query = self.session.query(TransRecords)
        if task_id is not None:
            count_query = count_query.filter(TransRecords.task_id == task_id)
        if search is not None:
            count_query = count_query.filter(
                or_(
                    TransRecords.srcname.like(f"%{search}%"),
                    TransRecords.srcpath.like(f"%{search}%")
                )
            )

        count = count_query.count()
        return records, count

    def get_record_by_id(self, record_id: int) -> Tuple[Optional[TransRecords], Optional[ExtraInfo]]:
        """通过ID获取转移记录和额外信息

        Args:
            record_id: 记录ID

        Returns:
            Tuple[Optional[TransRecords], Optional[ExtraInfo]]: 记录和额外信息
        """
        result = self.session.query(TransRecords, ExtraInfo).outerjoin(
            ExtraInfo, TransRecords.srcpath == ExtraInfo.filepath).filter(TransRecords.id == record_id).first()

        if not result:
            return None, None

        return result[0], result[1]

    def update_record(self, record: TransRecords, update_dict: dict) -> TransRecords:
        """更新转移记录

        Args:
            record: 记录对象
            update_dict: 更新字段字典

        Returns:
            TransRecords: 更新后的记录对象
        """
        for key, value in update_dict.items():
            if hasattr(record, key):
                setattr(record, key, value)

        self.session.commit()
        return record

    def update_top_folder(self, srcfolder: str, old_top_folder: str, new_top_folder: str) -> Tuple[bool, str, int]:
        """批量更新top_folder

        Args:
            srcfolder: 源文件夹
            old_top_folder: 旧的top_folder值
            new_top_folder: 新的top_folder值

        Returns:
            Tuple[bool, str, int]: 成功状态、消息和更新的记录数
        """
        query = self.session.query(TransRecords).filter(
            TransRecords.srcfolder == srcfolder,
            TransRecords.top_folder == old_top_folder
        )

        records_count = query.count()

        if records_count == 0:
            return False, f"没有找到匹配的记录: srcfolder={srcfolder}, top_folder={old_top_folder}", 0

        if records_count > 0:
            query.update({"top_folder": new_top_folder, "updatetime": datetime.now()})
            self.session.commit()

        return True, f"成功更新 {records_count} 条记录的 top_folder 从 '{old_top_folder}' 到 '{new_top_folder}'", records_count

    @staticmethod
    def _season_to_second_folder(season: int) -> str:
        if season == 0:
            return "Specials"
        if season > 0:
            return f"Season {season}"
        return ""

    def update_season(self, srcfolder: str, old_season: int, new_season: int) -> Tuple[bool, str, int]:
        """批量更新 season

        更新源文件夹上层目录相同且 season 相同的所有记录

        Args:
            srcfolder: 源文件夹
            old_season: 旧的 season 值
            new_season: 新的 season 值

        Returns:
            Tuple[bool, str, int]: 成功状态、消息和更新的记录数
        """
        parent_srcfolder = os.path.dirname(srcfolder.rstrip("/"))
        if not parent_srcfolder:
            return False, "无法确定源文件夹的上层目录", 0

        parent_prefix = f"{parent_srcfolder}/"
        query = self.session.query(TransRecords).filter(
            TransRecords.season == old_season,
            TransRecords.srcfolder.like(f"{parent_prefix}%"),
            ~TransRecords.srcfolder.like(f"{parent_prefix}%/%"),
        )

        records_count = query.count()
        if records_count == 0:
            return False, (
                f"没有找到匹配的记录: 上层目录={parent_srcfolder}, season={old_season}"
            ), 0

        update_values = {"season": new_season, "updatetime": datetime.now()}
        if new_season > -1:
            update_values["second_folder"] = self._season_to_second_folder(new_season)

        query.update(update_values)
        self.session.commit()

        return True, (
            f"成功更新 {records_count} 条记录的 season 从 {old_season} 到 {new_season}"
        ), records_count

    def _replace_path_prefix(self, path: str, old_prefix: str, new_prefix: str) -> str:
        """将路径中的旧前缀替换为新前缀"""
        if not path or not path.startswith(old_prefix):
            return path
        return new_prefix + path[len(old_prefix):]

    def update_src_path_prefix(
        self,
        old_prefix: str,
        new_prefix: str,
        task_id: Optional[int] = None
    ) -> Tuple[bool, str, int, int]:
        """批量替换转移记录的源路径前缀

        同时更新关联的 ExtraInfo.filepath，以保持自定义内容关联。

        Args:
            old_prefix: 旧路径前缀
            new_prefix: 新路径前缀
            task_id: 可选，仅更新指定任务的记录

        Returns:
            Tuple[bool, str, int, int]: 成功状态、消息、更新的记录数和更新的 ExtraInfo 数
        """
        old_prefix = old_prefix.rstrip("/")
        new_prefix = new_prefix.rstrip("/")

        if not old_prefix:
            return False, "旧路径前缀不能为空", 0, 0

        if old_prefix == new_prefix:
            return False, "新旧路径前缀相同，无需更新", 0, 0

        query = self.session.query(TransRecords).filter(
            or_(
                TransRecords.srcpath == old_prefix,
                TransRecords.srcpath.startswith(f"{old_prefix}/")
            )
        )
        if task_id is not None:
            query = query.filter(TransRecords.task_id == task_id)

        records = query.all()
        if not records:
            scope = f" (task_id={task_id})" if task_id is not None else ""
            return False, f"没有找到 srcpath 以 '{old_prefix}' 开头的记录{scope}", 0, 0

        updated_records = 0
        updated_extrainfo = 0
        skipped = 0

        for record in records:
            old_srcpath = record.srcpath
            new_srcpath = self._replace_path_prefix(old_srcpath, old_prefix, new_prefix)

            existing_record = self.session.query(TransRecords).filter(
                TransRecords.srcpath == new_srcpath,
                TransRecords.id != record.id
            ).first()
            if existing_record:
                skipped += 1
                continue

            extra_info = self.session.query(ExtraInfo).filter(ExtraInfo.filepath == old_srcpath).first()
            if extra_info:
                existing_extra = self.session.query(ExtraInfo).filter(
                    ExtraInfo.filepath == new_srcpath,
                    ExtraInfo.id != extra_info.id
                ).first()
                if existing_extra:
                    skipped += 1
                    continue
                extra_info.filepath = new_srcpath
                updated_extrainfo += 1

            record.srcpath = new_srcpath
            record.srcfolder = self._replace_path_prefix(record.srcfolder, old_prefix, new_prefix)
            record.updatetime = datetime.now()
            updated_records += 1

        if updated_records == 0:
            return False, f"未更新任何记录（跳过 {skipped} 条冲突记录）", 0, 0

        self.session.commit()

        message = (
            f"成功将路径前缀从 '{old_prefix}' 替换为 '{new_prefix}'，"
            f"更新 {updated_records} 条转移记录"
        )
        if updated_extrainfo:
            message += f"，同步更新 {updated_extrainfo} 条 ExtraInfo"
        if skipped:
            message += f"，跳过 {skipped} 条冲突记录"

        return True, message, updated_records, updated_extrainfo

    def delete_records(
        self,
        record_ids: List[int],
        force: bool = False
    ) -> Tuple[bool, str, int, List[int]]:
        """删除记录

        Args:
            record_ids: 记录ID列表
            force: 是否强制删除源文件和 Transmission 种子

        Returns:
            Tuple[bool, str, int, List[int]]: 成功状态、消息、成功删除数和失败ID列表
        """
        if not record_ids:
            return False, "未提供记录ID", 0, []

        deleted_count = 0
        failed_ids = []
        records_for_torrent_deletion = []

        for record_id in record_ids:
            transfer_record, extra_info = self.get_record_by_id(record_id)

            if not transfer_record:
                failed_ids.append(record_id)
                continue

            # 如果需要强制删除，保存记录用于后续删除种子
            if force and transfer_record.srcpath:
                records_for_torrent_deletion.append(transfer_record)

            dest_path = transfer_record.destpath
            src_path = transfer_record.srcpath

            # 删除关联的额外信息
            if extra_info:
                self.session.delete(extra_info)

            if force:
                # 如果强制删除，那么也删除源文件和记录
                self.session.delete(transfer_record)
                self.session.commit()
                # 文件系统操作放到后台线程，避免网络挂载路径阻塞请求
                self._clean_files_async(dest_path)
                self._clean_files_async(src_path)
            else:
                # 清除状态，可以重新转移
                reset_dict = {
                    'top_folder': '',
                    'second_folder': '',
                    'isepisode': False,
                    'season': -1,
                    'episode': -1,
                    'deleted': True,
                    'deadtime': datetime.now() + timedelta(days=7)
                }
                self.update_record(transfer_record, reset_dict)
                # 文件系统操作放到后台线程，避免网络挂载路径阻塞请求
                self._clean_files_async(dest_path)

            deleted_count += 1

        # 如果强制删除，尝试删除 Transmission 种子
        torrent_info_msg = ""
        if force and records_for_torrent_deletion:
            try:
                downloader_service = self._get_downloader_service()
                if downloader_service.initialize_transmission():
                    deleted_torrents, skipped_torrents = downloader_service.delete_torrents_by_records(
                        records_for_torrent_deletion,
                        check_video_files=True
                    )
                    torrent_info_msg = f"，删除种子 {deleted_torrents} 个，跳过 {skipped_torrents} 个"
                    logger.info(f"Deleted {deleted_torrents} torrents, skipped {skipped_torrents} torrents")
            except Exception as e:
                logger.error(f"删除种子失败: {str(e)}")
                torrent_info_msg = f"，种子删除失败: {str(e)}"

        success = deleted_count > 0

        if failed_ids:
            message = f"已删除 {deleted_count} 条记录{torrent_info_msg}。无法删除ID: {failed_ids}"
        else:
            message = f"成功删除 {deleted_count} 条记录{torrent_info_msg}"

        return success, message, deleted_count, failed_ids

    def get_trans_records(self, skip: int = 0, limit: int = 100) -> Tuple[List[TransRecords], int]:
        """获取所有转移记录

        Args:
            skip: 跳过记录数
            limit: 限制返回记录数

        Returns:
            Tuple[List[TransRecords], int]: 记录列表和总记录数
        """
        trans_records = self.session.query(TransRecords).offset(skip).limit(limit).all()
        count = self.session.query(TransRecords).count()

        return trans_records, count

    def get_records_to_cleanup(self, force: bool = False) -> List[TransRecords]:
        """获取需要清理的记录（过期或标记为已删除源文件的记录）
        在返回结果前，会检查文件是否真的不存在，如果文件仍然存在，会更新记录状态并延长过期时间
        忽略标记为ignored的记录

        清理规则：
        1. 源文件不存在，则标记为需要清理
        2. 目标文件不存在且已超过过期时间，则标记为需要清理

        Returns:
            List[TransRecords]: 需要清理的记录列表
        """
        current_time = datetime.now()
        # 首先获取潜在需要清理的记录
        potential_records = self.session.query(TransRecords).filter(
            or_(
                TransRecords.srcdeleted == True,
                TransRecords.deadtime.isnot(None)
            ),
            TransRecords.ignored == False
        ).all()

        # 筛选确实需要清理的记录
        records_to_cleanup = []
        for record in potential_records:
            src_exists = record.srcpath and os.path.exists(record.srcpath)
            dest_exists = record.destpath and os.path.exists(record.destpath)
            # 更新源文件是否存在的状态
            if record.srcdeleted == src_exists:
                record.srcdeleted = not src_exists
                self.session.commit()
            # 根据源文件和目标文件状态决定是否需要清理
            if not src_exists:
                # 源文件不存在，需要清理
                records_to_cleanup.append(record)
            elif not dest_exists and record.deadtime:
                # 如果有强制标记，忽视时间限制，直接清理
                # 否则，目标文件不存在且已超过过期时间，需要清理
                if force or record.deadtime <= current_time:
                    records_to_cleanup.append(record)
            else:
                # 文件都存在或未超过过期时间，不需要清理，重置状态
                record.deleted = False
                record.deadtime = None
                self.session.commit()

        return records_to_cleanup

    def _clean_files_async(self, file_path: str) -> None:
        """在后台守护线程中异步清理文件，避免网络挂载路径阻塞请求

        Args:
            file_path: 文件路径
        """
        if not file_path:
            return
        t = Thread(target=self._clean_files, args=(file_path,), daemon=True)
        t.start()

    def _clean_files(self, file_path: str) -> None:
        """清理文件及相关文件

        Args:
            file_path: 文件路径
        """
        if not file_path:
            return

        clean_folder = os.path.dirname(file_path)
        name_filter = os.path.splitext(os.path.basename(file_path))[0]

        cleanFilebyFilter(clean_folder, name_filter)
        cleanFolderWithoutSuffix(clean_folder, video_type)

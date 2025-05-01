import os
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import or_, desc, asc

from bonita.db.models.record import TransRecords
from bonita.db.models.extrainfo import ExtraInfo
from bonita.utils.filehelper import cleanFilebyFilter, cleanFolderWithoutSuffix, video_type


class RecordService:
    """转移记录服务，提供对转移记录的业务逻辑操作"""

    def __init__(self, session: Session):
        self.session = session

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

    def delete_records(self, record_ids: List[int], force: bool = False) -> Tuple[bool, str, int, List[int]]:
        """删除记录

        Args:
            record_ids: 记录ID列表
            force: 是否强制删除源文件

        Returns:
            Tuple[bool, str, int, List[int]]: 成功状态、消息、成功删除数和失败ID列表
        """
        if not record_ids:
            return False, "未提供记录ID", 0, []

        deleted_count = 0
        failed_ids = []

        for record_id in record_ids:
            transfer_record, extra_info = self.get_record_by_id(record_id)

            if not transfer_record:
                failed_ids.append(record_id)
                continue

            # 默认删除目标路径的文件
            self._clean_files(transfer_record.destpath)

            # 删除关联的额外信息
            if extra_info:
                self.session.delete(extra_info)

            if force:
                # 如果强制删除，那么也删除源文件和记录
                self._clean_files(transfer_record.srcpath)
                self.session.delete(transfer_record)
                self.session.commit()
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

            deleted_count += 1

        success = deleted_count > 0

        if failed_ids:
            message = f"已删除 {deleted_count} 条记录。无法删除ID: {failed_ids}"
        else:
            message = f"成功删除 {deleted_count} 条记录"

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

    def get_records_to_cleanup(self, current_time: datetime) -> List[TransRecords]:
        """获取需要清理的记录（过期或标记为已删除源文件的记录）
        
        Args:
            current_time: 当前时间，用于比较deadtime

        Returns:
            List[TransRecords]: 需要清理的记录列表
        """
        return self.session.query(TransRecords).filter(
            or_(
                TransRecords.srcdeleted == True,
                TransRecords.deadtime.isnot(None) & (TransRecords.deadtime <= current_time)
            )
        ).all()

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

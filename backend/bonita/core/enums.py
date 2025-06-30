from enum import Enum


class TaskStatusEnum(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"       # 等待中
    PROGRESS = "PROGRESS"     # 进行中
    SUCCESS = "SUCCESS"       # 成功
    FAILURE = "FAILURE"       # 失败
    REVOKED = "REVOKED"       # 已取消

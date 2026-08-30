class ServiceError(Exception):
    """业务错误，由路由映射为 HTTP 状态。"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class ForbiddenError(ServiceError):
    pass


class InvalidInputError(ServiceError):
    pass

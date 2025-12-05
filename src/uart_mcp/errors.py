"""错误码定义模块

定义所有串口操作相关的错误码和异常类。
"""

from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """错误码枚举

    定义所有串口操作可能返回的错误码。
    """

    PORT_NOT_FOUND = 1001  # 串口不存在
    PORT_BUSY = 1002  # 串口被占用
    PORT_OPEN_FAILED = 1003  # 串口打开失败
    PORT_CLOSED = 1004  # 串口已关闭
    INVALID_PARAM = 1005  # 参数无效
    READ_TIMEOUT = 1006  # 读取超时
    WRITE_FAILED = 1007  # 写入失败
    PERMISSION_DENIED = 1008  # 权限不足
    PORT_BLACKLISTED = 1009  # 串口在黑名单中


# 错误码对应的中文消息
ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.PORT_NOT_FOUND: "串口不存在",
    ErrorCode.PORT_BUSY: "串口被占用",
    ErrorCode.PORT_OPEN_FAILED: "串口打开失败",
    ErrorCode.PORT_CLOSED: "串口已关闭",
    ErrorCode.INVALID_PARAM: "参数无效",
    ErrorCode.READ_TIMEOUT: "读取超时",
    ErrorCode.WRITE_FAILED: "写入失败",
    ErrorCode.PERMISSION_DENIED: "权限不足",
    ErrorCode.PORT_BLACKLISTED: "串口在黑名单中",
}


class SerialError(Exception):
    """串口操作异常基类

    所有串口相关的异常都继承自此类。

    Attributes:
        code: 错误码
        message: 错误消息
        detail: 额外的错误详情
    """

    def __init__(
        self, code: ErrorCode, detail: str | None = None, **kwargs: Any
    ) -> None:
        """初始化串口异常

        Args:
            code: 错误码
            detail: 额外的错误详情，会附加到默认消息后
            **kwargs: 其他参数，用于格式化消息
        """
        self.code = code
        base_message = ERROR_MESSAGES.get(code, "未知错误")
        self.message = f"{base_message}：{detail}" if detail else base_message
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式

        Returns:
            包含错误码和消息的字典
        """
        return {"error": {"code": int(self.code), "message": self.message}}


class PortNotFoundError(SerialError):
    """串口不存在异常"""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PORT_NOT_FOUND, port)


class PortBusyError(SerialError):
    """串口被占用异常"""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PORT_BUSY, port)


class PortOpenFailedError(SerialError):
    """串口打开失败异常"""

    def __init__(self, port: str, reason: str | None = None) -> None:
        detail = f"{port}" if not reason else f"{port} - {reason}"
        super().__init__(ErrorCode.PORT_OPEN_FAILED, detail)


class PortClosedError(SerialError):
    """串口已关闭异常"""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PORT_CLOSED, port)


class InvalidParamError(SerialError):
    """参数无效异常"""

    def __init__(self, param: str, value: Any, reason: str | None = None) -> None:
        detail = f"{param}={value}"
        if reason:
            detail = f"{detail} ({reason})"
        super().__init__(ErrorCode.INVALID_PARAM, detail)


class PermissionDeniedError(SerialError):
    """权限不足异常"""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PERMISSION_DENIED, port)


class PortBlacklistedError(SerialError):
    """串口在黑名单中异常"""

    def __init__(self, port: str) -> None:
        super().__init__(ErrorCode.PORT_BLACKLISTED, port)


class WriteFailedError(SerialError):
    """写入失败异常"""

    def __init__(self, port: str, reason: str | None = None) -> None:
        detail = f"{port}" if not reason else f"{port} - {reason}"
        super().__init__(ErrorCode.WRITE_FAILED, detail)

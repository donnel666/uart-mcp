"""数据通信工具实现

提供串口数据收发功能，支持文本模式和二进制模式。
"""

import base64
from typing import Any

from ..errors import InvalidParamError
from ..serial_manager import get_serial_manager


def send_data(
    port: str,
    data: str,
    is_binary: bool = False,
) -> dict[str, Any]:
    """发送数据到串口

    Args:
        port: 串口路径
        data: 要发送的数据（文本模式为 UTF-8 字符串，二进制模式为 Base64 编码）
        is_binary: 是否为二进制模式

    Returns:
        发送结果，包含发送的字节数
    """
    manager = get_serial_manager()

    # 编码转换
    if is_binary:
        try:
            raw_data = base64.b64decode(data)
        except Exception as e:
            raise InvalidParamError("data", data, f"Base64 解码失败：{e}")
    else:
        raw_data = data.encode("utf-8")

    bytes_written = manager.send_data(port, raw_data)
    return {"success": True, "bytes_written": bytes_written}


def read_data(
    port: str,
    size: int | None = None,
    timeout_ms: int | None = None,
    is_binary: bool = False,
) -> dict[str, Any]:
    """从串口读取数据

    Args:
        port: 串口路径
        size: 读取字节数，None 表示读取所有可用数据
        timeout_ms: 读取超时（毫秒），None 使用串口配置的超时
        is_binary: 是否为二进制模式

    Returns:
        读取结果，包含数据和字节数
    """
    manager = get_serial_manager()
    raw_data = manager.read_data(port, size, timeout_ms)

    # 解码转换
    if is_binary:
        result_data = base64.b64encode(raw_data).decode("ascii")
    else:
        result_data = raw_data.decode("utf-8", errors="replace")

    return {"data": result_data, "bytes_read": len(raw_data)}


# 工具定义（用于 MCP 注册）
SEND_DATA_TOOL: dict[str, Any] = {
    "name": "send_data",
    "description": "向已打开的串口发送数据，支持文本和二进制模式",
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "串口路径，如 /dev/ttyUSB0 或 COM1",
            },
            "data": {
                "type": "string",
                "description": "要发送的数据（文本为UTF-8，二进制为Base64）",
            },
            "is_binary": {
                "type": "boolean",
                "description": "是否为二进制模式，True 时 data 为 Base64 编码",
                "default": False,
            },
        },
        "required": ["port", "data"],
    },
}

READ_DATA_TOOL: dict[str, Any] = {
    "name": "read_data",
    "description": "从已打开的串口读取数据，支持文本和二进制模式",
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "串口路径，如 /dev/ttyUSB0 或 COM1",
            },
            "size": {
                "type": "integer",
                "description": "读取字节数，不指定则读取所有可用数据",
            },
            "timeout_ms": {
                "type": "integer",
                "description": "读取超时（毫秒），不指定则使用串口配置的超时",
            },
            "is_binary": {
                "type": "boolean",
                "description": "是否为二进制模式，True 时返回 Base64 编码",
                "default": False,
            },
        },
        "required": ["port"],
    },
}

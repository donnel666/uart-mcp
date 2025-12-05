"""串口操作工具实现

提供打开、关闭、配置串口等功能。
"""

from typing import Any

from ..serial_manager import get_serial_manager
from ..types import (
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_FLOW_CONTROL,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DEFAULT_TIMEOUT_MS,
    DEFAULT_WRITE_TIMEOUT_MS,
    SUPPORTED_BAUDRATES,
    SUPPORTED_BYTESIZES,
    FlowControl,
    Parity,
    StopBits,
)


def open_port(
    port: str,
    baudrate: int = DEFAULT_BAUDRATE,
    bytesize: int = DEFAULT_BYTESIZE,
    parity: str = DEFAULT_PARITY.value,
    stopbits: float = float(DEFAULT_STOPBITS.value),
    flow_control: str = DEFAULT_FLOW_CONTROL.value,
    read_timeout_ms: int = DEFAULT_TIMEOUT_MS,
    write_timeout_ms: int = DEFAULT_WRITE_TIMEOUT_MS,
    auto_reconnect: bool = True,
) -> dict[str, Any]:
    """打开串口

    Args:
        port: 串口路径（如 /dev/ttyUSB0 或 COM1）
        baudrate: 波特率，默认 9600
        bytesize: 数据位，默认 8
        parity: 校验位，默认 N（无校验）
        stopbits: 停止位，默认 1
        flow_control: 流控制，默认 none
        read_timeout_ms: 读取超时（毫秒），默认 1000
        write_timeout_ms: 写入超时（毫秒），默认 1000
        auto_reconnect: 是否启用自动重连，默认 True

    Returns:
        串口状态信息
    """
    manager = get_serial_manager()
    status = manager.open_port(
        port=port,
        baudrate=baudrate,
        bytesize=bytesize,
        parity=parity,
        stopbits=stopbits,
        flow_control=flow_control,
        read_timeout_ms=read_timeout_ms,
        write_timeout_ms=write_timeout_ms,
        auto_reconnect=auto_reconnect,
    )
    return status.to_dict()


def close_port(port: str) -> dict[str, Any]:
    """关闭串口

    Args:
        port: 串口路径

    Returns:
        操作结果
    """
    manager = get_serial_manager()
    return manager.close_port(port)


def set_config(
    port: str,
    baudrate: int | None = None,
    bytesize: int | None = None,
    parity: str | None = None,
    stopbits: float | None = None,
    flow_control: str | None = None,
    read_timeout_ms: int | None = None,
    write_timeout_ms: int | None = None,
) -> dict[str, Any]:
    """修改串口配置（热更新）

    Args:
        port: 串口路径
        baudrate: 波特率（可选）
        bytesize: 数据位（可选）
        parity: 校验位（可选）
        stopbits: 停止位（可选）
        flow_control: 流控制（可选）
        read_timeout_ms: 读取超时（可选）
        write_timeout_ms: 写入超时（可选）

    Returns:
        更新后的串口状态
    """
    manager = get_serial_manager()
    status = manager.set_config(
        port=port,
        baudrate=baudrate,
        bytesize=bytesize,
        parity=parity,
        stopbits=stopbits,
        flow_control=flow_control,
        read_timeout_ms=read_timeout_ms,
        write_timeout_ms=write_timeout_ms,
    )
    return status.to_dict()


def get_status(port: str) -> dict[str, Any]:
    """获取串口状态

    Args:
        port: 串口路径

    Returns:
        串口状态信息
    """
    manager = get_serial_manager()
    status = manager.get_status(port)
    return status.to_dict()


# 工具定义（用于 MCP 注册）
OPEN_PORT_TOOL: dict[str, Any] = {
    "name": "open_port",
    "description": "打开指定串口，支持自定义配置参数",
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "串口路径，如 /dev/ttyUSB0 或 COM1",
            },
            "baudrate": {
                "type": "integer",
                "description": f"波特率，支持的值：{list(SUPPORTED_BAUDRATES)}",
                "default": DEFAULT_BAUDRATE,
            },
            "bytesize": {
                "type": "integer",
                "description": f"数据位，支持的值：{list(SUPPORTED_BYTESIZES)}",
                "default": DEFAULT_BYTESIZE,
            },
            "parity": {
                "type": "string",
                "description": f"校验位，支持的值：{[p.value for p in Parity]}",
                "default": DEFAULT_PARITY.value,
            },
            "stopbits": {
                "type": "number",
                "description": f"停止位，支持的值：{[s.value for s in StopBits]}",
                "default": float(DEFAULT_STOPBITS.value),
            },
            "flow_control": {
                "type": "string",
                "description": f"流控制，支持的值：{[f.value for f in FlowControl]}",
                "default": DEFAULT_FLOW_CONTROL.value,
            },
            "read_timeout_ms": {
                "type": "integer",
                "description": "读取超时（毫秒），范围 0-60000",
                "default": DEFAULT_TIMEOUT_MS,
            },
            "write_timeout_ms": {
                "type": "integer",
                "description": "写入超时（毫秒），范围 0-60000",
                "default": DEFAULT_WRITE_TIMEOUT_MS,
            },
            "auto_reconnect": {
                "type": "boolean",
                "description": "是否启用自动重连",
                "default": True,
            },
        },
        "required": ["port"],
    },
}

CLOSE_PORT_TOOL: dict[str, Any] = {
    "name": "close_port",
    "description": "关闭指定串口连接",
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "串口路径",
            },
        },
        "required": ["port"],
    },
}

SET_CONFIG_TOOL: dict[str, Any] = {
    "name": "set_config",
    "description": "修改已打开串口的配置（热更新，无需关闭重开）",
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "串口路径",
            },
            "baudrate": {
                "type": "integer",
                "description": f"波特率，支持的值：{list(SUPPORTED_BAUDRATES)}",
            },
            "bytesize": {
                "type": "integer",
                "description": f"数据位，支持的值：{list(SUPPORTED_BYTESIZES)}",
            },
            "parity": {
                "type": "string",
                "description": f"校验位，支持的值：{[p.value for p in Parity]}",
            },
            "stopbits": {
                "type": "number",
                "description": f"停止位，支持的值：{[s.value for s in StopBits]}",
            },
            "flow_control": {
                "type": "string",
                "description": f"流控制，支持的值：{[f.value for f in FlowControl]}",
            },
            "read_timeout_ms": {
                "type": "integer",
                "description": "读取超时（毫秒），范围 0-60000",
            },
            "write_timeout_ms": {
                "type": "integer",
                "description": "写入超时（毫秒），范围 0-60000",
            },
        },
        "required": ["port"],
    },
}

GET_STATUS_TOOL: dict[str, Any] = {
    "name": "get_status",
    "description": "获取已打开串口的当前状态和配置信息",
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "串口路径",
            },
        },
        "required": ["port"],
    },
}

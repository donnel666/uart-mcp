"""list_ports 工具实现

提供枚举系统所有可用串口设备的功能。
"""

from typing import Any

from ..serial_manager import get_serial_manager


def list_ports() -> list[dict[str, str]]:
    """列出所有可用串口设备

    返回系统中所有可用的串口设备列表，已过滤黑名单中的串口。

    Returns:
        串口信息列表，每个元素包含 port、description、hwid 字段
    """
    manager = get_serial_manager()
    ports = manager.list_ports()
    return [p.to_dict() for p in ports]


# 工具定义（用于 MCP 注册）
LIST_PORTS_TOOL: dict[str, Any] = {
    "name": "list_ports",
    "description": "列出所有可用串口设备，返回设备路径、描述信息和硬件ID",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

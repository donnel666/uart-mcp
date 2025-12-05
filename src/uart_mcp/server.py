"""MCP Server 实现

提供 UART MCP Server 的主服务器逻辑。
"""

import asyncio
import logging
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .errors import SerialError
from .serial_manager import get_serial_manager
from .tools.data_ops import (
    READ_DATA_TOOL,
    SEND_DATA_TOOL,
    read_data,
    send_data,
)
from .tools.list_ports import LIST_PORTS_TOOL, list_ports
from .tools.port_ops import (
    CLOSE_PORT_TOOL,
    GET_STATUS_TOOL,
    OPEN_PORT_TOOL,
    SET_CONFIG_TOOL,
    close_port,
    get_status,
    open_port,
    set_config,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建 MCP Server
server = Server("uart-mcp")


@server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def handle_list_tools() -> list[types.Tool]:
    """返回可用工具列表"""
    return [
        types.Tool(
            name=LIST_PORTS_TOOL["name"],
            description=LIST_PORTS_TOOL["description"],
            inputSchema=LIST_PORTS_TOOL["inputSchema"],
        ),
        types.Tool(
            name=OPEN_PORT_TOOL["name"],
            description=OPEN_PORT_TOOL["description"],
            inputSchema=OPEN_PORT_TOOL["inputSchema"],
        ),
        types.Tool(
            name=CLOSE_PORT_TOOL["name"],
            description=CLOSE_PORT_TOOL["description"],
            inputSchema=CLOSE_PORT_TOOL["inputSchema"],
        ),
        types.Tool(
            name=SET_CONFIG_TOOL["name"],
            description=SET_CONFIG_TOOL["description"],
            inputSchema=SET_CONFIG_TOOL["inputSchema"],
        ),
        types.Tool(
            name=GET_STATUS_TOOL["name"],
            description=GET_STATUS_TOOL["description"],
            inputSchema=GET_STATUS_TOOL["inputSchema"],
        ),
        types.Tool(
            name=SEND_DATA_TOOL["name"],
            description=SEND_DATA_TOOL["description"],
            inputSchema=SEND_DATA_TOOL["inputSchema"],
        ),
        types.Tool(
            name=READ_DATA_TOOL["name"],
            description=READ_DATA_TOOL["description"],
            inputSchema=READ_DATA_TOOL["inputSchema"],
        ),
    ]


@server.call_tool()  # type: ignore[untyped-decorator]
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    """处理工具调用"""
    try:
        result: Any
        if name == "list_ports":
            result = list_ports()
        elif name == "open_port":
            result = open_port(**arguments)
        elif name == "close_port":
            result = close_port(**arguments)
        elif name == "set_config":
            result = set_config(**arguments)
        elif name == "get_status":
            result = get_status(**arguments)
        elif name == "send_data":
            result = send_data(**arguments)
        elif name == "read_data":
            result = read_data(**arguments)
        else:
            raise ValueError(f"未知工具：{name}")

        # 返回 JSON 格式结果
        import json

        text = json.dumps(result, ensure_ascii=False)
        return [types.TextContent(type="text", text=text)]

    except SerialError as e:
        # 串口错误，返回错误信息
        import json

        text = json.dumps(e.to_dict(), ensure_ascii=False)
        return [types.TextContent(type="text", text=text)]

    except Exception as e:
        # 其他错误
        import json

        error_response = {"error": {"code": -1, "message": f"内部错误：{e!s}"}}
        text = json.dumps(error_response, ensure_ascii=False)
        return [types.TextContent(type="text", text=text)]


async def run_server() -> None:
    """运行 MCP 服务器"""
    logger.info("启动 UART MCP Server...")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="uart-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    """主入口函数"""
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    finally:
        # 关闭串口管理器
        manager = get_serial_manager()
        manager.shutdown()
        logger.info("UART MCP Server 已关闭")


if __name__ == "__main__":
    main()

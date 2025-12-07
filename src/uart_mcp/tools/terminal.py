"""终端会话工具实现

提供终端会话的创建、管理和数据收发功能。
"""

from typing import Any

from ..terminal_manager import get_terminal_manager
from ..types import DEFAULT_BUFFER_SIZE, DEFAULT_LOCAL_ECHO


def create_session(
    port: str,
    line_ending: str = "CRLF",
    local_echo: bool = DEFAULT_LOCAL_ECHO,
    buffer_size: int = DEFAULT_BUFFER_SIZE,
) -> dict[str, Any]:
    """在已打开串口上创建终端会话

    Args:
        port: 串口路径
        line_ending: 换行符类型（CR/LF/CRLF）
        local_echo: 是否本地回显
        buffer_size: 输出缓冲区大小

    Returns:
        会话信息
    """
    manager = get_terminal_manager()
    session_info = manager.create_session(
        port=port,
        line_ending=line_ending,
        local_echo=local_echo,
        buffer_size=buffer_size,
    )
    return session_info.to_dict()


def close_session(session_id: str) -> dict[str, Any]:
    """关闭指定终端会话

    Args:
        session_id: 会话ID（串口路径）

    Returns:
        操作结果
    """
    manager = get_terminal_manager()
    return manager.close_session(session_id)


def send_command(
    session_id: str,
    command: str,
    add_line_ending: bool = True,
) -> dict[str, Any]:
    """向终端发送命令

    Args:
        session_id: 会话ID（串口路径）
        command: 要发送的命令
        add_line_ending: 是否自动添加换行符

    Returns:
        发送结果
    """
    manager = get_terminal_manager()
    return manager.send_command(
        session_id=session_id,
        command=command,
        add_line_ending=add_line_ending,
    )


def read_output(
    session_id: str,
    clear: bool = True,
) -> dict[str, Any]:
    """读取终端输出缓冲区内容

    Args:
        session_id: 会话ID（串口路径）
        clear: 是否清空缓冲区

    Returns:
        输出内容
    """
    manager = get_terminal_manager()
    return manager.read_output(session_id=session_id, clear=clear)


def list_sessions() -> dict[str, Any]:
    """列出所有活动会话

    Returns:
        会话列表
    """
    manager = get_terminal_manager()
    sessions = manager.list_sessions()
    return {"sessions": sessions, "count": len(sessions)}


def get_session_info(session_id: str) -> dict[str, Any]:
    """获取会话详细信息

    Args:
        session_id: 会话ID（串口路径）

    Returns:
        会话信息
    """
    manager = get_terminal_manager()
    return manager.get_session_info(session_id)


def clear_buffer(session_id: str) -> dict[str, Any]:
    """清空会话输出缓冲区

    Args:
        session_id: 会话ID（串口路径）

    Returns:
        操作结果
    """
    manager = get_terminal_manager()
    return manager.clear_buffer(session_id)


# 工具定义（用于 MCP 注册）

CREATE_SESSION_TOOL: dict[str, Any] = {
    "name": "create_session",
    "description": "在已打开串口上创建终端会话，支持配置换行符和本地回显",
    "inputSchema": {
        "type": "object",
        "properties": {
            "port": {
                "type": "string",
                "description": "串口路径，如 /dev/ttyUSB0 或 COM1",
            },
            "line_ending": {
                "type": "string",
                "description": "换行符类型：CR（回车）、LF（换行）、CRLF（回车换行）",
                "enum": ["CR", "LF", "CRLF"],
                "default": "CRLF",
            },
            "local_echo": {
                "type": "boolean",
                "description": "是否本地回显发送的命令",
                "default": False,
            },
            "buffer_size": {
                "type": "integer",
                "description": "输出缓冲区大小（字节），默认 64KB",
                "default": DEFAULT_BUFFER_SIZE,
            },
        },
        "required": ["port"],
    },
}

CLOSE_SESSION_TOOL: dict[str, Any] = {
    "name": "close_session",
    "description": "关闭指定的终端会话",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "会话ID（即串口路径），如 /dev/ttyUSB0 或 COM1",
            },
        },
        "required": ["session_id"],
    },
}

SEND_COMMAND_TOOL: dict[str, Any] = {
    "name": "send_command",
    "description": "向终端发送命令，可选择是否自动添加换行符",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "会话ID（即串口路径），如 /dev/ttyUSB0 或 COM1",
            },
            "command": {
                "type": "string",
                "description": "要发送的命令内容",
            },
            "add_line_ending": {
                "type": "boolean",
                "description": "是否自动添加换行符",
                "default": True,
            },
        },
        "required": ["session_id", "command"],
    },
}

READ_OUTPUT_TOOL: dict[str, Any] = {
    "name": "read_output",
    "description": "读取终端输出缓冲区的内容",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "会话ID（即串口路径），如 /dev/ttyUSB0 或 COM1",
            },
            "clear": {
                "type": "boolean",
                "description": "读取后是否清空缓冲区",
                "default": True,
            },
        },
        "required": ["session_id"],
    },
}

LIST_SESSIONS_TOOL: dict[str, Any] = {
    "name": "list_sessions",
    "description": "列出所有活动的终端会话",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GET_SESSION_INFO_TOOL: dict[str, Any] = {
    "name": "get_session_info",
    "description": "获取指定终端会话的详细信息",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "会话ID（即串口路径），如 /dev/ttyUSB0 或 COM1",
            },
        },
        "required": ["session_id"],
    },
}

CLEAR_BUFFER_TOOL: dict[str, Any] = {
    "name": "clear_buffer",
    "description": "清空指定终端会话的输出缓冲区",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "会话ID（即串口路径），如 /dev/ttyUSB0 或 COM1",
            },
        },
        "required": ["session_id"],
    },
}

"""终端会话管理模块

提供终端会话的创建、管理和数据收发功能。
支持多会话并发，每个会话独立缓冲。
"""

import logging
import threading
import time
from collections import deque
from typing import Any

from .errors import (
    InvalidLineEndingError,
    PortNotOpenError,
    SendCommandFailedError,
    SessionClosedError,
    SessionExistsError,
    SessionNotFoundError,
)
from .serial_manager import get_serial_manager
from .types import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_LINE_ENDING,
    DEFAULT_LOCAL_ECHO,
    LineEnding,
    SessionInfo,
    TerminalConfig,
)

logger = logging.getLogger(__name__)

# 后台读取间隔（秒）
READ_INTERVAL = 0.05  # 50ms


class TerminalSession:
    """终端会话

    管理单个串口的终端会话，包括输出缓冲区和后台读取线程。

    Attributes:
        session_id: 会话ID（即串口路径）
        port: 串口路径
        config: 终端配置
        created_at: 创建时间戳
    """

    def __init__(
        self,
        port: str,
        line_ending: LineEnding = DEFAULT_LINE_ENDING,
        local_echo: bool = DEFAULT_LOCAL_ECHO,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
    ) -> None:
        """初始化终端会话

        Args:
            port: 串口路径
            line_ending: 换行符类型
            local_echo: 是否本地回显
            buffer_size: 输出缓冲区大小
        """
        self.session_id = port
        self.port = port
        self.config = TerminalConfig(
            line_ending=line_ending,
            local_echo=local_echo,
            buffer_size=buffer_size,
        )
        self.created_at = time.time()

        # 输出缓冲区（使用 deque 实现环形缓冲）
        self._buffer: deque[bytes] = deque()
        self._buffer_size = 0
        self._max_buffer_size = buffer_size
        self._buffer_lock = threading.Lock()

        # 后台读取线程控制
        self._running = False
        self._read_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_active(self) -> bool:
        """会话是否活跃"""
        return self._running

    @property
    def buffer_length(self) -> int:
        """当前缓冲区数据量（字节）"""
        with self._buffer_lock:
            return self._buffer_size

    def start(self) -> None:
        """启动后台读取线程"""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._read_thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name=f"terminal-read-{self.port}",
        )
        self._read_thread.start()
        logger.info("终端会话启动：%s", self.session_id)

    def stop(self) -> None:
        """停止后台读取线程"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2.0)

        logger.info("终端会话停止：%s", self.session_id)

    def _read_loop(self) -> None:
        """后台读取循环"""
        manager = get_serial_manager()

        while not self._stop_event.is_set():
            try:
                # 从串口读取数据
                data = manager.read_data(self.port, timeout_ms=50)
                if data:
                    self._append_to_buffer(data)
            except Exception as e:
                # 串口可能已关闭或出错，停止读取
                if self._running:
                    logger.warning("终端读取异常：%s - %s", self.session_id, e)
                    self._running = False
                break

            # 短暂休眠，避免 CPU 占用过高
            self._stop_event.wait(READ_INTERVAL)

    def _append_to_buffer(self, data: bytes) -> None:
        """向缓冲区追加数据

        如果缓冲区满，自动丢弃最旧的数据。

        Args:
            data: 要追加的数据
        """
        with self._buffer_lock:
            self._buffer.append(data)
            self._buffer_size += len(data)

            # 如果超出限制，丢弃旧数据
            while self._buffer_size > self._max_buffer_size and self._buffer:
                old_data = self._buffer.popleft()
                self._buffer_size -= len(old_data)

    def read_output(self, clear: bool = True) -> bytes:
        """读取输出缓冲区内容

        Args:
            clear: 是否清空缓冲区

        Returns:
            缓冲区中的数据
        """
        with self._buffer_lock:
            if not self._buffer:
                return b""

            # 合并所有数据块
            result = b"".join(self._buffer)

            if clear:
                self._buffer.clear()
                self._buffer_size = 0

            return result

    def clear_buffer(self) -> None:
        """清空输出缓冲区"""
        with self._buffer_lock:
            self._buffer.clear()
            self._buffer_size = 0

    def send_command(self, command: str, add_line_ending: bool = True) -> int:
        """发送命令

        Args:
            command: 要发送的命令
            add_line_ending: 是否自动添加换行符

        Returns:
            发送的字节数

        Raises:
            SendCommandFailedError: 发送失败
        """
        manager = get_serial_manager()

        # 准备数据
        data = command
        if add_line_ending:
            data += self.config.line_ending.value

        raw_data = data.encode("utf-8")

        try:
            bytes_written = manager.send_data(self.port, raw_data)

            # 本地回显
            if self.config.local_echo:
                self._append_to_buffer(raw_data)

            logger.debug("终端发送命令：%s - %d 字节", self.session_id, bytes_written)
            return bytes_written
        except Exception as e:
            raise SendCommandFailedError(self.session_id, str(e)) from e

    def get_info(self) -> SessionInfo:
        """获取会话信息

        Returns:
            会话信息
        """
        return SessionInfo(
            session_id=self.session_id,
            port=self.port,
            config=self.config,
            buffer_size=self.buffer_length,
            is_active=self.is_active,
            created_at=self.created_at,
        )


class TerminalManager:
    """终端管理器

    管理所有终端会话，提供会话的创建、关闭和查询功能。
    使用单例模式，确保全局只有一个管理器实例。

    Attributes:
        _sessions: 会话字典，键为会话ID（串口路径）
        _lock: 线程锁
    """

    def __init__(self) -> None:
        """初始化终端管理器"""
        self._sessions: dict[str, TerminalSession] = {}
        self._lock = threading.RLock()

    def create_session(
        self,
        port: str,
        line_ending: str = DEFAULT_LINE_ENDING.name,
        local_echo: bool = DEFAULT_LOCAL_ECHO,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
    ) -> SessionInfo:
        """创建终端会话

        Args:
            port: 串口路径
            line_ending: 换行符类型（CR/LF/CRLF）
            local_echo: 是否本地回显
            buffer_size: 输出缓冲区大小

        Returns:
            会话信息

        Raises:
            SessionExistsError: 会话已存在
            PortNotOpenError: 串口未打开
            InvalidLineEndingError: 无效的换行符配置
        """
        # 验证换行符配置
        try:
            line_ending_enum = LineEnding[line_ending.upper()]
        except KeyError:
            raise InvalidLineEndingError(line_ending)

        # 检查串口是否已打开
        manager = get_serial_manager()
        try:
            manager.get_status(port)
        except Exception:
            raise PortNotOpenError(port)

        with self._lock:
            # 检查会话是否已存在
            if port in self._sessions:
                raise SessionExistsError(port)

            # 创建会话
            session = TerminalSession(
                port=port,
                line_ending=line_ending_enum,
                local_echo=local_echo,
                buffer_size=buffer_size,
            )
            session.start()
            self._sessions[port] = session

            logger.info("创建终端会话：%s", port)
            return session.get_info()

    def close_session(self, session_id: str) -> dict[str, Any]:
        """关闭终端会话

        Args:
            session_id: 会话ID（串口路径）

        Returns:
            操作结果

        Raises:
            SessionNotFoundError: 会话不存在
        """
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFoundError(session_id)

            session = self._sessions.pop(session_id)
            session.stop()

            logger.info("关闭终端会话：%s", session_id)
            return {"success": True, "session_id": session_id}

    def get_session(self, session_id: str) -> TerminalSession:
        """获取终端会话

        Args:
            session_id: 会话ID（串口路径）

        Returns:
            终端会话

        Raises:
            SessionNotFoundError: 会话不存在
        """
        with self._lock:
            if session_id not in self._sessions:
                raise SessionNotFoundError(session_id)
            return self._sessions[session_id]

    def send_command(
        self, session_id: str, command: str, add_line_ending: bool = True
    ) -> dict[str, Any]:
        """向终端发送命令

        Args:
            session_id: 会话ID（串口路径）
            command: 要发送的命令
            add_line_ending: 是否自动添加换行符

        Returns:
            发送结果

        Raises:
            SessionNotFoundError: 会话不存在
            SessionClosedError: 会话已关闭
            SendCommandFailedError: 发送失败
        """
        session = self.get_session(session_id)

        if not session.is_active:
            raise SessionClosedError(session_id)

        bytes_written = session.send_command(command, add_line_ending)
        return {"success": True, "bytes_written": bytes_written}

    def read_output(self, session_id: str, clear: bool = True) -> dict[str, Any]:
        """读取终端输出

        Args:
            session_id: 会话ID（串口路径）
            clear: 是否清空缓冲区

        Returns:
            输出内容

        Raises:
            SessionNotFoundError: 会话不存在
        """
        session = self.get_session(session_id)
        data = session.read_output(clear)

        # 解码为字符串，替换不可解码的字符
        text = data.decode("utf-8", errors="replace")

        return {
            "data": text,
            "bytes_read": len(data),
        }

    def clear_buffer(self, session_id: str) -> dict[str, Any]:
        """清空终端缓冲区

        Args:
            session_id: 会话ID（串口路径）

        Returns:
            操作结果

        Raises:
            SessionNotFoundError: 会话不存在
        """
        session = self.get_session(session_id)
        session.clear_buffer()
        return {"success": True, "session_id": session_id}

    def list_sessions(self) -> list[dict[str, Any]]:
        """列出所有终端会话

        Returns:
            会话信息列表
        """
        with self._lock:
            return [session.get_info().to_dict() for session in self._sessions.values()]

    def get_session_info(self, session_id: str) -> dict[str, Any]:
        """获取会话详细信息

        Args:
            session_id: 会话ID（串口路径）

        Returns:
            会话信息

        Raises:
            SessionNotFoundError: 会话不存在
        """
        session = self.get_session(session_id)
        return session.get_info().to_dict()

    def shutdown(self) -> None:
        """关闭管理器

        停止所有会话。
        """
        with self._lock:
            for session_id, session in list(self._sessions.items()):
                try:
                    session.stop()
                    logger.debug("关闭终端会话：%s", session_id)
                except Exception as e:
                    logger.warning("关闭终端会话失败：%s - %s", session_id, e)
            self._sessions.clear()

        logger.info("终端管理器已关闭")


# 全局终端管理器实例
_terminal_manager: TerminalManager | None = None


def get_terminal_manager() -> TerminalManager:
    """获取终端管理器单例

    Returns:
        终端管理器实例
    """
    global _terminal_manager
    if _terminal_manager is None:
        _terminal_manager = TerminalManager()
    return _terminal_manager

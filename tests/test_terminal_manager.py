"""终端管理器测试"""

from unittest.mock import MagicMock, patch

import pytest

from uart_mcp.errors import (
    InvalidLineEndingError,
    PortNotOpenError,
    SessionExistsError,
    SessionNotFoundError,
)
from uart_mcp.terminal_manager import TerminalManager, TerminalSession
from uart_mcp.types import LineEnding


class TestTerminalSession:
    """测试 TerminalSession 类"""

    def test_session_init(self):
        """测试会话初始化"""
        session = TerminalSession(
            port="/dev/ttyUSB0",
            line_ending=LineEnding.CRLF,
            local_echo=False,
            buffer_size=65536,
        )

        assert session.session_id == "/dev/ttyUSB0"
        assert session.port == "/dev/ttyUSB0"
        assert session.config.line_ending == LineEnding.CRLF
        assert session.config.local_echo is False
        assert session.config.buffer_size == 65536
        assert session.is_active is False

    def test_session_buffer_operations(self):
        """测试缓冲区操作"""
        session = TerminalSession(port="/dev/ttyUSB0")

        # 手动添加数据到缓冲区
        session._append_to_buffer(b"hello")
        session._append_to_buffer(b" world")

        assert session.buffer_length == 11

        # 读取数据（清空）
        data = session.read_output(clear=True)
        assert data == b"hello world"
        assert session.buffer_length == 0

    def test_session_buffer_overflow(self):
        """测试缓冲区溢出处理"""
        # 创建小缓冲区
        session = TerminalSession(port="/dev/ttyUSB0", buffer_size=10)

        # 添加超出缓冲区的数据
        session._append_to_buffer(b"12345")
        session._append_to_buffer(b"67890")
        session._append_to_buffer(b"ABCDE")

        # 缓冲区应该丢弃旧数据
        assert session.buffer_length <= 10

    def test_session_clear_buffer(self):
        """测试清空缓冲区"""
        session = TerminalSession(port="/dev/ttyUSB0")

        session._append_to_buffer(b"test data")
        session.clear_buffer()

        assert session.buffer_length == 0
        assert session.read_output() == b""

    def test_session_get_info(self):
        """测试获取会话信息"""
        session = TerminalSession(port="/dev/ttyUSB0")
        session._append_to_buffer(b"test")

        info = session.get_info()

        assert info.session_id == "/dev/ttyUSB0"
        assert info.port == "/dev/ttyUSB0"
        assert info.buffer_size == 4
        assert info.is_active is False

    def test_session_send_command_with_line_ending(self):
        """测试发送命令（带换行符）"""
        session = TerminalSession(
            port="/dev/ttyUSB0",
            line_ending=LineEnding.CRLF,
            local_echo=True,
        )

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_mgr:
            mock_mgr.return_value.send_data.return_value = 7

            bytes_written = session.send_command("test", add_line_ending=True)

            assert bytes_written == 7
            # 验证发送的数据包含换行符
            mock_mgr.return_value.send_data.assert_called_once_with(
                "/dev/ttyUSB0", b"test\r\n"
            )

            # 验证本地回显
            assert session.buffer_length == 6  # "test\r\n"

    def test_session_send_command_without_line_ending(self):
        """测试发送命令（不带换行符）"""
        session = TerminalSession(port="/dev/ttyUSB0")

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_mgr:
            mock_mgr.return_value.send_data.return_value = 4

            bytes_written = session.send_command("test", add_line_ending=False)

            assert bytes_written == 4
            mock_mgr.return_value.send_data.assert_called_once_with(
                "/dev/ttyUSB0", b"test"
            )


class TestTerminalManager:
    """测试 TerminalManager 类"""

    def test_create_session_success(self):
        """测试成功创建会话"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            # 模拟 read_data 抛出异常，让后台线程退出
            mock_serial_mgr.return_value.read_data.side_effect = Exception("测试")

            info = manager.create_session(
                port="/dev/ttyUSB0",
                line_ending="CRLF",
            )

            assert info.session_id == "/dev/ttyUSB0"
            assert info.port == "/dev/ttyUSB0"
            assert info.config.line_ending.name == "CRLF"

        manager.shutdown()

    def test_create_session_already_exists(self):
        """测试创建已存在的会话"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("测试")

            manager.create_session(port="/dev/ttyUSB0")

            with pytest.raises(SessionExistsError):
                manager.create_session(port="/dev/ttyUSB0")

        manager.shutdown()

    def test_create_session_port_not_open(self):
        """测试在未打开的串口上创建会话"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.side_effect = Exception("未打开")

            with pytest.raises(PortNotOpenError):
                manager.create_session(port="/dev/ttyUSB0")

        manager.shutdown()

    def test_create_session_invalid_line_ending(self):
        """测试无效的换行符配置"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()

            with pytest.raises(InvalidLineEndingError):
                manager.create_session(port="/dev/ttyUSB0", line_ending="INVALID")

        manager.shutdown()

    def test_close_session_success(self):
        """测试成功关闭会话"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("测试")

            manager.create_session(port="/dev/ttyUSB0")
            result = manager.close_session("/dev/ttyUSB0")

            assert result["success"] is True
            assert result["session_id"] == "/dev/ttyUSB0"

        manager.shutdown()

    def test_close_session_not_found(self):
        """测试关闭不存在的会话"""
        manager = TerminalManager()

        with pytest.raises(SessionNotFoundError):
            manager.close_session("/dev/ttyUSB0")

        manager.shutdown()

    def test_send_command_success(self):
        """测试成功发送命令"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            # 让 read_data 返回空数据，避免后台线程退出
            mock_serial_mgr.return_value.read_data.return_value = b""
            mock_serial_mgr.return_value.send_data.return_value = 7

            manager.create_session(port="/dev/ttyUSB0")
            result = manager.send_command("/dev/ttyUSB0", "test")

            assert result["success"] is True
            assert result["bytes_written"] == 7

        manager.shutdown()

    def test_send_command_session_not_found(self):
        """测试向不存在的会话发送命令"""
        manager = TerminalManager()

        with pytest.raises(SessionNotFoundError):
            manager.send_command("/dev/ttyUSB0", "test")

        manager.shutdown()

    def test_read_output_success(self):
        """测试成功读取输出"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("测试")

            manager.create_session(port="/dev/ttyUSB0")

            # 手动向缓冲区添加数据
            session = manager.get_session("/dev/ttyUSB0")
            session._append_to_buffer(b"test output")

            result = manager.read_output("/dev/ttyUSB0")

            assert result["data"] == "test output"
            assert result["bytes_read"] == 11

        manager.shutdown()

    def test_clear_buffer_success(self):
        """测试成功清空缓冲区"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("测试")

            manager.create_session(port="/dev/ttyUSB0")

            session = manager.get_session("/dev/ttyUSB0")
            session._append_to_buffer(b"test data")

            result = manager.clear_buffer("/dev/ttyUSB0")

            assert result["success"] is True
            assert session.buffer_length == 0

        manager.shutdown()

    def test_list_sessions(self):
        """测试列出所有会话"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("测试")

            manager.create_session(port="/dev/ttyUSB0")
            manager.create_session(port="/dev/ttyUSB1")

            sessions = manager.list_sessions()

            assert len(sessions) == 2
            session_ids = [s["session_id"] for s in sessions]
            assert "/dev/ttyUSB0" in session_ids
            assert "/dev/ttyUSB1" in session_ids

        manager.shutdown()

    def test_get_session_info_success(self):
        """测试获取会话信息"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("测试")

            manager.create_session(port="/dev/ttyUSB0")
            info = manager.get_session_info("/dev/ttyUSB0")

            assert info["session_id"] == "/dev/ttyUSB0"
            assert info["port"] == "/dev/ttyUSB0"

        manager.shutdown()

    def test_get_session_info_not_found(self):
        """测试获取不存在的会话信息"""
        manager = TerminalManager()

        with pytest.raises(SessionNotFoundError):
            manager.get_session_info("/dev/ttyUSB0")

        manager.shutdown()

    def test_shutdown(self):
        """测试关闭管理器"""
        manager = TerminalManager()

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_serial_mgr:
            mock_serial_mgr.return_value.get_status.return_value = MagicMock()
            mock_serial_mgr.return_value.read_data.side_effect = Exception("测试")

            manager.create_session(port="/dev/ttyUSB0")
            manager.create_session(port="/dev/ttyUSB1")

            manager.shutdown()

            assert len(manager._sessions) == 0


class TestLineEndingConfigurations:
    """测试不同换行符配置"""

    @pytest.mark.parametrize(
        "line_ending,expected_suffix",
        [
            ("CR", b"\r"),
            ("LF", b"\n"),
            ("CRLF", b"\r\n"),
        ],
    )
    def test_different_line_endings(self, line_ending, expected_suffix):
        """测试不同换行符"""
        session = TerminalSession(
            port="/dev/ttyUSB0",
            line_ending=LineEnding[line_ending],
        )

        with patch("uart_mcp.terminal_manager.get_serial_manager") as mock_mgr:
            mock_mgr.return_value.send_data.return_value = len(b"cmd" + expected_suffix)

            session.send_command("cmd", add_line_ending=True)

            mock_mgr.return_value.send_data.assert_called_once_with(
                "/dev/ttyUSB0", b"cmd" + expected_suffix
            )

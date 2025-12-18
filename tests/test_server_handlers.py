"""server.py 的 handler 函数测试

覆盖 handle_list_tools 和 handle_call_tool 函数。
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHandleListTools:
    """测试 handle_list_tools 函数"""

    @pytest.mark.asyncio
    async def test_handle_list_tools_returns_all_tools(self):
        """测试：handle_list_tools 返回所有工具"""
        from uart_mcp.server import handle_list_tools

        tools = await handle_list_tools()

        # 验证返回工具列表
        assert isinstance(tools, list)
        assert len(tools) == 14  # 总共14个工具

        # 验证每个工具都有必要的属性
        tool_names = [tool.name for tool in tools]

        # 串口基础工具
        assert "list_ports" in tool_names
        assert "open_port" in tool_names
        assert "close_port" in tool_names
        assert "set_config" in tool_names
        assert "get_status" in tool_names

        # 数据操作工具
        assert "send_data" in tool_names
        assert "read_data" in tool_names

        # 终端会话工具
        assert "create_session" in tool_names
        assert "close_session" in tool_names
        assert "send_command" in tool_names
        assert "read_output" in tool_names
        assert "list_sessions" in tool_names
        assert "get_session_info" in tool_names
        assert "clear_buffer" in tool_names


class TestHandleCallTool:
    """测试 handle_call_tool 函数"""

    @pytest.mark.asyncio
    async def test_call_list_ports(self, mock_list_ports_with_devices, reset_managers):
        """测试：调用 list_ports 工具"""
        from uart_mcp.server import handle_call_tool

        result = await handle_call_tool("list_ports", {})

        assert len(result) == 1
        assert result[0].type == "text"

        data = json.loads(result[0].text)
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_call_open_port(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 open_port 工具"""
        from uart_mcp.server import handle_call_tool

        result = await handle_call_tool("open_port", {
            "port": "/dev/ttyMOCK0",
            "baudrate": 115200
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("is_open") is True

    @pytest.mark.asyncio
    async def test_call_get_status(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 get_status 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await handle_call_tool("get_status", {"port": "/dev/ttyMOCK0"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("is_open") is True

    @pytest.mark.asyncio
    async def test_call_set_config(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 set_config 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await handle_call_tool("set_config", {
            "port": "/dev/ttyMOCK0",
            "baudrate": 9600
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("config", {}).get("baudrate") == 9600

    @pytest.mark.asyncio
    async def test_call_send_data(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 send_data 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await handle_call_tool("send_data", {
            "port": "/dev/ttyMOCK0",
            "data": "Hello",
            "is_binary": False
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("success") is True

    @pytest.mark.asyncio
    async def test_call_read_data(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 read_data 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口并发送数据
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await handle_call_tool("send_data", {"port": "/dev/ttyMOCK0", "data": "Test", "is_binary": False})

        result = await handle_call_tool("read_data", {
            "port": "/dev/ttyMOCK0",
            "is_binary": False
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "Test" in data.get("data", "")

    @pytest.mark.asyncio
    async def test_call_close_port(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 close_port 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await handle_call_tool("close_port", {"port": "/dev/ttyMOCK0"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("success") is True

    # ========== 终端会话工具测试 ==========

    @pytest.mark.asyncio
    async def test_call_create_session(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 create_session 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})

        result = await handle_call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("session_id") == "/dev/ttyMOCK0"

    @pytest.mark.asyncio
    async def test_call_list_sessions(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 list_sessions 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口并创建会话
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await handle_call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await handle_call_tool("list_sessions", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "sessions" in data

    @pytest.mark.asyncio
    async def test_call_get_session_info(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 get_session_info 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口并创建会话
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await handle_call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await handle_call_tool("get_session_info", {"session_id": "/dev/ttyMOCK0"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("session_id") == "/dev/ttyMOCK0"

    @pytest.mark.asyncio
    async def test_call_send_command(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 send_command 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口并创建会话
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await handle_call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await handle_call_tool("send_command", {
            "session_id": "/dev/ttyMOCK0",
            "command": "AT"
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("success") is True

    @pytest.mark.asyncio
    async def test_call_read_output(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 read_output 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口并创建会话
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await handle_call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await handle_call_tool("read_output", {"session_id": "/dev/ttyMOCK0"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "data" in data

    @pytest.mark.asyncio
    async def test_call_clear_buffer(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 clear_buffer 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口并创建会话
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await handle_call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await handle_call_tool("clear_buffer", {"session_id": "/dev/ttyMOCK0"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("success") is True

    @pytest.mark.asyncio
    async def test_call_close_session(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：调用 close_session 工具"""
        from uart_mcp.server import handle_call_tool

        # 先打开串口并创建会话
        await handle_call_tool("open_port", {"port": "/dev/ttyMOCK0", "baudrate": 115200})
        await handle_call_tool("create_session", {"port": "/dev/ttyMOCK0"})

        result = await handle_call_tool("close_session", {"session_id": "/dev/ttyMOCK0"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data.get("success") is True

    # ========== 错误处理测试 ==========

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, reset_managers):
        """测试：调用未知工具返回错误"""
        from uart_mcp.server import handle_call_tool

        result = await handle_call_tool("unknown_tool", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "error" in data
        assert "未知工具" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_serial_error_handling(self, reset_managers):
        """测试：SerialError 异常处理"""
        from uart_mcp.server import handle_call_tool

        # 尝试获取未打开端口的状态，应该触发 SerialError
        result = await handle_call_tool("get_status", {"port": "/dev/ttyNONEXIST"})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "error" in data
        assert "code" in data["error"]

    @pytest.mark.asyncio
    async def test_general_exception_handling(self, reset_managers):
        """测试：普通异常处理"""
        from uart_mcp.server import handle_call_tool

        # 使用 patch 正确的模块路径来触发普通异常
        with patch("uart_mcp.server.list_ports", side_effect=RuntimeError("测试异常")):
            result = await handle_call_tool("list_ports", {})

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "error" in data
        assert "内部错误" in data["error"]["message"]


class TestMainAndRunServer:
    """测试 main() 和 run_server() 函数"""

    @pytest.mark.asyncio
    async def test_run_server_starts_correctly(self):
        """测试：run_server 启动并立即退出"""
        from uart_mcp.server import run_server

        # Mock stdio_server 上下文管理器，让它立即返回
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()

        async def mock_aenter(self):
            return (mock_read_stream, mock_write_stream)

        async def mock_aexit(self, *args):
            pass

        mock_context = MagicMock()
        mock_context.__aenter__ = mock_aenter
        mock_context.__aexit__ = mock_aexit

        with patch(
            "uart_mcp.server.mcp.server.stdio.stdio_server",
            return_value=mock_context
        ):
            with patch(
                "uart_mcp.server.server.run",
                new_callable=AsyncMock
            ) as mock_run:
                await run_server()
                mock_run.assert_called_once()

    def test_main_normal_exit(self):
        """测试：main 正常启动和退出"""
        from uart_mcp.server import main

        def mock_asyncio_run_impl(coro):
            # 关闭协程以避免警告
            coro.close()

        with patch(
            "uart_mcp.server.asyncio.run",
            side_effect=mock_asyncio_run_impl
        ) as mock_asyncio_run:
            with patch("uart_mcp.server.get_terminal_manager") as mock_term_mgr:
                with patch("uart_mcp.server.get_serial_manager") as mock_serial_mgr:
                    mock_term_instance = MagicMock()
                    mock_serial_instance = MagicMock()
                    mock_term_mgr.return_value = mock_term_instance
                    mock_serial_mgr.return_value = mock_serial_instance

                    main()

                    mock_asyncio_run.assert_called_once()
                    mock_term_instance.shutdown.assert_called_once()
                    mock_serial_instance.shutdown.assert_called_once()

    def test_main_keyboard_interrupt(self):
        """测试：main 处理 KeyboardInterrupt"""
        from uart_mcp.server import main

        def mock_asyncio_run_impl(coro):
            # 关闭协程以避免警告
            coro.close()
            raise KeyboardInterrupt

        with patch("uart_mcp.server.asyncio.run", side_effect=mock_asyncio_run_impl):
            with patch("uart_mcp.server.get_terminal_manager") as mock_term_mgr:
                with patch("uart_mcp.server.get_serial_manager") as mock_serial_mgr:
                    mock_term_instance = MagicMock()
                    mock_serial_instance = MagicMock()
                    mock_term_mgr.return_value = mock_term_instance
                    mock_serial_mgr.return_value = mock_serial_instance

                    # 不应该抛出异常
                    main()

                    # 确保清理仍然执行
                    mock_term_instance.shutdown.assert_called_once()
                    mock_serial_instance.shutdown.assert_called_once()


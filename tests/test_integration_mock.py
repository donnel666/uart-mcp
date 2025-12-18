"""基于Mock的集成测试脚本

本测试脚本模拟串口回环效果，无需真实硬件即可测试所有MCP工具功能。
适用于CICD环境的自动化测试。

运行方式:
    pytest tests/test_integration_mock.py -v
"""

import base64
import time

import pytest

# 测试配置
MOCK_PORT = "/dev/ttyMOCK0"
MOCK_BAUDRATE = 115200


class TestMockIntegration:
    """基于Mock的集成测试类"""

    # ========== 阶段1：串口基础操作测试 ==========

    def test_list_ports(self, mock_list_ports_with_devices, reset_managers):
        """测试：列出所有可用串口"""
        from uart_mcp.tools.list_ports import list_ports

        ports = list_ports()

        assert len(ports) == 2
        port_names = [p["port"] for p in ports]
        assert MOCK_PORT in port_names
        assert "/dev/ttyMOCK1" in port_names

    def test_open_port(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：打开串口"""
        from uart_mcp.tools.port_ops import open_port

        result = open_port(
            port=MOCK_PORT,
            baudrate=MOCK_BAUDRATE,
            bytesize=8,
            parity="N",
            stopbits=1.0,
        )

        assert result.get("is_open") is True
        assert result.get("port") == MOCK_PORT

    def test_get_status(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：获取串口状态"""
        from uart_mcp.tools.port_ops import get_status, open_port

        # 先打开串口
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        result = get_status(port=MOCK_PORT)

        assert result.get("is_open") is True
        config = result.get("config", {})
        assert config.get("baudrate") == MOCK_BAUDRATE

    def test_set_config(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：修改串口配置（热更新）"""
        from uart_mcp.tools.port_ops import get_status, open_port, set_config

        # 先打开串口
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        # 修改波特率
        new_baudrate = 9600
        result = set_config(port=MOCK_PORT, baudrate=new_baudrate)

        config = result.get("config", {})
        assert config.get("baudrate") == new_baudrate

        # 验证配置已更新
        status = get_status(port=MOCK_PORT)
        assert status.get("config", {}).get("baudrate") == new_baudrate

    def test_close_port(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：关闭串口"""
        from uart_mcp.tools.port_ops import close_port, open_port

        # 先打开串口
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        result = close_port(port=MOCK_PORT)

        assert result.get("success") is True

    # ========== 阶段2：数据通信测试（回环） ==========

    def test_send_receive_text(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：发送和接收文本数据（回环测试）"""
        from uart_mcp.tools.data_ops import read_data, send_data
        from uart_mcp.tools.port_ops import open_port

        # 打开串口
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        test_message = "Hello UART 你好串口!"

        # 发送数据
        send_result = send_data(port=MOCK_PORT, data=test_message, is_binary=False)
        assert send_result.get("success") is True

        # 读取数据（回环）
        read_result = read_data(port=MOCK_PORT, is_binary=False)
        received = read_result.get("data", "")

        assert test_message in received

    def test_send_receive_binary(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：发送和接收二进制数据（回环测试）"""
        from uart_mcp.tools.data_ops import read_data, send_data
        from uart_mcp.tools.port_ops import open_port

        # 打开串口
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        # 准备二进制数据
        raw_data = bytes([0x01, 0x02, 0x03, 0xFE, 0xFF])
        b64_data = base64.b64encode(raw_data).decode("ascii")

        # 发送二进制数据
        send_result = send_data(port=MOCK_PORT, data=b64_data, is_binary=True)
        assert send_result.get("success") is True

        # 读取二进制数据（回环）
        read_result = read_data(port=MOCK_PORT, is_binary=True)
        received_b64 = read_result.get("data", "")
        received_raw = base64.b64decode(received_b64) if received_b64 else b""

        assert raw_data == received_raw

    # ========== 阶段3：终端会话测试 ==========

    def test_create_session(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：创建终端会话"""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import create_session

        # 先打开串口
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        result = create_session(
            port=MOCK_PORT,
            line_ending="CRLF",
            local_echo=False,
        )

        assert result.get("session_id") == MOCK_PORT

    def test_list_sessions(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：列出所有会话"""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import create_session, list_sessions

        # 打开串口并创建会话
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        result = list_sessions()
        sessions = result.get("sessions", [])

        session_ids = [s.get("session_id") if isinstance(s, dict) else s for s in sessions]
        assert MOCK_PORT in session_ids

    def test_get_session_info(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：获取会话信息"""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import create_session, get_session_info

        # 打开串口并创建会话
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        result = get_session_info(session_id=MOCK_PORT)

        assert result.get("session_id") == MOCK_PORT

    def test_send_command_read_output(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：发送命令并读取输出（回环测试）"""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import (
            clear_buffer,
            create_session,
            read_output,
            send_command,
        )

        # 打开串口并创建会话
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        # 清空缓冲区
        clear_buffer(session_id=MOCK_PORT)

        test_cmd = "AT"

        # 发送命令
        send_result = send_command(
            session_id=MOCK_PORT,
            command=test_cmd,
            add_line_ending=True,
        )
        assert send_result.get("success") is True

        # 等待后台线程读取数据
        time.sleep(0.2)

        # 读取输出（回环模式下应该收到发送的命令）
        read_result = read_output(session_id=MOCK_PORT, clear=False)
        output = read_result.get("data", "")

        assert test_cmd in output

    def test_clear_buffer(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：清空缓冲区"""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import clear_buffer, create_session, read_output

        # 打开串口并创建会话
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        result = clear_buffer(session_id=MOCK_PORT)
        assert result.get("success") is True

        # 验证缓冲区已清空
        read_result = read_output(session_id=MOCK_PORT, clear=False)
        assert len(read_result.get("data", "")) == 0

    def test_close_session(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：关闭终端会话"""
        from uart_mcp.tools.port_ops import open_port
        from uart_mcp.tools.terminal import close_session, create_session

        # 打开串口并创建会话
        open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        create_session(port=MOCK_PORT)

        result = close_session(session_id=MOCK_PORT)

        assert result.get("success") is True

    # ========== 阶段4：错误处理测试 ==========

    def test_open_nonexistent_port(self, mock_list_ports_with_devices, reset_managers):
        """测试：打开不存在的端口（端口不在列表中）"""
        from uart_mcp.errors import PortNotFoundError
        from uart_mcp.tools.port_ops import open_port

        # 不使用mock_serial_loopback，让它尝试打开真实（不存在）端口
        # 由于端口不存在于系统中，应该抛出异常
        with pytest.raises((PortNotFoundError, Exception)):
            open_port(port="/dev/ttyNONEXIST_CICD_TEST", baudrate=9600)

    def test_get_status_unopened_port(self, reset_managers):
        """测试：获取未打开端口的状态"""
        from uart_mcp.tools.port_ops import get_status

        with pytest.raises(Exception):
            get_status(port=MOCK_PORT)

    def test_send_data_unopened_port(self, reset_managers):
        """测试：向未打开的端口发送数据"""
        from uart_mcp.tools.data_ops import send_data

        with pytest.raises(Exception):
            send_data(port=MOCK_PORT, data="test", is_binary=False)


class TestMockIntegrationWorkflow:
    """完整工作流程测试"""

    def test_full_workflow(self, mock_serial_loopback, mock_list_ports_with_devices, reset_managers):
        """测试：完整的串口通信工作流程"""
        from uart_mcp.tools.data_ops import read_data, send_data
        from uart_mcp.tools.port_ops import (
            close_port,
            get_status,
            open_port,
            set_config,
        )
        from uart_mcp.tools.terminal import (
            clear_buffer,
            close_session,
            create_session,
            get_session_info,
            list_sessions,
            read_output,
            send_command,
        )

        # 1. 打开串口
        result = open_port(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)
        assert result.get("is_open") is True

        # 2. 获取状态
        status = get_status(port=MOCK_PORT)
        assert status.get("is_open") is True

        # 3. 修改配置
        new_config = set_config(port=MOCK_PORT, baudrate=9600)
        assert new_config.get("config", {}).get("baudrate") == 9600

        # 恢复配置
        set_config(port=MOCK_PORT, baudrate=MOCK_BAUDRATE)

        # 4. 发送/接收文本
        send_data(port=MOCK_PORT, data="Hello", is_binary=False)
        read_result = read_data(port=MOCK_PORT, is_binary=False)
        assert "Hello" in read_result.get("data", "")

        # 5. 发送/接收二进制
        raw = bytes([0xAA, 0xBB])
        send_data(port=MOCK_PORT, data=base64.b64encode(raw).decode(), is_binary=True)
        read_result = read_data(port=MOCK_PORT, is_binary=True)
        assert base64.b64decode(read_result.get("data", "")) == raw

        # 6. 创建终端会话
        session = create_session(port=MOCK_PORT)
        assert session.get("session_id") == MOCK_PORT

        # 7. 列出会话
        sessions = list_sessions()
        assert len(sessions.get("sessions", [])) > 0

        # 8. 获取会话信息
        info = get_session_info(session_id=MOCK_PORT)
        assert info.get("session_id") == MOCK_PORT

        # 9. 发送命令
        clear_buffer(session_id=MOCK_PORT)
        send_command(session_id=MOCK_PORT, command="TEST")
        time.sleep(0.2)
        output = read_output(session_id=MOCK_PORT)
        assert "TEST" in output.get("data", "")

        # 10. 清空缓冲区
        clear_buffer(session_id=MOCK_PORT)
        output = read_output(session_id=MOCK_PORT)
        assert output.get("data", "") == ""

        # 11. 关闭会话
        close_session(session_id=MOCK_PORT)

        # 12. 关闭串口
        result = close_port(port=MOCK_PORT)
        assert result.get("success") is True

"""MCP 工具测试"""

from unittest.mock import patch

from uart_mcp.tools.list_ports import list_ports
from uart_mcp.tools.port_ops import close_port, get_status, open_port, set_config
from uart_mcp.types import PortInfo, PortStatus, SerialConfig


class TestListPortsTool:
    """测试 list_ports 工具"""

    def test_list_ports_returns_list(self):
        """测试返回列表格式"""
        with patch("uart_mcp.tools.list_ports.get_serial_manager") as mock_manager:
            mock_manager.return_value.list_ports.return_value = [
                PortInfo(
                    port="/dev/ttyUSB0", description="USB Serial", hwid="1234:5678"
                )
            ]

            result = list_ports()

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["port"] == "/dev/ttyUSB0"

    def test_list_ports_empty(self):
        """测试空列表"""
        with patch("uart_mcp.tools.list_ports.get_serial_manager") as mock_manager:
            mock_manager.return_value.list_ports.return_value = []

            result = list_ports()

            assert result == []


class TestOpenPortTool:
    """测试 open_port 工具"""

    def test_open_port_default_config(self):
        """测试使用默认配置打开"""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            mock_status = PortStatus(
                port="/dev/ttyUSB0",
                is_open=True,
                config=SerialConfig(),
                connected=True,
            )
            mock_manager.return_value.open_port.return_value = mock_status

            result = open_port(port="/dev/ttyUSB0")

            assert result["is_open"] is True
            assert result["port"] == "/dev/ttyUSB0"

    def test_open_port_custom_config(self):
        """测试使用自定义配置打开"""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            config = SerialConfig(baudrate=115200)
            mock_status = PortStatus(
                port="/dev/ttyUSB0",
                is_open=True,
                config=config,
                connected=True,
            )
            mock_manager.return_value.open_port.return_value = mock_status

            open_port(port="/dev/ttyUSB0", baudrate=115200)

            mock_manager.return_value.open_port.assert_called_once()
            call_kwargs = mock_manager.return_value.open_port.call_args[1]
            assert call_kwargs["baudrate"] == 115200


class TestClosePortTool:
    """测试 close_port 工具"""

    def test_close_port_success(self):
        """测试成功关闭"""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            mock_manager.return_value.close_port.return_value = {
                "success": True,
                "port": "/dev/ttyUSB0",
            }

            result = close_port(port="/dev/ttyUSB0")

            assert result["success"] is True


class TestSetConfigTool:
    """测试 set_config 工具"""

    def test_set_config_partial(self):
        """测试部分更新配置"""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            config = SerialConfig(baudrate=115200)
            mock_status = PortStatus(
                port="/dev/ttyUSB0",
                is_open=True,
                config=config,
            )
            mock_manager.return_value.set_config.return_value = mock_status

            result = set_config(port="/dev/ttyUSB0", baudrate=115200)

            assert result["config"]["baudrate"] == 115200


class TestGetStatusTool:
    """测试 get_status 工具"""

    def test_get_status_success(self):
        """测试成功获取状态"""
        with patch("uart_mcp.tools.port_ops.get_serial_manager") as mock_manager:
            config = SerialConfig()
            mock_status = PortStatus(
                port="/dev/ttyUSB0",
                is_open=True,
                config=config,
                connected=True,
                reconnecting=False,
            )
            mock_manager.return_value.get_status.return_value = mock_status

            result = get_status(port="/dev/ttyUSB0")

            assert result["is_open"] is True
            assert result["connected"] is True
            assert result["reconnecting"] is False

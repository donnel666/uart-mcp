"""串口管理器测试"""

from unittest.mock import MagicMock, patch

import pytest

from uart_mcp.errors import (
    InvalidParamError,
    PortBlacklistedError,
    PortClosedError,
    WriteFailedError,
)
from uart_mcp.serial_manager import SerialManager


class TestSerialManagerListPorts:
    """测试 list_ports 功能"""

    def test_list_ports_empty(self, mock_list_ports):
        """测试无可用串口"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        ports = manager.list_ports()

        assert ports == []
        manager.shutdown()

    def test_list_ports_with_devices(self, mock_list_ports):
        """测试有可用串口"""
        mock_port = MagicMock()
        mock_port.device = "/dev/ttyUSB0"
        mock_port.description = "USB Serial"
        mock_port.hwid = "USB VID:PID=1234:5678"
        mock_list_ports.return_value = [mock_port]

        manager = SerialManager(enable_auto_reconnect=False)
        ports = manager.list_ports()

        assert len(ports) == 1
        assert ports[0].port == "/dev/ttyUSB0"
        assert ports[0].description == "USB Serial"
        manager.shutdown()


class TestSerialManagerOpenPort:
    """测试 open_port 功能"""

    def test_open_port_success(self, mock_serial, mock_list_ports):
        """测试成功打开串口"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            status = manager.open_port("/dev/ttyUSB0")

            assert status.is_open is True
            assert status.port == "/dev/ttyUSB0"

        manager.shutdown()

    def test_open_port_idempotent(self, mock_serial, mock_list_ports):
        """测试重复打开串口（幂等操作）"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            # 第一次打开
            status1 = manager.open_port("/dev/ttyUSB0")
            # 第二次打开（应该返回当前状态）
            status2 = manager.open_port("/dev/ttyUSB0")

            assert status1.is_open is True
            assert status2.is_open is True
            # create_serial 只应该调用一次
            assert mock_create.call_count == 1

        manager.shutdown()

    def test_open_port_invalid_baudrate(self, mock_list_ports):
        """测试无效波特率"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(InvalidParamError) as exc_info:
            manager.open_port("/dev/ttyUSB0", baudrate=12345)

        assert exc_info.value.code.value == 1005
        manager.shutdown()

    def test_open_port_invalid_bytesize(self, mock_list_ports):
        """测试无效数据位"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(InvalidParamError):
            manager.open_port("/dev/ttyUSB0", bytesize=9)

        manager.shutdown()

    def test_open_port_blacklisted(self, mock_list_ports):
        """测试打开黑名单中的串口"""
        mock_list_ports.return_value = []

        with patch("uart_mcp.serial_manager.get_blacklist_manager") as mock_blacklist:
            mock_blacklist.return_value.is_blacklisted.return_value = True
            manager = SerialManager(enable_auto_reconnect=False)

            with pytest.raises(PortBlacklistedError):
                manager.open_port("/dev/ttyS0")

            manager.shutdown()


class TestSerialManagerClosePort:
    """测试 close_port 功能"""

    def test_close_port_success(self, mock_serial, mock_list_ports):
        """测试成功关闭串口"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            result = manager.close_port("/dev/ttyUSB0")

            assert result["success"] is True
            mock_serial_obj.close.assert_called_once()

        manager.shutdown()

    def test_close_port_not_open(self, mock_list_ports):
        """测试关闭未打开的串口"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.close_port("/dev/ttyUSB0")

        manager.shutdown()


class TestSerialManagerSetConfig:
    """测试 set_config 功能"""

    def test_set_config_success(self, mock_serial, mock_list_ports):
        """测试成功修改配置"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0", baudrate=9600)
            status = manager.set_config("/dev/ttyUSB0", baudrate=115200)

            assert status.config.baudrate == 115200
            mock_serial_obj.apply_settings.assert_called()

        manager.shutdown()

    def test_set_config_not_open(self, mock_list_ports):
        """测试配置未打开的串口"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.set_config("/dev/ttyUSB0", baudrate=115200)

        manager.shutdown()


class TestSerialManagerGetStatus:
    """测试 get_status 功能"""

    def test_get_status_success(self, mock_serial, mock_list_ports):
        """测试成功获取状态"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            status = manager.get_status("/dev/ttyUSB0")

            assert status.is_open is True
            assert status.port == "/dev/ttyUSB0"

        manager.shutdown()

    def test_get_status_not_open(self, mock_list_ports):
        """测试获取未打开串口的状态"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.get_status("/dev/ttyUSB0")

        manager.shutdown()


class TestSerialManagerSendData:
    """测试 send_data 功能"""

    def test_send_data_success(self, mock_serial, mock_list_ports):
        """测试成功发送数据"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_serial_obj.write.return_value = 5
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            bytes_written = manager.send_data("/dev/ttyUSB0", b"hello")

            assert bytes_written == 5
            mock_serial_obj.write.assert_called_once_with(b"hello")

        manager.shutdown()

    def test_send_data_not_open(self, mock_list_ports):
        """测试向未打开的串口发送数据"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.send_data("/dev/ttyUSB0", b"hello")

        manager.shutdown()

    def test_send_data_write_error(self, mock_serial, mock_list_ports):
        """测试写入失败"""
        from serial import SerialException

        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_serial_obj.write.side_effect = SerialException("写入错误")
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")

            with pytest.raises(WriteFailedError):
                manager.send_data("/dev/ttyUSB0", b"hello")

        manager.shutdown()


class TestSerialManagerReadData:
    """测试 read_data 功能"""

    def test_read_data_with_size(self, mock_serial, mock_list_ports):
        """测试读取指定字节数"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_serial_obj.timeout = 1.0
            mock_serial_obj.read.return_value = b"hello"
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            data = manager.read_data("/dev/ttyUSB0", size=5)

            assert data == b"hello"
            mock_serial_obj.read.assert_called_once_with(5)

        manager.shutdown()

    def test_read_data_available(self, mock_serial, mock_list_ports):
        """测试读取所有可用数据"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 10
            mock_serial_obj.timeout = 1.0
            mock_serial_obj.read.return_value = b"0123456789"
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            data = manager.read_data("/dev/ttyUSB0")

            assert data == b"0123456789"
            mock_serial_obj.read.assert_called_once_with(10)

        manager.shutdown()

    def test_read_data_with_timeout(self, mock_serial, mock_list_ports):
        """测试使用自定义超时"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 5
            mock_serial_obj.timeout = 1.0
            mock_serial_obj.read.return_value = b"hello"
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            data = manager.read_data("/dev/ttyUSB0", timeout_ms=500)

            # 验证超时被临时修改
            assert mock_serial_obj.timeout == 1.0  # 应该恢复原值

        manager.shutdown()

    def test_read_data_not_open(self, mock_list_ports):
        """测试从未打开的串口读取数据"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with pytest.raises(PortClosedError):
            manager.read_data("/dev/ttyUSB0")

        manager.shutdown()

    def test_read_data_empty(self, mock_serial, mock_list_ports):
        """测试无数据可读"""
        mock_list_ports.return_value = []
        manager = SerialManager(enable_auto_reconnect=False)

        with patch.object(manager, "_create_serial") as mock_create:
            mock_serial_obj = MagicMock()
            mock_serial_obj.is_open = True
            mock_serial_obj.in_waiting = 0
            mock_serial_obj.timeout = 1.0
            mock_serial_obj.read.return_value = b""
            mock_create.return_value = mock_serial_obj

            manager.open_port("/dev/ttyUSB0")
            data = manager.read_data("/dev/ttyUSB0")

            assert data == b""

        manager.shutdown()

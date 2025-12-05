"""pytest 配置和共享 fixtures"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_serial():
    """模拟 pyserial Serial 对象"""
    with patch("serial.Serial") as mock:
        serial_instance = MagicMock()
        serial_instance.is_open = True
        serial_instance.in_waiting = 0
        mock.return_value = serial_instance
        yield mock


@pytest.fixture
def mock_list_ports():
    """模拟 serial.tools.list_ports.comports()"""
    with patch("serial.tools.list_ports.comports") as mock:
        yield mock


@pytest.fixture
def mock_blacklist_empty():
    """模拟空黑名单"""
    with patch("uart_mcp.config.get_blacklist_path") as mock_path:
        mock_path.return_value.exists.return_value = False
        yield mock_path

"""pytest 配置和共享 fixtures"""

import threading
from unittest.mock import MagicMock, patch

import pytest


class MockSerialLoopback:
    """模拟串口回环的 Serial 类
    
    写入的数据会自动进入读取缓冲区，模拟TX/RX短接的回环效果
    """
    
    def __init__(self, port=None, baudrate=9600, bytesize=8, parity='N',
                 stopbits=1, timeout=None, write_timeout=None, 
                 xonxoff=False, rtscts=False, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        
        self._is_open = True
        self._buffer = bytearray()  # 回环缓冲区
        self._lock = threading.Lock()
    
    @property
    def is_open(self):
        return self._is_open
    
    @property
    def in_waiting(self):
        with self._lock:
            return len(self._buffer)
    
    def open(self):
        self._is_open = True
    
    def close(self):
        self._is_open = False
    
    def write(self, data):
        """写入数据，同时放入读取缓冲区（回环）"""
        if not self._is_open:
            raise Exception("串口未打开")
        if isinstance(data, str):
            data = data.encode('utf-8')
        with self._lock:
            self._buffer.extend(data)
        return len(data)
    
    def read(self, size=1):
        """从缓冲区读取数据"""
        if not self._is_open:
            raise Exception("串口未打开")
        with self._lock:
            data = bytes(self._buffer[:size])
            self._buffer = self._buffer[size:]
        return data
    
    def read_all(self):
        """读取所有可用数据"""
        with self._lock:
            data = bytes(self._buffer)
            self._buffer.clear()
        return data
    
    def reset_input_buffer(self):
        """清空输入缓冲区"""
        with self._lock:
            self._buffer.clear()
    
    def reset_output_buffer(self):
        """清空输出缓冲区（模拟）"""
        pass
    
    def flush(self):
        """刷新输出"""
        pass
    
    def apply_settings(self, settings):
        """应用配置设置（热更新）"""
        if "baudrate" in settings:
            self.baudrate = settings["baudrate"]
        if "bytesize" in settings:
            self.bytesize = settings["bytesize"]
        if "parity" in settings:
            self.parity = settings["parity"]
        if "stopbits" in settings:
            self.stopbits = settings["stopbits"]
        if "xonxoff" in settings:
            self.xonxoff = settings["xonxoff"]
        if "rtscts" in settings:
            self.rtscts = settings["rtscts"]


class MockPortInfo:
    """模拟串口信息对象"""
    def __init__(self, device, description="模拟串口", hwid="MOCK_HWID"):
        self.device = device
        self.description = description
        self.hwid = hwid


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
def mock_serial_loopback():
    """模拟串口回环 - 写入数据自动进入读取缓冲区
    
    用于集成测试，模拟真实硬件的回环效果
    """
    mock_instances = {}
    
    def create_mock_serial(*args, **kwargs):
        port = kwargs.get('port') or (args[0] if args else '/dev/mock')
        if port not in mock_instances:
            mock_instances[port] = MockSerialLoopback(*args, **kwargs)
        return mock_instances[port]
    
    with patch("serial.Serial", side_effect=create_mock_serial):
        yield mock_instances


@pytest.fixture
def mock_list_ports():
    """模拟 serial.tools.list_ports.comports()"""
    with patch("serial.tools.list_ports.comports") as mock:
        yield mock


@pytest.fixture
def mock_list_ports_with_devices():
    """模拟返回设备列表的 list_ports"""
    mock_ports = [
        MockPortInfo("/dev/ttyMOCK0", "模拟USB串口", "USB VID:PID=1234:5678"),
        MockPortInfo("/dev/ttyMOCK1", "模拟蓝牙串口", "BLUETOOTH ADDR=00:11:22:33:44:55"),
    ]
    with patch("serial.tools.list_ports.comports", return_value=mock_ports):
        yield mock_ports


@pytest.fixture
def mock_blacklist_empty():
    """模拟空黑名单"""
    with patch("uart_mcp.config.get_blacklist_path") as mock_path:
        mock_path.return_value.exists.return_value = False
        yield mock_path


@pytest.fixture
def reset_managers():
    """重置全局管理器状态，用于隔离测试"""
    # 保存原状态
    from uart_mcp import serial_manager, terminal_manager
    
    old_serial = serial_manager._serial_manager
    old_terminal = terminal_manager._terminal_manager
    
    # 重置为 None
    serial_manager._serial_manager = None
    terminal_manager._terminal_manager = None
    
    yield
    
    # 清理新创建的管理器
    try:
        if serial_manager._serial_manager is not None:
            serial_manager._serial_manager.shutdown()
    except Exception:
        pass
    try:
        if terminal_manager._terminal_manager is not None:
            terminal_manager._terminal_manager.shutdown()
    except Exception:
        pass
    
    # 恢复原状态
    serial_manager._serial_manager = old_serial
    terminal_manager._terminal_manager = old_terminal

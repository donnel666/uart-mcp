"""类型定义模块

定义串口配置和状态相关的数据类型。
"""

from dataclasses import dataclass
from enum import Enum


class Parity(str, Enum):
    """校验位枚举"""

    NONE = "N"
    EVEN = "E"
    ODD = "O"
    MARK = "M"
    SPACE = "S"


class StopBits(float, Enum):
    """停止位枚举"""

    ONE = 1
    ONE_POINT_FIVE = 1.5
    TWO = 2


class FlowControl(str, Enum):
    """流控制枚举"""

    NONE = "none"
    HARDWARE = "hardware"  # RTS/CTS
    SOFTWARE = "software"  # XON/XOFF


# 支持的波特率列表
SUPPORTED_BAUDRATES: tuple[int, ...] = (
    300,
    600,
    1200,
    2400,
    4800,
    9600,
    14400,
    19200,
    38400,
    57600,
    115200,
    230400,
    460800,
    921600,
)

# 支持的数据位
SUPPORTED_BYTESIZES: tuple[int, ...] = (5, 6, 7, 8)

# 默认配置值
DEFAULT_BAUDRATE = 9600
DEFAULT_BYTESIZE = 8
DEFAULT_PARITY = Parity.NONE
DEFAULT_STOPBITS = StopBits.ONE
DEFAULT_FLOW_CONTROL = FlowControl.NONE
DEFAULT_TIMEOUT_MS = 1000
DEFAULT_WRITE_TIMEOUT_MS = 1000
DEFAULT_CONNECT_TIMEOUT_MS = 5000


@dataclass
class SerialConfig:
    """串口配置

    Attributes:
        baudrate: 波特率
        bytesize: 数据位
        parity: 校验位
        stopbits: 停止位
        flow_control: 流控制
        read_timeout_ms: 读取超时（毫秒）
        write_timeout_ms: 写入超时（毫秒）
    """

    baudrate: int = DEFAULT_BAUDRATE
    bytesize: int = DEFAULT_BYTESIZE
    parity: Parity = DEFAULT_PARITY
    stopbits: StopBits = DEFAULT_STOPBITS
    flow_control: FlowControl = DEFAULT_FLOW_CONTROL
    read_timeout_ms: int = DEFAULT_TIMEOUT_MS
    write_timeout_ms: int = DEFAULT_WRITE_TIMEOUT_MS

    def to_dict(self) -> dict[str, int | str | float]:
        """转换为字典格式"""
        return {
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity.value,
            "stopbits": float(self.stopbits.value),
            "flow_control": self.flow_control.value,
            "read_timeout_ms": self.read_timeout_ms,
            "write_timeout_ms": self.write_timeout_ms,
        }


@dataclass
class PortInfo:
    """串口信息

    Attributes:
        port: 串口路径（如 /dev/ttyUSB0 或 COM1）
        description: 串口描述
        hwid: 硬件ID
    """

    port: str
    description: str
    hwid: str

    def to_dict(self) -> dict[str, str]:
        """转换为字典格式"""
        return {
            "port": self.port,
            "description": self.description,
            "hwid": self.hwid,
        }


@dataclass
class PortStatus:
    """串口状态

    Attributes:
        port: 串口路径
        is_open: 是否已打开
        config: 当前配置
        connected: 物理连接状态
        reconnecting: 是否正在重连
    """

    port: str
    is_open: bool
    config: SerialConfig | None = None
    connected: bool = False
    reconnecting: bool = False

    def to_dict(self) -> dict[str, str | bool | dict[str, int | str | float] | None]:
        """转换为字典格式"""
        return {
            "port": self.port,
            "is_open": self.is_open,
            "config": self.config.to_dict() if self.config else None,
            "connected": self.connected,
            "reconnecting": self.reconnecting,
        }

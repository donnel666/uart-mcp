"""类型模块测试"""

from uart_mcp.types import (
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_FLOW_CONTROL,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    FlowControl,
    Parity,
    PortInfo,
    PortStatus,
    SerialConfig,
    StopBits,
)


class TestEnums:
    """测试枚举类型"""

    def test_parity_values(self):
        """测试校验位枚举"""
        assert Parity.NONE.value == "N"
        assert Parity.EVEN.value == "E"
        assert Parity.ODD.value == "O"
        assert Parity.MARK.value == "M"
        assert Parity.SPACE.value == "S"

    def test_stopbits_values(self):
        """测试停止位枚举"""
        assert StopBits.ONE.value == 1
        assert StopBits.ONE_POINT_FIVE.value == 1.5
        assert StopBits.TWO.value == 2

    def test_flow_control_values(self):
        """测试流控制枚举"""
        assert FlowControl.NONE.value == "none"
        assert FlowControl.HARDWARE.value == "hardware"
        assert FlowControl.SOFTWARE.value == "software"


class TestSerialConfig:
    """测试串口配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = SerialConfig()
        assert config.baudrate == DEFAULT_BAUDRATE
        assert config.bytesize == DEFAULT_BYTESIZE
        assert config.parity == DEFAULT_PARITY
        assert config.stopbits == DEFAULT_STOPBITS
        assert config.flow_control == DEFAULT_FLOW_CONTROL

    def test_custom_config(self):
        """测试自定义配置"""
        config = SerialConfig(
            baudrate=115200,
            bytesize=7,
            parity=Parity.EVEN,
            stopbits=StopBits.TWO,
            flow_control=FlowControl.HARDWARE,
        )
        assert config.baudrate == 115200
        assert config.bytesize == 7
        assert config.parity == Parity.EVEN
        assert config.stopbits == StopBits.TWO
        assert config.flow_control == FlowControl.HARDWARE

    def test_to_dict(self):
        """测试转换为字典"""
        config = SerialConfig()
        result = config.to_dict()
        assert result["baudrate"] == DEFAULT_BAUDRATE
        assert result["bytesize"] == DEFAULT_BYTESIZE
        assert result["parity"] == "N"
        assert result["stopbits"] == 1.0
        assert result["flow_control"] == "none"


class TestPortInfo:
    """测试串口信息类"""

    def test_port_info_creation(self):
        """测试创建串口信息"""
        info = PortInfo(
            port="/dev/ttyUSB0",
            description="USB Serial",
            hwid="USB VID:PID=1234:5678",
        )
        assert info.port == "/dev/ttyUSB0"
        assert info.description == "USB Serial"
        assert info.hwid == "USB VID:PID=1234:5678"

    def test_to_dict(self):
        """测试转换为字典"""
        info = PortInfo(port="COM1", description="COM Port", hwid="ACPI\\PNP0501")
        result = info.to_dict()
        assert result["port"] == "COM1"
        assert result["description"] == "COM Port"
        assert result["hwid"] == "ACPI\\PNP0501"


class TestPortStatus:
    """测试串口状态类"""

    def test_port_status_open(self):
        """测试已打开的串口状态"""
        config = SerialConfig()
        status = PortStatus(
            port="/dev/ttyUSB0",
            is_open=True,
            config=config,
            connected=True,
            reconnecting=False,
        )
        assert status.is_open is True
        assert status.connected is True
        assert status.reconnecting is False

    def test_to_dict(self):
        """测试转换为字典"""
        config = SerialConfig()
        status = PortStatus(port="/dev/ttyUSB0", is_open=True, config=config)
        result = status.to_dict()
        assert result["port"] == "/dev/ttyUSB0"
        assert result["is_open"] is True
        assert result["config"] is not None

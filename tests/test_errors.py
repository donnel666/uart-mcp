"""错误模块测试"""

from uart_mcp.errors import (
    ErrorCode,
    InvalidParamError,
    PortBlacklistedError,
    PortBusyError,
    PortClosedError,
    PortNotFoundError,
    SerialError,
)


class TestErrorCode:
    """测试错误码枚举"""

    def test_error_codes_values(self):
        """测试错误码值"""
        assert ErrorCode.PORT_NOT_FOUND == 1001
        assert ErrorCode.PORT_BUSY == 1002
        assert ErrorCode.PORT_OPEN_FAILED == 1003
        assert ErrorCode.PORT_CLOSED == 1004
        assert ErrorCode.INVALID_PARAM == 1005
        assert ErrorCode.READ_TIMEOUT == 1006
        assert ErrorCode.WRITE_FAILED == 1007
        assert ErrorCode.PERMISSION_DENIED == 1008
        assert ErrorCode.PORT_BLACKLISTED == 1009


class TestSerialError:
    """测试串口异常基类"""

    def test_serial_error_with_detail(self):
        """测试带详情的异常"""
        error = SerialError(ErrorCode.PORT_NOT_FOUND, "/dev/ttyUSB0")
        assert error.code == ErrorCode.PORT_NOT_FOUND
        assert "串口不存在" in error.message
        assert "/dev/ttyUSB0" in error.message

    def test_serial_error_without_detail(self):
        """测试不带详情的异常"""
        error = SerialError(ErrorCode.PORT_NOT_FOUND)
        assert error.code == ErrorCode.PORT_NOT_FOUND
        assert error.message == "串口不存在"

    def test_to_dict(self):
        """测试转换为字典"""
        error = SerialError(ErrorCode.PORT_NOT_FOUND, "/dev/ttyUSB0")
        result = error.to_dict()
        assert result["error"]["code"] == 1001
        assert "串口不存在" in result["error"]["message"]


class TestSpecificErrors:
    """测试具体异常类"""

    def test_port_not_found_error(self):
        """测试串口不存在异常"""
        error = PortNotFoundError("/dev/ttyUSB0")
        assert error.code == ErrorCode.PORT_NOT_FOUND
        assert "/dev/ttyUSB0" in error.message

    def test_port_busy_error(self):
        """测试串口被占用异常"""
        error = PortBusyError("COM1")
        assert error.code == ErrorCode.PORT_BUSY
        assert "COM1" in error.message

    def test_port_closed_error(self):
        """测试串口已关闭异常"""
        error = PortClosedError("/dev/ttyUSB0")
        assert error.code == ErrorCode.PORT_CLOSED

    def test_invalid_param_error(self):
        """测试参数无效异常"""
        error = InvalidParamError("baudrate", -1, "必须为正数")
        assert error.code == ErrorCode.INVALID_PARAM
        assert "baudrate" in error.message
        assert "-1" in error.message

    def test_port_blacklisted_error(self):
        """测试串口在黑名单中异常"""
        error = PortBlacklistedError("/dev/ttyS0")
        assert error.code == ErrorCode.PORT_BLACKLISTED
        assert "/dev/ttyS0" in error.message

"""串口管理器模块

提供串口的枚举、打开、关闭、配置等核心功能。
"""

import logging
import threading
import time
from typing import Any

import serial
import serial.tools.list_ports
from serial import SerialException

from .config import get_blacklist_manager
from .errors import (
    InvalidParamError,
    PermissionDeniedError,
    PortBlacklistedError,
    PortBusyError,
    PortClosedError,
    PortNotFoundError,
    PortOpenFailedError,
)
from .types import (
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_FLOW_CONTROL,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DEFAULT_TIMEOUT_MS,
    DEFAULT_WRITE_TIMEOUT_MS,
    SUPPORTED_BAUDRATES,
    SUPPORTED_BYTESIZES,
    FlowControl,
    Parity,
    PortInfo,
    PortStatus,
    SerialConfig,
    StopBits,
)

logger = logging.getLogger(__name__)

# 重连检测间隔（秒）
RECONNECT_CHECK_INTERVAL = 2.0
# 重连尝试间隔（秒）
RECONNECT_RETRY_INTERVAL = 3.0


class ManagedPort:
    """管理的串口连接

    封装 pyserial 的 Serial 对象，添加配置和状态管理。

    Attributes:
        port: 串口路径
        serial: pyserial Serial 对象
        config: 串口配置
        reconnecting: 是否正在重连
        auto_reconnect: 是否启用自动重连
    """

    def __init__(
        self,
        port: str,
        serial_obj: serial.Serial,
        config: SerialConfig,
        auto_reconnect: bool = True,
    ) -> None:
        self.port = port
        self.serial = serial_obj
        self.config = config
        self.reconnecting = False
        self.auto_reconnect = auto_reconnect
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        """检查物理连接状态"""
        try:
            # 尝试读取 DSR 状态来检测连接
            # 如果串口已断开，这会抛出异常
            if self.serial.is_open:
                # 某些串口可能不支持 DSR，所以我们用 in_waiting 检查
                _ = self.serial.in_waiting
                return True
        except (SerialException, OSError):
            pass
        return False


class SerialManager:
    """串口管理器

    提供串口设备的枚举、打开、关闭、配置等功能。
    支持多串口同时连接、配置热更新和自动重连。

    Attributes:
        _ports: 已打开的串口字典，键为串口路径
        _lock: 线程锁
        _reconnect_thread: 重连检测线程
        _running: 管理器运行状态
    """

    def __init__(self, enable_auto_reconnect: bool = True) -> None:
        """初始化串口管理器

        Args:
            enable_auto_reconnect: 是否启用自动重连功能
        """
        self._ports: dict[str, ManagedPort] = {}
        self._lock = threading.RLock()
        self._running = True
        self._enable_auto_reconnect = enable_auto_reconnect
        self._reconnect_thread: threading.Thread | None = None

        if enable_auto_reconnect:
            self._start_reconnect_thread()

    def _start_reconnect_thread(self) -> None:
        """启动重连检测线程"""
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop, daemon=True, name="serial-reconnect"
        )
        self._reconnect_thread.start()
        logger.debug("重连检测线程已启动")

    def _reconnect_loop(self) -> None:
        """重连检测循环"""
        while self._running:
            try:
                self._check_and_reconnect()
            except Exception as e:
                logger.error("重连检测异常：%s", e)
            time.sleep(RECONNECT_CHECK_INTERVAL)

    def _check_and_reconnect(self) -> None:
        """检查并重连断开的串口"""
        with self._lock:
            ports_to_reconnect: list[tuple[str, SerialConfig]] = []
            for port_path, managed in list(self._ports.items()):
                if not managed.auto_reconnect:
                    continue
                if not managed.is_connected and not managed.reconnecting:
                    logger.info("检测到串口断开：%s", port_path)
                    managed.reconnecting = True
                    ports_to_reconnect.append((port_path, managed.config))

        # 在锁外执行重连操作
        for port_path, config in ports_to_reconnect:
            self._try_reconnect(port_path, config)

    def _try_reconnect(self, port: str, config: SerialConfig) -> None:
        """尝试重连串口

        Args:
            port: 串口路径
            config: 串口配置
        """
        logger.info("尝试重连串口：%s", port)
        try:
            serial_obj = self._create_serial(port, config)
            with self._lock:
                if port in self._ports:
                    old_managed = self._ports[port]
                    try:
                        old_managed.serial.close()
                    except Exception:
                        pass
                    # 保留原始的 auto_reconnect 设置
                    self._ports[port] = ManagedPort(
                        port,
                        serial_obj,
                        config,
                        auto_reconnect=old_managed.auto_reconnect,
                    )
                    logger.info("串口重连成功：%s", port)
                else:
                    # 端口在重连期间被关闭，释放新创建的串口资源
                    serial_obj.close()
                    logger.info("串口在重连期间被关闭，已释放资源：%s", port)
        except Exception as e:
            logger.warning("串口重连失败：%s - %s", port, e)
            with self._lock:
                if port in self._ports:
                    self._ports[port].reconnecting = False

    def _create_serial(self, port: str, config: SerialConfig) -> serial.Serial:
        """创建 pyserial Serial 对象

        Args:
            port: 串口路径
            config: 串口配置

        Returns:
            配置好的 Serial 对象

        Raises:
            PortNotFoundError: 串口不存在
            PortBusyError: 串口被占用
            PortOpenFailedError: 打开失败
        """
        # 转换配置
        parity_map = {
            Parity.NONE: serial.PARITY_NONE,
            Parity.EVEN: serial.PARITY_EVEN,
            Parity.ODD: serial.PARITY_ODD,
            Parity.MARK: serial.PARITY_MARK,
            Parity.SPACE: serial.PARITY_SPACE,
        }

        stopbits_map = {
            StopBits.ONE: serial.STOPBITS_ONE,
            StopBits.ONE_POINT_FIVE: serial.STOPBITS_ONE_POINT_FIVE,
            StopBits.TWO: serial.STOPBITS_TWO,
        }

        try:
            serial_obj = serial.Serial(
                port=port,
                baudrate=config.baudrate,
                bytesize=config.bytesize,
                parity=parity_map[config.parity],
                stopbits=stopbits_map[config.stopbits],
                timeout=config.read_timeout_ms / 1000.0,
                write_timeout=config.write_timeout_ms / 1000.0,
                xonxoff=config.flow_control == FlowControl.SOFTWARE,
                rtscts=config.flow_control == FlowControl.HARDWARE,
            )
            return serial_obj
        except serial.SerialException as e:
            error_msg = str(e).lower()
            if "no such file" in error_msg or "not found" in error_msg:
                raise PortNotFoundError(port) from e
            if "permission" in error_msg or "access" in error_msg:
                raise PermissionDeniedError(port) from e
            if "busy" in error_msg or "in use" in error_msg:
                raise PortBusyError(port) from e
            raise PortOpenFailedError(port, str(e)) from e

    def list_ports(self) -> list[PortInfo]:
        """列出所有可用串口

        返回系统中所有可用的串口，已过滤黑名单中的串口。

        Returns:
            串口信息列表
        """
        blacklist = get_blacklist_manager()
        ports: list[PortInfo] = []

        for port_info in serial.tools.list_ports.comports():
            if blacklist.is_blacklisted(port_info.device):
                logger.debug("串口在黑名单中，已过滤：%s", port_info.device)
                continue
            ports.append(
                PortInfo(
                    port=port_info.device,
                    description=port_info.description or "",
                    hwid=port_info.hwid or "",
                )
            )

        return ports

    def open_port(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUDRATE,
        bytesize: int = DEFAULT_BYTESIZE,
        parity: str = DEFAULT_PARITY.value,
        stopbits: float = DEFAULT_STOPBITS.value,
        flow_control: str = DEFAULT_FLOW_CONTROL.value,
        read_timeout_ms: int = DEFAULT_TIMEOUT_MS,
        write_timeout_ms: int = DEFAULT_WRITE_TIMEOUT_MS,
        auto_reconnect: bool = True,
    ) -> PortStatus:
        """打开串口

        Args:
            port: 串口路径
            baudrate: 波特率
            bytesize: 数据位
            parity: 校验位
            stopbits: 停止位
            flow_control: 流控制
            read_timeout_ms: 读取超时（毫秒）
            write_timeout_ms: 写入超时（毫秒）
            auto_reconnect: 是否启用自动重连

        Returns:
            串口状态

        Raises:
            PortBlacklistedError: 串口在黑名单中
            PortNotFoundError: 串口不存在
            PortBusyError: 串口被占用
            InvalidParamError: 参数无效
        """
        # 检查黑名单
        blacklist = get_blacklist_manager()
        if blacklist.is_blacklisted(port):
            raise PortBlacklistedError(port)

        # 验证参数
        config = self._validate_and_create_config(
            baudrate,
            bytesize,
            parity,
            stopbits,
            flow_control,
            read_timeout_ms,
            write_timeout_ms,
        )

        with self._lock:
            # 检查是否已打开（幂等操作）
            if port in self._ports:
                managed = self._ports[port]
                logger.info("串口已打开，返回当前状态：%s", port)
                return PortStatus(
                    port=port,
                    is_open=True,
                    config=managed.config,
                    connected=managed.is_connected,
                    reconnecting=managed.reconnecting,
                )

            # 打开串口
            serial_obj = self._create_serial(port, config)
            managed = ManagedPort(port, serial_obj, config, auto_reconnect)
            self._ports[port] = managed
            logger.info("串口打开成功：%s", port)

            return PortStatus(
                port=port,
                is_open=True,
                config=config,
                connected=managed.is_connected,
                reconnecting=False,
            )

    def _validate_and_create_config(
        self,
        baudrate: int,
        bytesize: int,
        parity: str,
        stopbits: float,
        flow_control: str,
        read_timeout_ms: int,
        write_timeout_ms: int,
    ) -> SerialConfig:
        """验证参数并创建配置对象

        Raises:
            InvalidParamError: 参数无效
        """
        # 验证波特率
        if baudrate not in SUPPORTED_BAUDRATES:
            raise InvalidParamError(
                "baudrate", baudrate, f"支持的值：{SUPPORTED_BAUDRATES}"
            )

        # 验证数据位
        if bytesize not in SUPPORTED_BYTESIZES:
            raise InvalidParamError(
                "bytesize", bytesize, f"支持的值：{SUPPORTED_BYTESIZES}"
            )

        # 验证校验位
        try:
            parity_enum = Parity(parity)
        except ValueError:
            raise InvalidParamError(
                "parity", parity, f"支持的值：{[p.value for p in Parity]}"
            )

        # 验证停止位
        try:
            stopbits_enum = StopBits(stopbits)
        except ValueError:
            raise InvalidParamError(
                "stopbits", stopbits, f"支持的值：{[s.value for s in StopBits]}"
            )

        # 验证流控制
        try:
            flow_enum = FlowControl(flow_control)
        except ValueError:
            valid_values = [f.value for f in FlowControl]
            raise InvalidParamError(
                "flow_control", flow_control, f"支持的值：{valid_values}"
            )

        # 验证超时
        if read_timeout_ms < 0 or read_timeout_ms > 60000:
            raise InvalidParamError("read_timeout_ms", read_timeout_ms, "范围：0-60000")
        if write_timeout_ms < 0 or write_timeout_ms > 60000:
            raise InvalidParamError(
                "write_timeout_ms", write_timeout_ms, "范围：0-60000"
            )

        return SerialConfig(
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity_enum,
            stopbits=stopbits_enum,
            flow_control=flow_enum,
            read_timeout_ms=read_timeout_ms,
            write_timeout_ms=write_timeout_ms,
        )

    def close_port(self, port: str) -> dict[str, Any]:
        """关闭串口

        Args:
            port: 串口路径

        Returns:
            操作结果

        Raises:
            PortClosedError: 串口未打开
        """
        with self._lock:
            if port not in self._ports:
                raise PortClosedError(port)

            managed = self._ports.pop(port)
            try:
                managed.serial.close()
            except Exception as e:
                logger.warning("关闭串口时发生异常：%s - %s", port, e)

            logger.info("串口关闭成功：%s", port)
            return {"success": True, "port": port}

    def set_config(
        self,
        port: str,
        baudrate: int | None = None,
        bytesize: int | None = None,
        parity: str | None = None,
        stopbits: float | None = None,
        flow_control: str | None = None,
        read_timeout_ms: int | None = None,
        write_timeout_ms: int | None = None,
    ) -> PortStatus:
        """修改串口配置（热更新）

        Args:
            port: 串口路径
            baudrate: 波特率（可选）
            bytesize: 数据位（可选）
            parity: 校验位（可选）
            stopbits: 停止位（可选）
            flow_control: 流控制（可选）
            read_timeout_ms: 读取超时（可选）
            write_timeout_ms: 写入超时（可选）

        Returns:
            更新后的串口状态

        Raises:
            PortClosedError: 串口未打开
            InvalidParamError: 参数无效
        """
        with self._lock:
            if port not in self._ports:
                raise PortClosedError(port)

            managed = self._ports[port]
            current_config = managed.config

            # 构建新配置，未指定的参数使用当前值
            cc = current_config  # 简化引用
            new_baudrate = baudrate if baudrate is not None else cc.baudrate
            new_bytesize = bytesize if bytesize is not None else cc.bytesize
            new_parity = parity if parity is not None else cc.parity.value
            new_stopbits = stopbits if stopbits is not None else cc.stopbits.value
            new_flow = (
                flow_control if flow_control is not None else cc.flow_control.value
            )
            new_read_timeout = (
                read_timeout_ms if read_timeout_ms is not None else cc.read_timeout_ms
            )
            new_write_timeout = (
                write_timeout_ms
                if write_timeout_ms is not None
                else cc.write_timeout_ms
            )
            new_config = self._validate_and_create_config(
                new_baudrate,
                new_bytesize,
                new_parity,
                new_stopbits,
                new_flow,
                new_read_timeout,
                new_write_timeout,
            )

            # 应用配置（热更新）
            self._apply_config(managed, new_config)
            managed.config = new_config

            logger.info("串口配置更新成功：%s", port)
            return PortStatus(
                port=port,
                is_open=True,
                config=new_config,
                connected=managed.is_connected,
                reconnecting=managed.reconnecting,
            )

    def _apply_config(self, managed: ManagedPort, config: SerialConfig) -> None:
        """应用配置到已打开的串口

        Args:
            managed: 管理的串口对象
            config: 新配置
        """
        ser = managed.serial

        # 转换校验位
        parity_map = {
            Parity.NONE: serial.PARITY_NONE,
            Parity.EVEN: serial.PARITY_EVEN,
            Parity.ODD: serial.PARITY_ODD,
            Parity.MARK: serial.PARITY_MARK,
            Parity.SPACE: serial.PARITY_SPACE,
        }

        # 转换停止位
        stopbits_map = {
            StopBits.ONE: serial.STOPBITS_ONE,
            StopBits.ONE_POINT_FIVE: serial.STOPBITS_ONE_POINT_FIVE,
            StopBits.TWO: serial.STOPBITS_TWO,
        }

        # 使用 apply_settings 进行热更新
        ser.apply_settings(
            {
                "baudrate": config.baudrate,
                "bytesize": config.bytesize,
                "parity": parity_map[config.parity],
                "stopbits": stopbits_map[config.stopbits],
                "xonxoff": config.flow_control == FlowControl.SOFTWARE,
                "rtscts": config.flow_control == FlowControl.HARDWARE,
            }
        )

        # 更新超时设置
        ser.timeout = config.read_timeout_ms / 1000.0
        ser.write_timeout = config.write_timeout_ms / 1000.0

    def get_status(self, port: str) -> PortStatus:
        """获取串口状态

        Args:
            port: 串口路径

        Returns:
            串口状态

        Raises:
            PortClosedError: 串口未打开
        """
        with self._lock:
            if port not in self._ports:
                raise PortClosedError(port)

            managed = self._ports[port]
            return PortStatus(
                port=port,
                is_open=True,
                config=managed.config,
                connected=managed.is_connected,
                reconnecting=managed.reconnecting,
            )

    def get_all_status(self) -> list[PortStatus]:
        """获取所有已打开串口的状态

        Returns:
            串口状态列表
        """
        with self._lock:
            return [
                PortStatus(
                    port=port,
                    is_open=True,
                    config=managed.config,
                    connected=managed.is_connected,
                    reconnecting=managed.reconnecting,
                )
                for port, managed in self._ports.items()
            ]

    def shutdown(self) -> None:
        """关闭管理器

        停止重连线程并关闭所有串口。
        """
        self._running = False

        # 等待重连线程结束
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=5.0)

        # 关闭所有串口
        with self._lock:
            for port, managed in list(self._ports.items()):
                try:
                    managed.serial.close()
                    logger.debug("关闭串口：%s", port)
                except Exception as e:
                    logger.warning("关闭串口失败：%s - %s", port, e)
            self._ports.clear()

        logger.info("串口管理器已关闭")


# 全局串口管理器实例
_serial_manager: SerialManager | None = None


def get_serial_manager() -> SerialManager:
    """获取串口管理器单例

    Returns:
        串口管理器实例
    """
    global _serial_manager
    if _serial_manager is None:
        _serial_manager = SerialManager()
    return _serial_manager

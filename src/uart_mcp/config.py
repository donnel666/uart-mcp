"""配置管理模块

管理串口黑名单和全局配置。
"""

import logging
import os
import platform
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11 兼容

logger = logging.getLogger(__name__)

# 支持的波特率和数据位（从 types.py 导入常量以保持一致性）
SUPPORTED_BAUDRATES: tuple[int, ...] = (
    300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 38400, 57600,
    115200, 230400, 460800, 921600,
)
SUPPORTED_BYTESIZES: tuple[int, ...] = (5, 6, 7, 8)
SUPPORTED_PARITIES: tuple[str, ...] = ("N", "E", "O", "M", "S")
SUPPORTED_STOPBITS: tuple[float, ...] = (1.0, 1.5, 2.0)
SUPPORTED_LOG_LEVELS: tuple[str, ...] = (
    "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
)


@dataclass
class UartConfig:
    """全局配置

    Attributes:
        baudrate: 波特率
        bytesize: 数据位
        parity: 校验位
        stopbits: 停止位
        read_timeout: 读取超时（毫秒）
        write_timeout: 写入超时（毫秒）
        xonxoff: 软件流控
        rtscts: 硬件流控
        dsrdtr: DSR/DTR 流控
        auto_reconnect: 自动重连开关
        reconnect_interval: 重连间隔（毫秒）
        log_level: 日志级别
    """

    # 串口默认参数
    baudrate: int = 115200
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1.0
    # 超时设置（毫秒）
    read_timeout: int = 1000
    write_timeout: int = 1000
    # 流控
    xonxoff: bool = False
    rtscts: bool = False
    dsrdtr: bool = False
    # 自动重连
    auto_reconnect: bool = True
    reconnect_interval: int = 5000
    # 日志级别
    log_level: str = "INFO"


def get_config_dir() -> Path:
    """获取配置文件目录

    根据操作系统返回对应的配置目录路径。

    Returns:
        配置目录路径
    """
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / ".uart-mcp"
    else:  # Linux/macOS
        return Path.home() / ".uart-mcp"


def get_config_path() -> Path:
    """获取配置文件路径

    Returns:
        配置文件路径
    """
    return get_config_dir() / "config.toml"


def get_blacklist_path() -> Path:
    """获取黑名单配置文件路径

    Returns:
        黑名单文件路径
    """
    return get_config_dir() / "blacklist.conf"


class ConfigManager:
    """配置管理器

    负责加载、解析和管理全局配置文件。

    Attributes:
        _config: 当前配置实例
        _lock: 线程锁，用于热加载时的并发保护
    """

    def __init__(self) -> None:
        """初始化配置管理器"""
        self._config: UartConfig = UartConfig()
        self._lock = threading.Lock()
        self._load_config()

    def _check_permission(self, path: Path) -> None:
        """校验文件权限（仅 Unix 系统）

        Args:
            path: 文件路径

        Raises:
            PermissionError: 权限不符（错误码 1008）
        """
        import stat

        # 仅在 Unix 系统执行权限校验
        if platform.system() in ("Linux", "Darwin"):
            mode = path.stat().st_mode
            file_perm = stat.S_IMODE(mode)
            # 600 = rw------- (仅所有者可读写)
            if file_perm != 0o600:
                raise PermissionError(
                    f"配置文件权限应为 600（rw-------），"
                    f"当前为 {oct(file_perm)}，错误码：1008"
                )

    def _load_config_from_file(self, config_path: Path) -> UartConfig:
        """从配置文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            解析后的配置对象

        Raises:
            PermissionError: 权限校验失败（错误码 1008）
            ValueError: 配置解析失败或值不在有效范围（错误码 1005）
        """
        # 权限校验
        if config_path.exists():
            self._check_permission(config_path)

        # 读取并解析 TOML
        try:
            with config_path.open("rb") as f:
                config_dict: dict[str, Any] = tomllib.load(f)
        except FileNotFoundError:
            logger.info("配置文件不存在，使用默认配置：%s", config_path)
            return UartConfig()
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"TOML 解析失败，错误码：1005，原因：{e}") from e
        except Exception as e:
            raise ValueError(f"读取配置文件失败，错误码：1005，原因：{e}") from e

        # 构建配置对象（缺失字段使用默认值）
        config = self._build_config_from_dict(config_dict)

        # 值范围验证（警告而不阻止加载）
        self._validate_config_ranges(config)

        return config

    def _build_config_from_dict(self, config_dict: dict[str, Any]) -> UartConfig:
        """从字典构建配置对象（含类型验证）

        Args:
            config_dict: 配置字典

        Returns:
            配置对象

        Raises:
            ValueError: 配置类型错误或值无效
        """
        config = UartConfig()

        # 串口配置
        serial = config_dict.get("serial", {})
        if "baudrate" in serial:
            raw = serial["baudrate"]
            if not isinstance(raw, int):
                raise ValueError(f"baudrate 必须是整数，得到 {type(raw).__name__}")
            config.baudrate = raw
        if "bytesize" in serial:
            raw = serial["bytesize"]
            if not isinstance(raw, int):
                raise ValueError(f"bytesize 必须是整数，得到 {type(raw).__name__}")
            config.bytesize = raw
        if "parity" in serial:
            raw = serial["parity"]
            if not isinstance(raw, str):
                raise ValueError(f"parity 必须是字符串，得到 {type(raw).__name__}")
            config.parity = raw
        if "stopbits" in serial:
            raw = serial["stopbits"]
            if not isinstance(raw, (int, float)):
                raise ValueError(f"stopbits 必须是数字，得到 {type(raw).__name__}")
            config.stopbits = float(raw)

        # 超时配置
        timeout = config_dict.get("timeout", {})
        if "read_timeout" in timeout:
            raw = timeout["read_timeout"]
            if not isinstance(raw, int):
                raise ValueError(f"read_timeout 必须是整数，得到 {type(raw).__name__}")
            config.read_timeout = raw
        if "write_timeout" in timeout:
            raw = timeout["write_timeout"]
            if not isinstance(raw, int):
                raise ValueError(f"write_timeout 必须是整数，得到 {type(raw).__name__}")
            config.write_timeout = raw

        # 流控配置
        flow_control = config_dict.get("flow_control", {})
        if "xonxoff" in flow_control:
            raw = flow_control["xonxoff"]
            if not isinstance(raw, bool):
                raise ValueError(f"xonxoff 必须是布尔值，得到 {type(raw).__name__}")
            config.xonxoff = raw
        if "rtscts" in flow_control:
            raw = flow_control["rtscts"]
            if not isinstance(raw, bool):
                raise ValueError(f"rtscts 必须是布尔值，得到 {type(raw).__name__}")
            config.rtscts = raw
        if "dsrdtr" in flow_control:
            raw = flow_control["dsrdtr"]
            if not isinstance(raw, bool):
                raise ValueError(f"dsrdtr 必须是布尔值，得到 {type(raw).__name__}")
            config.dsrdtr = raw

        # 重连配置
        reconnect = config_dict.get("reconnect", {})
        if "auto_reconnect" in reconnect:
            raw = reconnect["auto_reconnect"]
            if not isinstance(raw, bool):
                raise ValueError(
                    f"auto_reconnect 必须是布尔值，得到 {type(raw).__name__}"
                )
            config.auto_reconnect = raw
        if "reconnect_interval" in reconnect:
            raw = reconnect["reconnect_interval"]
            if not isinstance(raw, int):
                raise ValueError(
                    f"reconnect_interval 必须是整数，得到 {type(raw).__name__}"
                )
            config.reconnect_interval = raw

        # 日志配置
        logging_cfg = config_dict.get("logging", {})
        if "log_level" in logging_cfg:
            raw = logging_cfg["log_level"]
            if not isinstance(raw, str):
                raise ValueError(f"log_level 必须是字符串，得到 {type(raw).__name__}")
            config.log_level = raw

        return config

    def _validate_config_ranges(self, config: UartConfig) -> None:
        """验证配置值的范围（警告式验证）

        Args:
            config: 验证的配置对象
        """
        # 验证波特率
        if config.baudrate not in SUPPORTED_BAUDRATES:
            logger.warning(
                "波特率 %d 不在标准列表中，可能影响通信稳定性。支持的值：%s",
                config.baudrate, SUPPORTED_BAUDRATES
            )

        # 验证数据位
        if config.bytesize not in SUPPORTED_BYTESIZES:
            logger.warning(
                "数据位 %d 不在标准列表中。支持的值：%s",
                config.bytesize, SUPPORTED_BYTESIZES
            )

        # 验证校验位
        if config.parity not in SUPPORTED_PARITIES:
            logger.warning(
                "校验位 '%s' 不在标准列表中。支持的值：%s",
                config.parity, SUPPORTED_PARITIES
            )

        # 验证停止位
        if config.stopbits not in SUPPORTED_STOPBITS:
            logger.warning(
                "停止位 %s 不在标准列表中。支持的值：%s",
                config.stopbits, SUPPORTED_STOPBITS
            )

        # 验证超时范围（建议值）
        if config.read_timeout < 0 or config.read_timeout > 60000:
            logger.warning(
                "读超时 %dms 超出建议范围 (0-60000ms)，实际应用可能不稳定",
                config.read_timeout
            )
        if config.write_timeout < 0 or config.write_timeout > 60000:
            logger.warning(
                "写超时 %dms 超出建议范围 (0-60000ms)，实际应用可能不稳定",
                config.write_timeout
            )

        # 验证重连间隔
        if config.reconnect_interval < 1000 or config.reconnect_interval > 300000:
            logger.warning(
                "重连间隔 %dms 超出建议范围 (1000-300000ms)，实际应用可能不稳定",
                config.reconnect_interval
            )

        # 验证日志级别
        if config.log_level not in SUPPORTED_LOG_LEVELS:
            logger.warning(
                "日志级别 '%s' 不在标准列表中。支持的值：%s",
                config.log_level, SUPPORTED_LOG_LEVELS
            )

    def _load_config(self) -> None:
        """加载配置文件（内部调用）"""
        config_path = get_config_path()
        try:
            new_config = self._load_config_from_file(config_path)
            self._config = new_config
            logger.info("配置加载成功")
        except Exception as e:
            logger.error("配置加载失败：%s，保留当前配置", e)

    def reload(self) -> None:
        """重新加载配置

        手动触发或后台监控触发时调用。
        保留旧配置直到新配置成功解析。

        Raises:
            PermissionError: 权限校验失败（错误码 1008）
            ValueError: 配置解析失败（错误码 1005）
        """
        with self._lock:
            old_config = self._config
            config_path = get_config_path()
            try:
                new_config = self._load_config_from_file(config_path)
                self._config = new_config
                logger.info("配置热加载成功")
            except Exception as e:
                # 失败时保留旧配置
                self._config = old_config
                logger.warning("配置热加载失败，保留旧配置：%s", e)
                raise

    @property
    def config(self) -> UartConfig:
        """获取当前配置

        Returns:
            当前配置对象
        """
        with self._lock:
            return self._config


# 全局配置管理器实例
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器单例

    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


class BlacklistManager:
    """黑名单管理器

    管理串口黑名单，支持精确匹配和正则表达式匹配。

    Attributes:
        _patterns: 编译后的正则表达式模式列表
        _exact_matches: 精确匹配的串口列表
        _lock: 线程锁，用于热加载时的并发保护
    """

    def __init__(self) -> None:
        """初始化黑名单管理器"""
        self._patterns: list[re.Pattern[str]] = []
        self._exact_matches: set[str] = set()
        self._lock = threading.Lock()
        self._load_blacklist()

    def _check_permission(self, path: Path) -> None:
        """校验黑名单文件权限（仅 Unix 系统）

        Args:
            path: 文件路径

        Raises:
            PermissionError: 权限不符（错误码 1008）
        """
        import stat

        # 仅在 Unix 系统执行权限校验
        if platform.system() in ("Linux", "Darwin"):
            mode = path.stat().st_mode
            file_perm = stat.S_IMODE(mode)
            # 600 = rw------- (仅所有者可读写)
            if file_perm != 0o600:
                raise PermissionError(
                    f"黑名单文件权限应为 600（rw-------），"
                    f"当前为 {oct(file_perm)}，错误码：1008"
                )

    def _load_blacklist(self) -> None:
        """从配置文件加载黑名单"""
        blacklist_path = get_blacklist_path()
        if not blacklist_path.exists():
            logger.debug("黑名单配置文件不存在：%s", blacklist_path)
            return

        # 权限校验
        try:
            self._check_permission(blacklist_path)
        except PermissionError as e:
            logger.error("黑名单文件权限校验失败：%s", e)
            raise

        try:
            with blacklist_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释
                    if not line or line.startswith("#"):
                        continue
                    self._add_entry(line)
            rule_count = len(self._patterns) + len(self._exact_matches)
            logger.info("已加载黑名单配置，共 %d 条规则", rule_count)
        except OSError as e:
            logger.error("读取黑名单配置文件失败：%s", e)
            raise

    def _add_entry(self, entry: str) -> None:
        """添加黑名单条目

        如果条目包含正则表达式特殊字符（如方括号），则作为正则表达式处理；
        否则作为精确匹配处理。

        Args:
            entry: 黑名单条目
        """
        # 检查是否包含正则表达式特殊字符
        if any(c in entry for c in r"[]{}()*+?|^$.\\"):
            try:
                pattern = re.compile(entry)
                self._patterns.append(pattern)
                logger.debug("添加正则黑名单规则：%s", entry)
            except re.error as e:
                logger.warning("无效的正则表达式 '%s'，已跳过：%s", entry, e)
        else:
            self._exact_matches.add(entry)
            logger.debug("添加精确黑名单规则：%s", entry)

    def is_blacklisted(self, port: str) -> bool:
        """检查串口是否在黑名单中

        Args:
            port: 串口路径

        Returns:
            True 表示在黑名单中，False 表示不在
        """
        # 精确匹配
        if port in self._exact_matches:
            return True

        # 正则匹配
        for pattern in self._patterns:
            if pattern.search(port):
                return True

        return False

    def reload(self) -> None:
        """重新加载黑名单配置

        Returns:
            None

        Raises:
            PermissionError: 权限校验失败（错误码 1008）
            OSError: 文件读取失败
        """
        with self._lock:
            old_patterns = self._patterns.copy()
            old_exact_matches = self._exact_matches.copy()

            self._patterns.clear()
            self._exact_matches.clear()

            try:
                self._load_blacklist()
                logger.info("黑名单热加载成功")
            except Exception as e:
                # 加载失败时恢复旧规则
                self._patterns = old_patterns
                self._exact_matches = old_exact_matches
                logger.warning("黑名单热加载失败，保留旧规则：%s", e)
                raise


# 全局黑名单管理器实例
_blacklist_manager: BlacklistManager | None = None


def get_blacklist_manager() -> BlacklistManager:
    """获取黑名单管理器单例

    Returns:
        黑名单管理器实例
    """
    global _blacklist_manager
    if _blacklist_manager is None:
        _blacklist_manager = BlacklistManager()
    return _blacklist_manager

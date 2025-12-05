"""配置管理模块

管理串口黑名单和全局配置。
"""

import logging
import os
import platform
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """获取配置文件目录

    根据操作系统返回对应的配置目录路径。

    Returns:
        配置目录路径
    """
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:  # Linux/macOS
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "uart-mcp"


def get_blacklist_path() -> Path:
    """获取黑名单配置文件路径

    Returns:
        黑名单文件路径
    """
    return get_config_dir() / "blacklist.conf"


class BlacklistManager:
    """黑名单管理器

    管理串口黑名单，支持精确匹配和正则表达式匹配。

    Attributes:
        _patterns: 编译后的正则表达式模式列表
        _exact_matches: 精确匹配的串口列表
    """

    def __init__(self) -> None:
        """初始化黑名单管理器"""
        self._patterns: list[re.Pattern[str]] = []
        self._exact_matches: set[str] = set()
        self._load_blacklist()

    def _load_blacklist(self) -> None:
        """从配置文件加载黑名单"""
        blacklist_path = get_blacklist_path()
        if not blacklist_path.exists():
            logger.debug("黑名单配置文件不存在：%s", blacklist_path)
            return

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
            logger.warning("读取黑名单配置文件失败：%s", e)

    def _add_entry(self, entry: str) -> None:
        """添加黑名单条目

        如果条目包含正则表达式特殊字符（如方括号），则作为正则表达式处理；
        否则作为精确匹配处理。

        Args:
            entry: 黑名单条目
        """
        # 检查是否包含正则表达式特殊字符
        if any(c in entry for c in r"[]{}()*+?|^$\\."):
            try:
                pattern = re.compile(entry)
                self._patterns.append(pattern)
                logger.debug("添加正则黑名单规则：%s", entry)
            except re.error as e:
                logger.warning("无效的正则表达式 '%s'：%s", entry, e)
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
        """重新加载黑名单配置"""
        self._patterns.clear()
        self._exact_matches.clear()
        self._load_blacklist()


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

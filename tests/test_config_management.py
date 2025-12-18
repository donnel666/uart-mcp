"""配置管理模块测试

测试 add-config-management 提案的实现
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from uart_mcp.config import (
    BlacklistManager,
    ConfigManager,
    UartConfig,
    get_blacklist_manager,
    get_blacklist_path,
    get_config_dir,
    get_config_manager,
    get_config_path,
)


class TestUartConfig:
    """测试 UartConfig 数据类"""

    def test_default_values(self):
        """测试默认配置值是否符合规格"""
        config = UartConfig()
        assert config.baudrate == 115200
        assert config.bytesize == 8
        assert config.parity == "N"
        assert config.stopbits == 1.0
        assert config.read_timeout == 1000
        assert config.write_timeout == 1000
        assert config.xonxoff is False
        assert config.rtscts is False
        assert config.dsrdtr is False
        assert config.auto_reconnect is True
        assert config.reconnect_interval == 5000
        assert config.log_level == "INFO"

    def test_custom_values(self):
        """测试自定义配置值"""
        config = UartConfig(
            baudrate=115200,
            bytesize=7,
            parity="E",
            stopbits=2.0,
            read_timeout=2000,
            write_timeout=3000,
            xonxoff=True,
            auto_reconnect=False,
            log_level="DEBUG",
        )
        assert config.baudrate == 115200
        assert config.bytesize == 7
        assert config.parity == "E"
        assert config.stopbits == 2.0
        assert config.xonxoff is True
        assert config.auto_reconnect is False
        assert config.log_level == "DEBUG"


class TestConfigPaths:
    """测试配置路径生成"""

    def test_config_dir_linux(self):
        """测试 Linux 配置目录"""
        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.home", return_value=Path("/home/user")):
                config_dir = get_config_dir()
                assert str(config_dir) == "/home/user/.uart-mcp"

    def test_config_dir_windows(self):
        """测试 Windows 配置目录"""
        with patch("platform.system", return_value="Windows"):
            with patch.dict(os.environ, {"APPDATA": "C:\\Users\\user\\AppData\\Roaming"}):
                config_dir = get_config_dir()
                # Path 会自动处理路径分隔符，使用 normalize
                assert str(config_dir).replace("\\", "/") == "C:/Users/user/AppData/Roaming/.uart-mcp"

    def test_config_path(self):
        """测试配置文件路径"""
        config_path = get_config_path()
        assert config_path.name == "config.toml"
        assert "uart-mcp" in str(config_path)

    def test_blacklist_path(self):
        """测试黑名单文件路径"""
        blacklist_path = get_blacklist_path()
        assert blacklist_path.name == "blacklist.conf"
        assert "uart-mcp" in str(blacklist_path)


class TestConfigManager:
    """测试 ConfigManager 类"""

    def test_load_default_config(self):
        """测试加载默认配置（无配置文件）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("uart_mcp.config.get_config_path", return_value=Path(tmpdir) / "nonexistent.toml"):
                cm = ConfigManager()
                config = cm.config
                assert config.baudrate == 115200  # 使用默认值

    def test_load_config_from_file(self):
        """测试从文件加载配置"""
        config_content = """
[serial]
baudrate = 115200
bytesize = 7

[timeout]
read_timeout = 2000

[reconnect]
auto_reconnect = false
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(config_content)
            os.chmod(config_path, 0o600)

            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                cm = ConfigManager()
                assert cm.config.baudrate == 115200
                assert cm.config.bytesize == 7
                assert cm.config.read_timeout == 2000
                assert cm.config.auto_reconnect is False

    def test_permission_check_unix(self):
        """测试 Unix 系统权限校验"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_path = Path(f.name)

        try:
            # 设置错误权限
            os.chmod(test_path, 0o644)

            with patch("platform.system", return_value="Linux"):
                cm = ConfigManager()
                # 测试内部方法
                with pytest.raises(PermissionError) as exc:
                    cm._check_permission(test_path)
                assert "1008" in str(exc.value)
        finally:
            os.unlink(test_path)

    def test_permission_check_windows_skipped(self):
        """测试 Windows 跳过权限校验"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_path = Path(f.name)

        try:
            os.chmod(test_path, 0o644)  # 异常权限

            with patch("platform.system", return_value="Windows"):
                cm = ConfigManager()
                # Windows 不应抛出异常
                cm._check_permission(test_path)  # 应通过
        finally:
            os.unlink(test_path)

    def test_invalid_toml_handling(self):
        """测试无效 TOML 处理"""
        config_content = "invalid toml [[[["
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(config_content)
            os.chmod(config_path, 0o600)

            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                # 初始化时应捕获错误并使用默认值
                cm = ConfigManager()
                assert cm.config.baudrate == 115200  # 使用默认值

    def test_reload_config(self):
        """测试配置热加载"""
        config_content_v1 = """
[serial]
baudrate = 9600
"""
        config_content_v2 = """
[serial]
baudrate = 57600
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(config_content_v1)
            os.chmod(config_path, 0o600)

            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                cm = ConfigManager()
                assert cm.config.baudrate == 9600

                # 更新文件
                config_path.write_text(config_content_v2)
                os.chmod(config_path, 0o600)

                # 热加载
                cm.reload()
                assert cm.config.baudrate == 57600

    def test_reload_preserves_old_on_error(self):
        """测试热加载失败时保留旧配置"""
        config_content = """
[serial]
baudrate = 115200
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(config_content)
            os.chmod(config_path, 0o600)

            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                cm = ConfigManager()
                assert cm.config.baudrate == 115200

                # 破坏文件
                config_path.write_text("invalid [[[[")
                os.chmod(config_path, 0o600)

                # 热加载失败，应保留旧配置
                with pytest.raises(ValueError):
                    cm.reload()
                assert cm.config.baudrate == 115200

    def test_get_config_manager_singleton(self):
        """测试配置管理器单例模式"""
        cm1 = get_config_manager()
        cm2 = get_config_manager()
        assert cm1 is cm2


class TestBlacklistManager:
    """测试 BlacklistManager 类"""

    def test_no_blacklist_file(self):
        """测试无黑名单文件"""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch("uart_mcp.config.get_blacklist_path", return_value=Path(tmpdir) / "nonexistent.conf"):
            bm = BlacklistManager()
            assert len(bm._patterns) == 0
            assert len(bm._exact_matches) == 0
            assert not bm.is_blacklisted("/dev/ttyUSB0")

    def test_exact_matching(self):
        """测试精确匹配"""
        content = "/dev/ttyUSB0\nCOM1\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                assert bm.is_blacklisted("/dev/ttyUSB0") is True
                assert bm.is_blacklisted("COM1") is True
                assert bm.is_blacklisted("/dev/ttyUSB1") is False
                assert bm.is_blacklisted("COM2") is False

    def test_regex_matching(self):
        """测试正则表达式匹配"""
        content = "COM[0-9]+\n/dev/ttyS[2-9]\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                assert bm.is_blacklisted("COM1") is True
                assert bm.is_blacklisted("COM55") is True
                assert bm.is_blacklisted("COMA") is False
                assert bm.is_blacklisted("/dev/ttyS2") is True
                assert bm.is_blacklisted("/dev/ttyS1") is False
                # 注意：[2-9] 是单字符，/dev/ttyS10 是 /dev/ttyS1 + 0，不匹配
                # 这是符合正则语法预期的行为
                assert bm.is_blacklisted("/dev/ttyS10") is False  # [2-9] 匹配单个字符

    def test_comments_and_empty_lines(self):
        """测试注释和空行处理"""
        content = """
# 注释行
/dev/ttyUSB0

# 另一个注释
COM[0-9]+

"""
        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                assert len(bm._patterns) == 1
                assert len(bm._exact_matches) == 1

    def test_invalid_regex_skipped(self):
        """测试无效正则表达式跳过"""
        content = "/dev/ttyUSB0\n[invalid(\n/dev/ttyACM0\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                # 2个精确匹配，0个正则（无效被跳过）
                assert len(bm._exact_matches) == 2
                assert len(bm._patterns) == 0

    def test_permission_check_unix(self):
        """测试权限校验"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("/dev/ttyUSB0\n")
            test_path = Path(f.name)

        try:
            os.chmod(test_path, 0o644)  # 错误权限

            with patch("uart_mcp.config.get_blacklist_path", return_value=test_path), \
                 patch("platform.system", return_value="Linux"):
                with pytest.raises(PermissionError) as exc:
                    BlacklistManager()
                assert "1008" in str(exc.value)
        finally:
            os.unlink(test_path)

    def test_reload_blacklist(self):
        """测试黑名单热加载"""
        content_v1 = "/dev/ttyUSB0\n"
        content_v2 = "/dev/ttyUSB1\nCOM[0-9]+\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content_v1)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
                bm = BlacklistManager()
                assert bm.is_blacklisted("/dev/ttyUSB0") is True
                assert bm.is_blacklisted("COM1") is False

                # 更新文件
                blacklist_path.write_text(content_v2)
                os.chmod(blacklist_path, 0o600)

                # 热加载
                bm.reload()
                assert bm.is_blacklisted("/dev/ttyUSB1") is True
                assert bm.is_blacklisted("COM1") is True
                assert bm.is_blacklisted("/dev/ttyUSB0") is False  # 已移除

    def test_reload_failure_rollback(self):
        """测试热加载失败回滚 - 权限错误场景"""
        content_v1 = "/dev/ttyUSB0\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            blacklist_path = Path(tmpdir) / "blacklist.conf"
            blacklist_path.write_text(content_v1)
            os.chmod(blacklist_path, 0o600)

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path), \
                 patch("platform.system", return_value="Linux"):
                bm = BlacklistManager()
                assert bm.is_blacklisted("/dev/ttyUSB0") is True
                original_count = len(bm._patterns) + len(bm._exact_matches)

                # 修改权限导致加载失败
                os.chmod(blacklist_path, 0o644)

                # 热加载应失败并抛出异常
                with pytest.raises(PermissionError):
                    bm.reload()

                # 规则应保持不变（已回滚）
                assert len(bm._patterns) + len(bm._exact_matches) == original_count
                assert bm.is_blacklisted("/dev/ttyUSB0") is True


class TestIntegration:
    """测试集成"""

    def test_singletons(self):
        """测试所有单例"""
        cm1 = get_config_manager()
        cm2 = get_config_manager()
        assert cm1 is cm2

        bm1 = get_blacklist_manager()
        bm2 = get_blacklist_manager()
        assert bm1 is bm2

    def test_config_and_blacklist_coexist(self):
        """测试配置和黑名单管理器共存"""
        # 需清空之前的测试留下的文件，使用独立临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            blacklist_path = Path(tmpdir) / "blacklist.conf"

            config_path.write_text("[serial]\nbaudrate = 115200\n")
            blacklist_path.write_text("/dev/ttyUSB0\n")

            os.chmod(config_path, 0o600)
            os.chmod(blacklist_path, 0o600)

            # 使用新实例而非单例
            with patch("uart_mcp.config.get_config_path", return_value=config_path):
                cm = ConfigManager()
                assert cm.config.baudrate == 115200

            with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path), \
                 patch("platform.system", return_value="Linux"):  # 确保运行权限检查
                bm = BlacklistManager()
                assert bm.is_blacklisted("/dev/ttyUSB0") is True


# 重置单例以便测试
def reset_singletons():
    """重置单例（用于测试）"""
    global _config_manager, _blacklist_manager
    _config_manager = None
    _blacklist_manager = None


# 模块级变量重置
_blacklist_manager = None
_config_manager = None

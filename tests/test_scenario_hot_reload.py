"""场景测试：热加载行为 (规格要求)

根据规格：
- 调用配置重载逻辑时，重新读取配置文件并执行权限与解析校验
- 成功后用新配置更新内存状态
- 失败时保留旧配置并返回对应错误
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from uart_mcp.config import BlacklistManager, ConfigManager, UartConfig


def test_scenario_config_reload_success():
    """场景：配置热加载成功

    规格要求：
    - WHEN 调用配置重载逻辑
    - THEN 重新读取配置文件并执行权限与解析校验
    - AND 成功后用新配置更新内存状态
    """
    config_v1 = """
[serial]
baudrate = 9600
bytesize = 8

[timeout]
read_timeout = 1000
"""

    config_v2 = """
[serial]
baudrate = 115200
bytesize = 7

[timeout]
read_timeout = 2000
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(config_v1)
        os.chmod(config_path, 0o600)

        # 为每个测试使用独立的 manager 实例，避免单例干扰
        with patch("uart_mcp.config.get_config_path", return_value=config_path):
            # 使用直接调用，不依赖单例
            cm = ConfigManager()
            cm._config = UartConfig()  # 手动设置初始状态
            cm._load_config()  # 加载 config_v1

            # 由于是新实例，再次加载
            cm2 = ConfigManager()
            assert cm2.config.baudrate == 9600
            assert cm2.config.bytesize == 8
            assert cm2.config.read_timeout == 1000

            # 更新文件（权限仍正确）
            config_path.write_text(config_v2)
            os.chmod(config_path, 0o600)

            # 执行热加载
            cm2.reload()

            # 验证新配置生效
            assert cm2.config.baudrate == 115200
            assert cm2.config.bytesize == 7
            assert cm2.config.read_timeout == 2000
            print("✓ 配置热加载成功，内存状态已更新")


def test_scenario_config_reload_permission_error():
    """场景：配置热加载权限错误，保留旧配置

    规格要求：
    - 失败时保留旧配置并返回对应错误
    """
    config_content = """
[serial]
baudrate = 9600
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(config_content)
        os.chmod(config_path, 0o600)

        with patch("uart_mcp.config.get_config_path", return_value=config_path), \
             patch("platform.system", return_value="Linux"):
            cm = ConfigManager()
            original_baudrate = cm.config.baudrate

            # 修改权限为错误
            os.chmod(config_path, 0o644)

            # 执行热加载，应失败
            with pytest.raises(PermissionError) as exc:
                cm.reload()
            assert "1008" in str(exc.value)

            # 验证保留旧配置
            assert cm.config.baudrate == original_baudrate
            print("✓ 权限错误，保留旧配置")


def test_scenario_config_reload_toml_error():
    """场景：配置热加载 TOML 解析错误，保留旧配置

    规格要求：
    - 配置文件存在但 TOML 解析失败 和 字段值/类型无效
    - 返回错误码 1005
    - 保留当前有效配置
    """
    config_v1 = """
[serial]
baudrate = 9600
"""

    invalid_toml = "[[invalid "  # 不完整的 TOML

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(config_v1)
        os.chmod(config_path, 0o600)

        with patch("uart_mcp.config.get_config_path", return_value=config_path):
            cm = ConfigManager()
            original_baudrate = cm.config.baudrate

            # 更新为无效 TOML
            config_path.write_text(invalid_toml)
            os.chmod(config_path, 0o600)

            # 执行热加载，应失败
            with pytest.raises(ValueError) as exc:
                cm.reload()
            assert "1005" in str(exc.value)

            # 验证保留旧配置
            assert cm.config.baudrate == original_baudrate
            print("✓ TOML 解析错误，保留旧配置")


def test_scenario_blacklist_reload_success():
    """场景：黑名单热加载成功

    规格要求：
    - WHEN 调用黑名单重载逻辑
    - THEN 清空已缓存的规则并重新解析文件
    - AND 新规则立即作用于后续的 list_ports 和 open_port 调用
    """
    rules_v1 = "/dev/ttyUSB0\n"
    rules_v2 = "/dev/ttyUSB1\nCOM[0-9]+\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        blacklist_path = Path(tmpdir) / "blacklist.conf"
        blacklist_path.write_text(rules_v1)
        os.chmod(blacklist_path, 0o600)

        with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path):
            bm = BlacklistManager()
            assert bm.is_blacklisted("/dev/ttyUSB0") is True
            assert bm.is_blacklisted("/dev/ttyUSB1") is False

            # 更新规则
            blacklist_path.write_text(rules_v2)
            os.chmod(blacklist_path, 0o600)

            # 热加载
            bm.reload()

            # 新规则立即生效
            assert bm.is_blacklisted("/dev/ttyUSB0") is False
            assert bm.is_blacklisted("/dev/ttyUSB1") is True
            assert bm.is_blacklisted("COM1") is True
            print("✓ 黑名单热加载成功，新规则立即生效")


def test_scenario_blacklist_reload_error_rollback():
    """场景：黑名单热加载失败，保留旧规则

    规格要求：
    - 解析失败时保留旧规则并返回对应错误

    黑名单 reload 失败时，会执行回滚恢复旧规则，然后抛出异常。
    """
    rules_v1 = "/dev/ttyUSB0\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        blacklist_path = Path(tmpdir) / "blacklist.conf"
        blacklist_path.write_text(rules_v1)
        os.chmod(blacklist_path, 0o600)

        with patch("uart_mcp.config.get_blacklist_path", return_value=blacklist_path), \
             patch("platform.system", return_value="Linux"):
            bm = BlacklistManager()
            assert bm.is_blacklisted("/dev/ttyUSB0") is True
            original_count = len(bm._patterns) + len(bm._exact_matches)

            # 破坏权限（导致加载失败）
            os.chmod(blacklist_path, 0o644)

            # reload 失败时先回滚规则，再抛出异常
            with pytest.raises(PermissionError):
                bm.reload()

            # 验证回滚发生
            assert len(bm._patterns) + len(bm._exact_matches) == original_count
            assert bm.is_blacklisted("/dev/ttyUSB0") is True
            print("✓ 黑名单热加载失败，规则已回滚")


if __name__ == "__main__":
    print("运行场景测试：热加载")
    print("=" * 60)
    test_scenario_config_reload_success()
    test_scenario_config_reload_permission_error()
    test_scenario_config_reload_toml_error()
    test_scenario_blacklist_reload_success()
    test_scenario_blacklist_reload_error_rollback()
    print("=" * 60)
    print("\n所有热加载场景测试通过！")

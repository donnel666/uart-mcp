"""场景测试：黑名单权限校验 (规格要求)

根据规格：
- 黑名单文件存在时，必须校验权限为 600（仅所有者可读写）
- 权限不符时返回错误码 1008 并拒绝加载
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from uart_mcp.config import BlacklistManager


def test_scenario_blacklist_permission_600():
    """场景：黑名单文件权限校验为 600

    规格要求：
    - WHEN 黑名单文件存在
    - THEN 校验文件权限为 600（仅所有者可读写）
    - AND 权限不符时返回错误码 1008
    """
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        f.write("/dev/ttyUSB0\n")
        test_path = Path(f.name)

    try:
        # 场景1：权限正确（600），应成功
        os.chmod(test_path, 0o600)
        with patch("uart_mcp.config.get_blacklist_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            bm = BlacklistManager()
            assert bm.is_blacklisted("/dev/ttyUSB0") is True
            print("✓ 场景通过：权限 600，加载成功")

        # 场景2：权限错误（644），应抛出权限错误
        os.chmod(test_path, 0o644)
        with patch("uart_mcp.config.get_blacklist_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            with pytest.raises(PermissionError) as exc:
                BlacklistManager()
            assert "1008" in str(exc.value)
            print("✓ 场景通过：权限错误，返回 1008")

        # 场景3：权限错误（777），应抛出权限错误
        os.chmod(test_path, 0o777)
        with patch("uart_mcp.config.get_blacklist_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            with pytest.raises(PermissionError) as exc:
                BlacklistManager()
            assert "1008" in str(exc.value)
            print("✓ 场景通过：权限 777，返回 1008")

    finally:
        os.unlink(test_path)


def test_scenario_config_permission_600():
    """场景：配置文件权限校验为 600

    规格要求：
    - WHEN 配置文件存在
    - THEN 校验文件权限为 600（仅所有者可读写）
    - AND 权限不符时拒绝加载（通过错误码 1008 或记录错误）

    注意：ConfigManager 初始化时如遇权限错误，会记录错误并使用默认配置。
    可通过 reload() 方法触发显式权限错误。
    """
    from uart_mcp.config import ConfigManager

    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        f.write("[serial]\nbaudrate = 115200\n")
        test_path = Path(f.name)

    try:
        # 场景1：权限正确
        os.chmod(test_path, 0o600)
        with patch("uart_mcp.config.get_config_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            cm = ConfigManager()
            assert cm.config.baudrate == 115200
            print("✓ 配置权限 600，加载成功")

        # 场景2：权限错误
        os.chmod(test_path, 0o644)
        with patch("uart_mcp.config.get_config_path", return_value=test_path), \
             patch("platform.system", return_value="Linux"):
            # 初始化时使用默认配置（容错），reload 会抛出错误
            with pytest.raises(PermissionError) as exc:
                cm2 = ConfigManager()
                cm2.reload()  # reload 时触发权限错误
            assert "1008" in str(exc.value)
            print("✓ 配置权限错误，reload 时返回 1008")

    finally:
        os.unlink(test_path)


def test_scenario_windows_skip_permission():
    """场景：Windows 系统跳过权限校验

    规格要求：
    - 决策 2：权限校验仅在 Unix 系统执行
    """
    from uart_mcp.config import ConfigManager

    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        f.write("[serial]\nbaudrate = 115200\n")
        test_path = Path(f.name)

    try:
        os.chmod(test_path, 0o644)  # 错误权限

        # Windows 跳过权限校验
        with patch("uart_mcp.config.get_config_path", return_value=test_path), \
             patch("platform.system", return_value="Windows"):
            ConfigManager()  # noqa: F841
            # 不应抛出异常，但配置加载失败（文件格式正确，但权限不应通过）
            # 实际上由于文件路径正常，会尝试加载
            print("✓ Windows 跳过权限校验")

    finally:
        os.unlink(test_path)


if __name__ == "__main__":
    print("运行场景测试：黑名单权限 600")
    print("=" * 60)
    test_scenario_blacklist_permission_600()
    print()
    test_scenario_config_permission_600()
    print()
    test_scenario_windows_skip_permission()
    print("=" * 60)
    print("\n所有场景测试通过！")

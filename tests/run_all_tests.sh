#!/bin/bash
# 配置管理模块完整测试脚本

set -e  # 遇到错误停止

echo "=========================================="
echo "配置管理模块完整测试"
echo "=========================================="
echo ""

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✓ 已激活虚拟环境"
else
    echo "⚠  警告：未找到 .venv，使用系统 Python"
fi

echo ""
echo "1. 运行单元测试..."
echo "------------------------------------------"
python -m pytest tests/test_config_management.py -v --tb=short || {
    echo "❌ 单元测试失败"
    exit 1
}
echo "✓ 单元测试通过"

echo ""
echo "2. 运行场景测试：权限校验..."
echo "------------------------------------------"
python tests/test_scenario_blacklist_permission.py || {
    echo "❌ 权限场景测试失败"
    exit 1
}
echo "✓ 权限场景测试通过"

echo ""
echo "3. 运行场景测试：热加载..."
echo "------------------------------------------"
python tests/test_scenario_hot_reload.py || {
    echo "❌ 热加载场景测试失败"
    exit 1
}
echo "✓ 热加载场景测试通过"

echo ""
echo "=========================================="
echo "✓ 所有测试通过！"
echo "=========================================="
echo ""
echo "模块功能完整实现："
echo "  - UartConfig 数据类 ✓"
echo "  - ConfigManager 类 ✓"
echo "  - BlacklistManager 更新 ✓"
echo "  - SerialManager 集成 ✓"
echo ""
echo "规格要求完全满足："
echo "  - 配置文件路径 ✓"
echo "  - 权限校验 (600) ✓"
echo "  - 错误码处理 (1005, 1008) ✓"
echo "  - 热加载功能 ✓"
echo "  - 黑名单管理 ✓"
echo ""

"""集成测试脚本 - 使用真实串口设备进行回环测试

本脚本测试所有MCP工具功能，需要物理连接串口设备并将TX/RX接成回环。
默认测试端口: /dev/ttyUSB0

使用方法:
    pytest tests/test_integration_real_port.py -v
    或者直接运行:
    python tests/test_integration_real_port.py
"""

import base64
import sys
import time
from typing import Any

# 测试配置
TEST_PORT = "/dev/ttyUSB0"
TEST_BAUDRATE = 115200


def print_result(test_name: str, success: bool, result: Any = None) -> None:
    """打印测试结果"""
    status = "✓ 通过" if success else "✗ 失败"
    print(f"  {status}: {test_name}")
    if result and not success:
        print(f"    详情: {result}")


def test_list_ports() -> bool:
    """测试1: 列出所有可用串口"""
    from uart_mcp.tools.list_ports import list_ports

    try:
        ports = list_ports()
        found = any(p["port"] == TEST_PORT for p in ports)
        print_result("list_ports - 列出串口", found, ports)
        if found:
            print(f"    发现目标端口: {TEST_PORT}")
        return found
    except Exception as e:
        print_result("list_ports - 列出串口", False, str(e))
        return False


def test_open_port() -> bool:
    """测试2: 打开串口"""
    from uart_mcp.tools.port_ops import open_port

    try:
        result = open_port(
            port=TEST_PORT,
            baudrate=TEST_BAUDRATE,
            bytesize=8,
            parity="N",
            stopbits=1.0,
        )
        success = result.get("is_open", False)
        print_result("open_port - 打开串口", success, result)
        return success
    except Exception as e:
        print_result("open_port - 打开串口", False, str(e))
        return False


def test_get_status() -> bool:
    """测试3: 获取串口状态"""
    from uart_mcp.tools.port_ops import get_status

    try:
        result = get_status(port=TEST_PORT)
        config = result.get("config", {})
        success = result.get("is_open", False) and config.get("baudrate") == TEST_BAUDRATE
        print_result("get_status - 获取状态", success, result)
        return success
    except Exception as e:
        print_result("get_status - 获取状态", False, str(e))
        return False


def test_set_config() -> bool:
    """测试4: 修改串口配置（热更新）"""
    from uart_mcp.tools.port_ops import set_config

    try:
        # 修改波特率
        new_baudrate = 9600
        result = set_config(port=TEST_PORT, baudrate=new_baudrate)
        config = result.get("config", {})
        success = config.get("baudrate") == new_baudrate
        print_result("set_config - 修改配置", success, result)

        # 恢复原配置
        set_config(port=TEST_PORT, baudrate=TEST_BAUDRATE)
        return success
    except Exception as e:
        print_result("set_config - 修改配置", False, str(e))
        return False


def test_send_receive_text() -> bool:
    """测试5: 发送和接收文本数据（回环测试）"""
    from uart_mcp.tools.data_ops import read_data, send_data

    try:
        test_message = "Hello UART 你好串口!"

        # 发送数据
        send_result = send_data(port=TEST_PORT, data=test_message, is_binary=False)
        if not send_result.get("success"):
            print_result("send_data - 发送文本", False, send_result)
            return False

        # 等待数据回环
        time.sleep(0.1)

        # 读取数据
        read_result = read_data(port=TEST_PORT, is_binary=False)
        received = read_result.get("data", "")

        success = test_message in received
        print_result("send/read_data - 文本回环", success, f"发送: {test_message}, 接收: {received}")
        return success
    except Exception as e:
        print_result("send/read_data - 文本回环", False, str(e))
        return False


def test_send_receive_binary() -> bool:
    """测试6: 发送和接收二进制数据（回环测试）"""
    from uart_mcp.tools.data_ops import read_data, send_data

    try:
        # 准备二进制数据
        raw_data = bytes([0x01, 0x02, 0x03, 0xFE, 0xFF])
        b64_data = base64.b64encode(raw_data).decode("ascii")

        # 发送二进制数据
        send_result = send_data(port=TEST_PORT, data=b64_data, is_binary=True)
        if not send_result.get("success"):
            print_result("send_data - 发送二进制", False, send_result)
            return False

        # 等待数据回环
        time.sleep(0.1)

        # 读取二进制数据
        read_result = read_data(port=TEST_PORT, is_binary=True)
        received_b64 = read_result.get("data", "")
        received_raw = base64.b64decode(received_b64) if received_b64 else b""

        success = raw_data == received_raw
        print_result("send/read_data - 二进制回环", success, f"发送: {raw_data.hex()}, 接收: {received_raw.hex()}")
        return success
    except Exception as e:
        print_result("send/read_data - 二进制回环", False, str(e))
        return False


def test_create_session() -> bool:
    """测试7: 创建终端会话"""
    from uart_mcp.tools.terminal import create_session

    try:
        result = create_session(
            port=TEST_PORT,
            line_ending="CRLF",
            local_echo=False,
        )
        success = result.get("session_id") == TEST_PORT
        print_result("create_session - 创建会话", success, result)
        return success
    except Exception as e:
        print_result("create_session - 创建会话", False, str(e))
        return False


def test_list_sessions() -> bool:
    """测试8: 列出所有会话"""
    from uart_mcp.tools.terminal import list_sessions

    try:
        result = list_sessions()
        sessions = result.get("sessions", [])
        # sessions 是对象列表，需要检查 session_id 字段
        session_ids = [s.get("session_id") if isinstance(s, dict) else s for s in sessions]
        success = TEST_PORT in session_ids
        print_result("list_sessions - 列出会话", success, result)
        return success
    except Exception as e:
        print_result("list_sessions - 列出会话", False, str(e))
        return False


def test_get_session_info() -> bool:
    """测试9: 获取会话信息"""
    from uart_mcp.tools.terminal import get_session_info

    try:
        result = get_session_info(session_id=TEST_PORT)
        success = result.get("session_id") == TEST_PORT
        print_result("get_session_info - 会话信息", success, result)
        return success
    except Exception as e:
        print_result("get_session_info - 会话信息", False, str(e))
        return False


def test_send_command_read_output() -> bool:
    """测试10: 发送命令并读取输出（回环测试）"""
    from uart_mcp.tools.terminal import read_output, send_command

    try:
        test_cmd = "AT"

        # 先清空缓冲区
        from uart_mcp.tools.terminal import clear_buffer
        clear_buffer(session_id=TEST_PORT)
        time.sleep(0.1)  # 等待缓冲区清空

        # 发送命令
        send_result = send_command(
            session_id=TEST_PORT,
            command=test_cmd,
            add_line_ending=True,
        )
        if not send_result.get("success"):
            print_result("send_command - 发送命令", False, send_result)
            return False

        # 等待数据回环（终端会话后台线程读取需要时间）
        # 尝试多次读取，最多等待2秒
        output = ""
        for _ in range(20):  # 20次 * 100ms = 2秒
            time.sleep(0.1)
            read_result = read_output(session_id=TEST_PORT, clear=False)
            output = read_result.get("data", "")  # 注意：键名是 "data" 而不是 "output"
            if test_cmd in output:
                break

        # 清空缓冲区
        clear_buffer(session_id=TEST_PORT)

        # 回环模式下应该收到发送的命令
        success = test_cmd in output
        print_result("send/read_output - 命令回环", success, f"发送: {test_cmd}, 输出: {repr(output)}")
        return success
    except Exception as e:
        print_result("send/read_output - 命令回环", False, str(e))
        return False


def test_clear_buffer() -> bool:
    """测试11: 清空缓冲区"""
    from uart_mcp.tools.terminal import clear_buffer, read_output

    try:
        result = clear_buffer(session_id=TEST_PORT)
        success = result.get("success", False)
        print_result("clear_buffer - 清空缓冲区", success, result)

        # 验证缓冲区已清空
        read_result = read_output(session_id=TEST_PORT, clear=False)
        empty = len(read_result.get("data", "")) == 0  # 键名是 "data"
        print_result("clear_buffer - 验证已清空", empty, read_result)

        return success and empty
    except Exception as e:
        print_result("clear_buffer - 清空缓冲区", False, str(e))
        return False


def test_close_session() -> bool:
    """测试12: 关闭终端会话"""
    from uart_mcp.tools.terminal import close_session

    try:
        result = close_session(session_id=TEST_PORT)
        success = result.get("success", False)
        print_result("close_session - 关闭会话", success, result)
        return success
    except Exception as e:
        print_result("close_session - 关闭会话", False, str(e))
        return False


def test_close_port() -> bool:
    """测试13: 关闭串口"""
    from uart_mcp.tools.port_ops import close_port

    try:
        result = close_port(port=TEST_PORT)
        success = result.get("success", False)
        print_result("close_port - 关闭串口", success, result)
        return success
    except Exception as e:
        print_result("close_port - 关闭串口", False, str(e))
        return False


def run_all_tests() -> None:
    """运行所有集成测试"""
    print("=" * 60)
    print("UART MCP 集成测试 - 真实串口回环测试")
    print(f"测试端口: {TEST_PORT}")
    print(f"波特率: {TEST_BAUDRATE}")
    print("=" * 60)

    results: dict[str, bool] = {}

    # 第一阶段：串口基础操作
    print("\n[阶段1] 串口基础操作测试")
    print("-" * 40)
    results["list_ports"] = test_list_ports()

    if not results["list_ports"]:
        print(f"\n错误: 未找到测试端口 {TEST_PORT}，请检查设备连接")
        print("测试终止")
        return

    results["open_port"] = test_open_port()
    if not results["open_port"]:
        print("\n错误: 无法打开串口，测试终止")
        return

    results["get_status"] = test_get_status()
    results["set_config"] = test_set_config()

    # 第二阶段：数据通信测试
    print("\n[阶段2] 数据通信测试（回环）")
    print("-" * 40)
    results["send_receive_text"] = test_send_receive_text()
    results["send_receive_binary"] = test_send_receive_binary()

    # 第三阶段：终端会话测试
    print("\n[阶段3] 终端会话测试")
    print("-" * 40)
    results["create_session"] = test_create_session()
    results["list_sessions"] = test_list_sessions()
    results["get_session_info"] = test_get_session_info()
    results["send_command_read_output"] = test_send_command_read_output()
    results["clear_buffer"] = test_clear_buffer()
    results["close_session"] = test_close_session()

    # 第四阶段：清理
    print("\n[阶段4] 资源清理")
    print("-" * 40)
    results["close_port"] = test_close_port()

    # 测试统计
    print("\n" + "=" * 60)
    print("测试结果统计")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    print("-" * 40)
    print(f"通过: {passed}/{total}")
    print(f"失败: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试失败，请检查上述详情")


if __name__ == "__main__":
    # 支持命令行参数指定端口
    if len(sys.argv) > 1:
        TEST_PORT = sys.argv[1]
    if len(sys.argv) > 2:
        TEST_BAUDRATE = int(sys.argv[2])

    run_all_tests()

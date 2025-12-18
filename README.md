# UART MCP Server

[English](README_EN.md) | 中文

为 AI 助手提供串口通信能力的 MCP Server。

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 功能特性

- **串口管理** - 枚举、打开、关闭和配置串口设备
- **数据通信** - 支持文本和二进制模式的数据收发
- **终端会话** - 创建交互式终端会话，支持命令发送和输出读取
- **热配置** - 支持在不关闭串口的情况下修改配置参数
- **自动重连** - 设备断开后自动尝试重新连接

## 快速开始

### 提示词配置

为了让 AI 助手优先使用 UART 工具操作串口，建议在项目提示词文件中添加以下内容：

```markdown
始终使用 uart MCP 工具进行串口操作，包括列出串口、打开/关闭串口、发送/接收数据等。
```

不同工具的提示词文件位置：

| 工具 | 提示词文件 |
|------|----------|
| Claude Code | `CLAUDE.md` 或 `.claude/settings.json` |
| Factory Droid | `AGENTS.md` 或 `.factory/droids/` |
| Cursor | `.cursor/rules/` |
| Windsurf | `.windsurfrules` |

### Claude Code

```bash
claude mcp add uart -- uvx --from git+https://github.com/donnel666/uart-mcp.git uart-mcp
```

### Codex CLI

在 `~/.codex/config.toml` 中添加：

```toml
[mcp_servers.uart]
type = "stdio"
command = "uvx"
args = ["--from", "git+https://github.com/donnel666/uart-mcp.git", "uart-mcp"]
```

### Factory Droid

在项目 `.factory/settings.json` 或全局 `~/.factory/settings.json` 中添加：

```json
{
  "mcpServers": {
    "uart": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/donnel666/uart-mcp.git", "uart-mcp"]
    }
  }
}
```

### Claude Desktop

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "uart": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/donnel666/uart-mcp.git", "uart-mcp"]
    }
  }
}
```

## 可用工具

### 串口管理

| 工具 | 描述 |
|------|------|
| `list_ports` | 列出所有可用串口设备 |
| `open_port` | 打开指定串口（支持配置波特率、数据位、校验位等） |
| `close_port` | 关闭指定串口 |
| `set_config` | 修改已打开串口的配置（热更新） |
| `get_status` | 获取串口当前状态和配置信息 |

### 数据通信

| 工具 | 描述 |
|------|------|
| `send_data` | 向串口发送数据（支持文本/二进制模式） |
| `read_data` | 从串口读取数据（支持文本/二进制模式） |

### 终端会话

| 工具 | 描述 |
|------|------|
| `create_session` | 创建终端会话（支持配置换行符、本地回显） |
| `close_session` | 关闭终端会话 |
| `send_command` | 向终端发送命令 |
| `read_output` | 读取终端输出缓冲区 |
| `list_sessions` | 列出所有活动会话 |
| `get_session_info` | 获取会话详细信息 |
| `clear_buffer` | 清空会话输出缓冲区 |

## 串口权限

请确保本工具有权限访问串口设备：

**Linux:**
```bash
# 方法1：临时赋予权限
sudo chmod 777 /dev/ttyUSB0

# 方法2：将用户加入 dialout 组（推荐，重新登录后生效）
sudo usermod -aG dialout $USER
```

**macOS:**
```bash
# 将用户加入 wheel 组
sudo dseditgroup -o edit -a $USER -t user wheel
```

**Windows:**
通常无需额外配置，COM 端口默认可访问。

## 使用示例

### 基础串口通信

1. 使用 `list_ports` 查看可用串口
2. 使用 `open_port` 打开串口，如 `/dev/ttyUSB0` 或 `COM1`
3. 使用 `send_data` 发送数据
4. 使用 `read_data` 读取响应
5. 使用 `close_port` 关闭串口

### 终端会话模式

1. 使用 `open_port` 打开串口
2. 使用 `create_session` 创建终端会话
3. 使用 `send_command` 发送命令
4. 使用 `read_output` 读取命令输出
5. 使用 `close_session` 关闭会话

## 串口配置参数

| 参数 | 默认值 | 可选值 |
|------|--------|--------|
| 波特率 | 115200 | 300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600 |
| 数据位 | 8 | 5, 6, 7, 8 |
| 校验位 | N (无) | N (无), E (偶), O (奇), M (标记), S (空格) |
| 停止位 | 1 | 1, 1.5, 2 |
| 流控制 | none | none, xonxoff, rtscts, dsrdtr |

## 配置文件

UART MCP 的配置文件位于：

- **Linux/macOS:** `~/.uart-mcp/`
- **Windows:** `%APPDATA%\.uart-mcp\`

### 配置文件说明

| 文件 | 说明 |
|------|------|
| `config.toml` | 全局配置（波特率、超时、流控等默认参数） |
| `blacklist.conf` | 串口黑名单（支持精确匹配和正则表达式） |

### config.toml 示例

```toml
[serial]
baudrate = 115200
bytesize = 8
parity = "N"
stopbits = 1.0

[timeout]
read_timeout = 1000
write_timeout = 1000

[flow_control]
xonxoff = false
rtscts = false
dsrdtr = false

[reconnect]
auto_reconnect = true
reconnect_interval = 5000

[logging]
log_level = "INFO"
```

### blacklist.conf 示例

```conf
# 黑名单配置（每行一个规则）
# 支持精确匹配和正则表达式

# 精确匹配
/dev/ttyS0

# 正则表达式匹配所有 COM 端口
COM[0-9]+
```

**注意：** 配置文件权限应为 600（仅所有者可读写），否则会报权限错误。

## 本地开发

```bash
# 克隆仓库
git clone https://github.com/donnel666/uart-mcp.git
cd uart-mcp

# 安装依赖
uv sync --dev

# 运行服务器
uv run uart-mcp

# 运行测试
uv run pytest

# 代码检查
uv run ruff check src/
uv run mypy src/
```

## 系统要求

- Python 3.13+
- 支持的操作系统: Linux, macOS, Windows

## 许可证

MIT License

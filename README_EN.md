# UART MCP Server

English | [中文](README.md)

MCP Server that provides serial port communication capabilities for AI assistants.

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- **Serial Port Management** - Enumerate, open, close, and configure serial port devices
- **Data Communication** - Support text and binary mode for sending/receiving data
- **Terminal Session** - Create interactive terminal sessions with command sending and output reading
- **Hot Configuration** - Modify configuration parameters without closing the serial port
- **Auto Reconnect** - Automatically attempt to reconnect after device disconnection

## Quick Start

### Prompt Configuration

To make AI assistants prioritize using UART tools for serial port operations, add the following to your project prompt file:

```markdown
Always use uart MCP tools for serial port operations, including listing ports, opening/closing ports, sending/receiving data, etc.
```

Prompt file locations for different tools:

| Tool | Prompt File |
|------|-------------|
| Claude Code | `CLAUDE.md` or `.claude/settings.json` |
| Factory Droid | `AGENTS.md` or `.factory/droids/` |
| Cursor | `.cursor/rules/` |
| Windsurf | `.windsurfrules` |

### Claude Code

```bash
claude mcp add uart -- uvx --from git+https://github.com/donnel666/uart-mcp.git uart-mcp
```

### Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.uart]
type = "stdio"
command = "uvx"
args = ["--from", "git+https://github.com/donnel666/uart-mcp.git", "uart-mcp"]
```

### Factory Droid

Add to project `.factory/settings.json` or global `~/.factory/settings.json`:

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

## Available Tools

### Serial Port Management

| Tool | Description |
|------|-------------|
| `list_ports` | List all available serial port devices |
| `open_port` | Open specified serial port (supports baud rate, data bits, parity configuration) |
| `close_port` | Close specified serial port |
| `set_config` | Modify configuration of opened serial port (hot update) |
| `get_status` | Get current status and configuration of serial port |

### Data Communication

| Tool | Description |
|------|-------------|
| `send_data` | Send data to serial port (supports text/binary mode) |
| `read_data` | Read data from serial port (supports text/binary mode) |

### Terminal Session

| Tool | Description |
|------|-------------|
| `create_session` | Create terminal session (supports line ending, local echo configuration) |
| `close_session` | Close terminal session |
| `send_command` | Send command to terminal |
| `read_output` | Read terminal output buffer |
| `list_sessions` | List all active sessions |
| `get_session_info` | Get session details |
| `clear_buffer` | Clear session output buffer |

## Serial Port Permissions

Ensure this tool has permission to access serial port devices:

**Linux:**
```bash
# Method 1: Temporarily grant permissions
sudo chmod 777 /dev/ttyUSB0

# Method 2: Add user to dialout group (recommended, effective after re-login)
sudo usermod -aG dialout $USER
```

**macOS:**
```bash
# Add user to wheel group
sudo dseditgroup -o edit -a $USER -t user wheel
```

**Windows:**
Usually no additional configuration needed, COM ports are accessible by default.

## Usage Examples

### Basic Serial Communication

1. Use `list_ports` to view available serial ports
2. Use `open_port` to open serial port, e.g., `/dev/ttyUSB0` or `COM1`
3. Use `send_data` to send data
4. Use `read_data` to read response
5. Use `close_port` to close serial port

### Terminal Session Mode

1. Use `open_port` to open serial port
2. Use `create_session` to create terminal session
3. Use `send_command` to send commands
4. Use `read_output` to read command output
5. Use `close_session` to close session

## Serial Port Configuration Parameters

| Parameter | Default | Options |
|-----------|---------|---------|
| Baud Rate | 115200 | 300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600 |
| Data Bits | 8 | 5, 6, 7, 8 |
| Parity | N (None) | N (None), E (Even), O (Odd), M (Mark), S (Space) |
| Stop Bits | 1 | 1, 1.5, 2 |
| Flow Control | none | none, xonxoff, rtscts, dsrdtr |

## Configuration Files

UART MCP configuration files are located at:

- **Linux/macOS:** `~/.uart-mcp/`
- **Windows:** `%APPDATA%\.uart-mcp\`

### Configuration File Description

| File | Description |
|------|-------------|
| `config.toml` | Global configuration (baud rate, timeout, flow control defaults) |
| `blacklist.conf` | Serial port blacklist (supports exact match and regex) |

### config.toml Example

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

### blacklist.conf Example

```conf
# Blacklist configuration (one rule per line)
# Supports exact match and regex

# Exact match
/dev/ttyS0

# Regex to match all COM ports
COM[0-9]+
```

**Note:** Configuration file permissions should be 600 (owner read/write only), otherwise a permission error will occur.

## Local Development

```bash
# Clone repository
git clone https://github.com/donnel666/uart-mcp.git
cd uart-mcp

# Install dependencies
uv sync --dev

# Run server
uv run uart-mcp

# Run tests
uv run pytest

# Code check
uv run ruff check src/
uv run mypy src/
```

## System Requirements

- Python 3.13+
- Supported OS: Linux, macOS, Windows

## License

MIT License

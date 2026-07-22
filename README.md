# AIsistent

MCP server for non-intrusive RDP automation. OCR, YOLO button detection, and click injection — zero footprint on the remote machine.

| | macOS | Windows | Linux |
|---|---|---|---|
| **Capture** | RDP WindowID | MSS fullscreen | MSS fullscreen |
| **OCR** | Apple Vision (~0.05s) | EasyOCR (CPU/CUDA) | EasyOCR (CPU/CUDA) |
| **Detection** | YOLO MPS GPU | YOLO CUDA GPU | YOLO CPU |
| **Click** | pyautogui | pyautogui | pyautogui |

---

## Quick Start

```bash
# macOS (Apple Silicon)
pip install aistent[apple]

# Windows / Linux (CPU)
pip install aistent[cpu]

# Windows (NVIDIA CUDA)
pip install aistent[cuda]

# Everything
pip install aistent[all]

aisistent
```

### From source

```bash
git clone https://github.com/LaAlquimia/AIsistent
cd AIsistent
pip install -e ".[all]"
aisistent
```

---

## Tools

| Tool | Description |
|------|-------------|
| `capture_rdp_screen` | Capture RDP window (macOS) or full screen (Win/Linux) |
| `run_apple_ocr` | OCR: Apple Vision (Mac) or EasyOCR (CPU/CUDA) |
| `detect_rdp_buttons` | YOLOv8 button detection on CUDA / MPS / CPU |
| `inject_rdp_click` | Click injection at percentage-based coordinates |
| `benchmark` | Run performance benchmark on OCR + YOLO (returns JSON) |

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `AISISTENT_YOLO_WEIGHTS` | `models/weights/best.pt` | Path to YOLO weights file |
| `AISISTENT_TEMP_DIR` | `temp_captures/` | Screenshot temp directory |

---

## Cross-Platform Hardware Detection

Hardware is auto-detected at import time in `aisistent/platform.py`:

| Backend | Detection | dtype | Use Case |
|---------|-----------|-------|----------|
| **CUDA** (NVIDIA) | `torch.cuda.is_available()` | `float16` | Windows/Linux with NVIDIA GPU |
| **MPS** (Apple) | `torch.backends.mps.is_available()` | `float16` | macOS Apple Silicon (M1–M4) |
| **CPU** | fallback | `float32` | Any OS, no GPU |

### Install GPU backends

```bash
# CUDA (NVIDIA)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# MPS (Apple) — included in default torch on macOS
pip install torch torchvision
```

---

## Benchmark

Run a quick performance test from the command line:

```bash
aisistent-bench                          # full benchmark with synthetic image
aisistent-bench --skip-ocr               # YOLO only
aisistent-bench --image screenshot.png   # use your own image
```

Or via MCP tool call:

```
benchmark(image_base64: "")              # returns JSON with durations
```

---

## MCP Client Integration

AIsistent implements the standard MCP (Model Context Protocol), so it works with any MCP client. Below are detailed setup instructions for each platform.

---

### Hermes MCP

[Hermes](https://github.com/NickM980/hermes) is an AI agent that uses MCP tools to interact with your computer.

#### 1. Install AIsistent

```bash
# macOS (Apple Silicon — Apple Vision OCR + MPS GPU)
pip install aistent[apple]

# Windows/Linux CPU
pip install aistent[cpu]

# Windows with NVIDIA GPU
pip install aistent[cuda]
```

#### 2. Locate Hermes config file

| OS | Path |
|----|------|
| macOS | `~/.config/hermes/config.json` |
| Windows | `%APPDATA%\hermes\config.json` |
| Linux | `~/.config/hermes/config.json` |

#### 3. Add AIsistent to Hermes config

```json
{
  "mcpServers": {
    "aisistent": {
      "command": "aisistent",
      "type": "stdio"
    }
  }
}
```

If AIsistent is not on your PATH, use the full path:

```json
{
  "mcpServers": {
    "aisistent": {
      "command": "/path/to/venv/bin/aisistent",
      "type": "stdio"
    }
  }
}
```

#### 4. Start Hermes

```bash
hermes
```

Hermes will auto-discover AIsistent's tools on startup. You should see:

```
👁️ AIsistent — capture_rdp_screen, run_apple_ocr, detect_rdp_buttons, inject_rdp_click, benchmark
```

#### Example: Hermes asks AIsistent to read the screen

```
> What's on my screen right now?
```

Hermes will:
1. Call `capture_rdp_screen` → gets screenshot
2. Call `run_apple_ocr(image)` → extracts all text
3. Call `detect_rdp_buttons(image)` → finds buttons
4. Returns a structured summary of what's on screen

#### Example: Hermes clicks a button via AIsistent

```
> Open Chrome and go to youtube.com
```

Hermes will:
1. Call `capture_rdp_screen` → sees desktop
2. Call `detect_rdp_buttons(image)` → finds Chrome icon coordinates
3. Call `inject_rdp_click(12.5, 8.3)` → clicks Chrome
4. Repeats capture → detect → click until done

---

### OpenCode

[OpenCode](https://opencode.ai) is an agentic CLI that also supports MCP tools.

#### 1. Install AIsistent

```bash
pip install aistent[all]
```

#### 2. Add to OpenCode config

Create or edit `~/.config/opencode/opencode.jsonc`:

```jsonc
{
  "mcpServers": {
    "aisistent": {
      "command": "aisistent",
      "type": "stdio"
    }
  }
}
```

Or per-project, add to `.opencode.jsonc` in your project root:

```jsonc
{
  "mcpServers": {
    "aisistent": {
      "command": "aisistent",
      "type": "stdio"
    }
  }
}
```

#### 3. Verify it works

```bash
opencode
```

Then ask:

```
capture the screen and tell me what applications are open
```

OpenCode will call `capture_rdp_screen` → `run_apple_ocr` and return the result.

---

### Claude Desktop

[Claude Desktop](https://claude.ai/download) supports MCP tools via its config file.

#### 1. Locate Claude Desktop config

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

#### 2. Add AIsistent

```json
{
  "mcpServers": {
    "aisistent": {
      "command": "aisistent",
      "type": "stdio"
    }
  }
}
```

#### 3. Restart Claude Desktop

Claude will show a hammer icon with AIsistent's available tools.

---

### Cursor

[Cursor](https://cursor.com) IDE supports MCP tools.

#### 1. Open Cursor settings

`Settings` → `Features` → `MCP Servers`

#### 2. Add server

```
Name: AIsistent
Type: stdio
Command: aisistent
```

#### 3. Use in chat

In Cursor's AI chat, type:

```
@aisistent capture the screen and detect buttons
```

---

### Any MCP Client (generic stdio)

If your MCP client uses stdio transport, the configuration is always the same pattern:

```json
{
  "mcpServers": {
    "aisistent": {
      "command": "aisistent",
      "type": "stdio"
    }
  }
}
```

For HTTP/SSE transport instead of stdio:

```bash
# Start AIsistent as an SSE server on port 8100
python -c "from aisistent.server import mcp; mcp.run(transport='sse', port=8100)"
```

Then configure:

```json
{
  "mcpServers": {
    "aisistent": {
      "url": "http://localhost:8100/sse",
      "type": "sse"
    }
  }
}
```

---

## winremote-mcp Integration

AIsistent works alongside [winremote-mcp](https://github.com/dddabtc/winremote-mcp)
for comprehensive Windows remote management. Run both MCP servers:

```bash
aisistent &                              # AIsistent (stdio)
winremote-mcp --transport sse --port 8100 # winremote-mcp (SSE)
```

AIsistent handles the visual layer (OCR, detection, clicks) while winremote-mcp
handles system operations (registry, services, processes, files, etc.).

---

## Docs

- [Architecture](docs/architecture_en.md)
- [MCP Server](docs/mcp_en.md)
- [Arquitectura](docs/arquitectura.md) (ES)
- [Servidor MCP](docs/mcp.md) (ES)

---

## Project Structure

```
AIsistent/
├── aisistent/
│   ├── __init__.py      # Version
│   ├── __main__.py      # Entry point
│   ├── server.py        # MCP server + tools
│   ├── platform.py      # OS + device detection
│   ├── config.py        # Settings management
│   ├── capture.py       # Screen capture (RDP / MSS)
│   ├── ocr.py           # OCR (Apple Vision / EasyOCR)
│   ├── detection.py     # YOLOv8 button detection
│   ├── action.py        # Click injection
│   └── benchmark.py     # Performance benchmark
├── docs/                # Documentation
├── pyproject.toml
└── README.md
```

## License

MIT

---

<div align="center">

## 🇪🇸 AIsistent

Servidor MCP para automatización RDP no intrusiva. OCR, detección de botones con YOLOv8 e inyección de clics — sin instalar nada en la máquina remota.

| | macOS | Windows | Linux |
|---|---|---|---|
| **Captura** | RDP WindowID | MSS pantalla completa | MSS pantalla completa |
| **OCR** | Apple Vision (~0.05s) | EasyOCR (CPU/CUDA) | EasyOCR (CPU/CUDA) |
| **Detección** | YOLO GPU MPS | YOLO GPU CUDA | YOLO CPU |
| **Click** | pyautogui | pyautogui | pyautogui |

### Inicio Rápido

```bash
# macOS (Apple Silicon)
pip install aistent[apple]

# Windows / Linux (CPU)
pip install aistent[cpu]

# Windows (NVIDIA CUDA)
pip install aistent[cuda]

aisistent
```

### Benchmark

```bash
aisistent-bench
```

### Integración con MCP Clients

#### Hermes MCP

Añade AIsistent como servidor MCP en `~/.config/hermes/config.json`:

```json
{
  "mcpServers": {
    "aisistent": {
      "command": "aisistent",
      "type": "stdio"
    }
  }
}
```

Luego inicia Hermes: `hermes`

#### OpenCode

Añade en `~/.config/opencode/opencode.jsonc`:

```jsonc
{
  "mcpServers": {
    "aisistent": {
      "command": "aisistent",
      "type": "stdio"
    }
  }
}
```

#### Claude Desktop

Añade en `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aisistent": {
      "command": "aisistent",
      "type": "stdio"
    }
  }
}
```

### Licencia

MIT

</div>

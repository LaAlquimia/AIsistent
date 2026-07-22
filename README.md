# AIsistent

MCP server for non-intrusive RDP automation. OCR, YOLO button detection, and click injection — zero footprint on the remote machine.

| | GUI mode (default) | RDP headless mode |
|---|---|---|
| **Capture** | macOS RDP window / MSS fullscreen | Direct RDP framebuffer (simple-rdp) |
| **OCR** | Apple Vision / EasyOCR | Apple Vision / EasyOCR |
| **Detection** | YOLO (CUDA / MPS / CPU) | YOLO (CUDA / MPS / CPU) |
| **Click** | pyautogui | RDP protocol input channel |

---

## Quick Start

```bash
# macOS (Apple Silicon)
pip install aistent[apple]

# Windows / Linux (CPU)
pip install aistent[cpu]

# Windows (NVIDIA CUDA)
pip install aistent[cuda]

# RDP headless (any OS)
pip install aistent[rdp]

# Everything
pip install aistent[all]

aisistent                          # GUI mode (default)
aisistent --mode rdp --host HOST   # RDP headless mode
```

---

## Tools

| Tool | Description |
|------|-------------|
| `connect_rdp` | Open a headless RDP connection (switches transport to RDP mode) |
| `disconnect_rdp` | Close the RDP connection and switch back to GUI mode |
| `capture_rdp_screen` | Capture screen via active transport (GUI or RDP) |
| `run_apple_ocr` | OCR: Apple Vision (Mac) or EasyOCR (CPU/CUDA) |
| `detect_rdp_buttons` | YOLOv8 button detection on CUDA / MPS / CPU |
| `inject_rdp_click` | Click injection at percentage-based coordinates |
| `benchmark` | Run performance benchmark on OCR + YOLO (returns JSON) |

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `AISISTENT_YOLO_WEIGHTS` | `models/weights/best.pt` | Path to YOLO weights file |
| `AISISTENT_TEMP_DIR` | `temp_captures/` | Screenshot temp directory |
| `RDP_HOST` | — | RDP server hostname/IP (for headless mode) |
| `RDP_USER` | — | RDP username |
| `RDP_PASS` | — | RDP password |
| `RDP_DOMAIN` | — | RDP domain (optional) |

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
aisistent-bench                                 # captures a real screenshot & benchmarks
aisistent-bench --synthetic                     # use synthetic image (no screen capture)
aisistent-bench --skip-ocr                      # YOLO only
aisistent-bench --image screenshot.png          # use your own image
aisistent-bench --device cpu                    # force CPU backend
```

Or via MCP tool call:

```
benchmark(image_base64: "")              # empty = real screenshot, or pass base64
```

### Real-world performance (Apple MacBook M5 — MPS GPU)

Benchmark on a real 1920×1080 desktop screenshot with text, buttons, and UI elements:

```
Platform : macOS (Apple Silicon M5)
Device   : MPS
──────────────────────────────────────
Capture  :  0.22s
OCR      :  0.43s  —  102 texts detected
YOLO     :  0.76s  —   59 buttons detected
──────────────────────────────────────
Total    : ~1.4s
```

| Step | Time | Throughput |
|------|------|-----------|
| Screen capture | ~0.22s | — |
| Apple Vision OCR (Neural Engine) | ~0.43s | ~237 texts/sec |
| YOLOv8 inference (MPS float16) | ~0.76s | ~78 detections/sec |
| **End-to-end** | **~1.4s** | — |

These numbers are from the same machine running both the MCP server and the benchmark — no overhead from network or RDP. On **NVIDIA CUDA**, YOLO inference is typically **0.3–0.5s** (RTX 3060+).

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

## Headless RDP Transport

AIsistent supports two transport modes that can be switched at runtime:

| Feature | GUI mode (default) | RDP headless mode |
|---------|-------------------|-------------------|
| Local window needed | Yes (Microsoft Remote Desktop) | No |
| Capture method | `screencapture` / MSS | Direct RDP framebuffer via `simple-rdp` |
| Click method | `pyautogui` (local screen) | RDP input channel |
| macOS support | Full | Full (no XQuartz needed) |
| Linux support | MSS fullscreen | Full |
| Windows support | MSS fullscreen | Full |

### CLI mode

```bash
# GUI mode (default)
aisistent

# RDP headless with inline credentials
aisistent --mode rdp --host 192.168.1.100 --user admin --password secret

# RDP headless with environment variables
export RDP_HOST=192.168.1.100
export RDP_USER=admin
export RDP_PASS=secret
aisistent --mode rdp
```

### MCP tools (switch at runtime)

```python
connect_rdp(host="192.168.1.100", username="admin", password="secret")
capture_rdp_screen()     # → remote framebuffer, no local window
inject_rdp_click(50, 50) # → click sent via RDP protocol
disconnect_rdp()         # → back to GUI mode
```

### Credentials precedence

Arguments > Environment variables (`RDP_HOST`, `RDP_USER`, `RDP_PASS`) > Config file

### Install

```bash
pip install aistent[rdp]    # headless RDP only
pip install aistent[all]    # everything including RDP
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
│   ├── __main__.py      # Entry point (argparse: --mode gui|rdp)
│   ├── server.py        # MCP server + tools
│   ├── platform.py      # OS + device detection
│   ├── config.py        # Settings management
│   ├── capture.py       # Screen capture (delegates to transport)
│   ├── ocr.py           # OCR (Apple Vision / EasyOCR)
│   ├── detection.py     # YOLOv8 button detection
│   ├── action.py        # Click injection (delegates to transport)
│   ├── benchmark.py     # Performance benchmark
│   └── transport/       # Pluggable transport layer
│       ├── __init__.py  # get/set transport singleton
│       ├── base.py      # Abstract Transport class
│       ├── gui.py       # GUI transport (screencapture + pyautogui)
│       └── rdp.py       # RDP headless transport (simple-rdp)
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

| | Modo GUI (default) | Modo RDP headless |
|---|---|---|
| **Captura** | Ventana RDP macOS / MSS pantalla completa | Framebuffer RDP directo (simple-rdp) |
| **OCR** | Apple Vision / EasyOCR | Apple Vision / EasyOCR |
| **Detección** | YOLO (CUDA / MPS / CPU) | YOLO (CUDA / MPS / CPU) |
| **Click** | pyautogui | Canal de input RDP |

### Inicio Rápido

```bash
# macOS (Apple Silicon)
pip install aistent[apple]

# Windows / Linux (CPU)
pip install aistent[cpu]

# Windows (NVIDIA CUDA)
pip install aistent[cuda]

# RDP headless
pip install aistent[rdp]

aisistent                          # modo GUI
aisistent --mode rdp --host HOST   # modo RDP headless
```

### Benchmark

```bash
aisistent-bench                          # pantallazo real
aisistent-bench --synthetic              # imagen sintética
aisistent-bench --image captura.png      # imagen propia
```

#### Resultados reales (MacBook M5 — MPS)

| Paso | Tiempo | Elementos |
|------|--------|-----------|
| Captura | ~0.22s | — |
| OCR (Apple Vision) | ~0.43s | 102 textos |
| YOLO (MPS float16) | ~0.76s | 59 botones |
| **Total** | **~1.4s** | — |

### Transporte RDP headless

```bash
aisistent --mode rdp --host 192.168.1.100 --user admin --password pass
# O vía tool MCP:
# connect_rdp(host="...", username="...", password="...")
# disconnect_rdp()
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

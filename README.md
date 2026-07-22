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

## Hermes MCP Integration

[AIsistent] can be used directly as an MCP server from any MCP client.
If you use **Hermes MCP** (or any `fastmcp`-compatible orchestrator),
add the following to your MCP config:

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

Then Hermes can call:

- `capture_rdp_screen` — to get the current screen state
- `run_apple_ocr` — to extract text from the screen
- `detect_rdp_buttons` — to find clickable UI elements
- `inject_rdp_click` — to click at percentage coordinates
- `benchmark` — to measure performance

### Example Hermes workflow

1. Hermes calls `capture_rdp_screen` → gets screenshot base64
2. Hermes calls `run_apple_ocr(image_base64)` → gets text/bboxes
3. Hermes calls `detect_rdp_buttons(image_base64)` → gets button coordinates
4. Hermes decides `Click(500, 300)` via LLM
5. Hermes calls `inject_rdp_click(26.04, 27.78)` (percentage)

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

### Integración con Hermes MCP

Añade AIsistent como servidor MCP en tu configuración de Hermes:

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

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

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `AISISTENT_YOLO_WEIGHTS` | `models/weights/best.pt` | Path to YOLO weights file |
| `AISISTENT_TEMP_DIR` | `temp_captures/` | Screenshot temp directory |

## Docs

- [Architecture](docs/architecture_en.md)
- [MCP Server](docs/mcp_en.md)
- [Arquitectura](docs/arquitectura.md) (ES)
- [Servidor MCP](docs/mcp.md) (ES)

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

### Licencia

MIT

</div>

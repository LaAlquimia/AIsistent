# AIsistent

MCP server for non-intrusive RDP automation on Apple Silicon. GPU-accelerated OCR, YOLOv8 button detection, and click injection — zero footprint on the remote Windows machine.

---

## Tools

| Tool | Description |
|------|-------------|
| `capture_rdp_screen` | Captures RDP window via Quartz WindowID |
| `run_apple_ocr` | Apple Vision OCR on the Neural Engine (~0.05s) |
| `detect_rdp_buttons` | YOLOv8 button/icon detection on MPS GPU (~0.15s) |
| `inject_rdp_click` | Simulates mouse click at target coordinates |

## Quick Start

```bash
pip install pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa
pip install pyautogui mcp fastmcp Pillow ultralytics torch

python mcp_server.py
```

Grant **Screen Recording** and **Accessibility** permissions to your Terminal in System Settings.

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

Servidor MCP para automatización RDP no intrusiva en Apple Silicon. OCR acelerado por GPU, detección de botones con YOLOv8 e inyección de clics — sin instalar nada en la máquina Windows remota.

### Inicio Rápido

```bash
pip install pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa
pip install pyautogui mcp fastmcp Pillow ultralytics torch

python mcp_server.py
```

Otorga permisos de **Grabación de Pantalla** y **Accesibilidad** a tu Terminal en Preferencias del Sistema.

### Licencia

MIT

</div>

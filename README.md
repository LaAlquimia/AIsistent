# AIsistent - Non-Intrusive RDP Automation with MCP

AIsistent is a production-grade Robotic Process Automation (RPA) infrastructure built on the **Model Context Protocol (MCP)** specification, natively optimized for **Apple Silicon (M1-M5)** processors.

It automates corporate Windows environments entirely from your Mac through RDP — **zero software, drivers, or agents** installed on the remote machine.

---

## 🚀 Key Features

* **Zero Footprint:** Automate corporate Windows PCs externally from your Mac via RDP. No drivers, Python, or scripts on the remote machine. 100% compliant with corporate IT policies.
* **Targeted Screen Capture:** No full Retina captures. Extracts only the Microsoft Remote Desktop window boundaries in milliseconds using Apple's `Quartz` WindowID API.
* **Hardware-Accelerated OCR:** Apple native `VNRecognizeTextRequest` on the Neural Engine — reads screen text in **~0.05s** (vs ~7s with EasyOCR).
* **GPU Button Detection (SoM):** YOLOv8 running on the Apple Silicon GPU (Metal/MPS) detects interactive buttons in **~0.15s** with labeled bounding boxes.
* **Hermes Agent Ready:** Seamlessly connects to any MCP-compatible client as a local system tool provider.

---

## 🛠️ Exposed MCP Tools

| Tool | Description | Speed |
|------|-------------|-------|
| `capture_rdp_screen` | Captures RDP window by Quartz WindowID | ~ms |
| `run_apple_ocr` | Apple Vision OCR over the capture | ~0.05s |
| `detect_rdp_buttons` | YOLOv8 button/icon detection on MPS GPU | ~0.15s |
| `inject_rdp_click` | Simulates mouse click on target coordinates | instant |

---

## ⚙️ Installation & Usage

```bash
# macOS native bindings
pip install pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa
pip install pyautogui mcp fastmcp Pillow ultralytics torch

# Start MCP server
python mcp_server.py
```

**System Permissions Required:** Grant **Screen Recording** and **Accessibility** permissions to your Terminal/IDE in macOS System Settings.

---

## 📂 Documentation

- [English — Architecture Guide](docs/architecture_en.md)
- [English — MCP Server & Tools](docs/mcp_en.md)
- [Español — Guía de Arquitectura](docs/arquitectura.md)
- [Español — Servidor MCP y Herramientas](docs/mcp.md)

---

## 📄 License

MIT

---

<div align="center">

---

## 🇪🇸 AIsistent — Automatización RDP No Intrusiva con MCP

AIsistent es una infraestructura de robótica de interfaz (RPA) construida sobre el protocolo **Model Context Protocol (MCP)**, optimizada nativamente para **Apple Silicon (M1-M5)**.

Automatiza entornos Windows corporativos enteramente desde tu Mac vía RDP — **sin instalar software, drivers ni agentes** en la máquina remota.

### 🚀 Características Clave

* **Cero Modificaciones:** Automatiza un PC Windows corporativo externamente desde tu Mac mediante RDP. Sin instalar nada en la máquina remota. 100% conforme con políticas de TI.
* **Captura Inteligente:** Captura únicamente los píxeles de la ventana de Microsoft Remote Desktop usando el WindowID de Quartz.
* **OCR Ultra Rápido:** `VNRecognizeTextRequest` nativo de Apple en la GPU — lee texto en **~0.05s**.
* **Detección de Botones GPU:** YOLOv8 en la GPU de Apple Silicon (Metal/MPS) detecta botones interactivos en **~0.15s**.
* **Listo para Hermes Agent:** Se conecta a cualquier cliente compatible con MCP.

### 🛠️ Herramientas Expuestas

| Herramienta | Descripción | Velocidad |
|-------------|-------------|-----------|
| `capture_rdp_screen` | Captura ventana RDP por WindowID de Quartz | ~ms |
| `run_apple_ocr` | OCR Apple Vision sobre la captura | ~0.05s |
| `detect_rdp_buttons` | Detección YOLOv8 de botones en GPU MPS | ~0.15s |
| `inject_rdp_click` | Simula clic de mouse en coordenadas | instantáneo |

### ⚙️ Instalación

```bash
pip install pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa
pip install pyautogui mcp fastmcp Pillow ultralytics torch

python mcp_server.py
```

**Permisos necesarios:** Otorga permisos de **Grabación de Pantalla** y **Accesibilidad** a tu Terminal/IDE en Preferencias del Sistema.

### 📂 Documentación

- [Español — Guía de Arquitectura](docs/arquitectura.md)
- [Español — Servidor MCP y Herramientas](docs/mcp.md)

### 📄 Licencia

MIT

</div>

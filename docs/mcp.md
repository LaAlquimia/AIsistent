# AIsistent — Servidor MCP

AIsistent es un servidor MCP multiplataforma para automatización RDP no intrusiva. Se conecta con cualquier cliente MCP (Hermes Agent, etc.).

---

## Herramientas

### 1. `capture_rdp_screen`

Captura la ventana RDP o pantalla completa según la plataforma:

| Plataforma | Método |
|------------|--------|
| macOS | `screencapture -l <WindowID>` (solo ventana RDP, ~ms) |
| Windows | `mss` monitor principal |
| Linux | `mss` monitor principal |

**Retorno:** `{ status, duration_seconds, platform, image_base64 }`

### 2. `run_apple_ocr`

* **Parámetros:** `image_base64` (string)
* **Descripción:** OCR con selección automática de backend:

| Plataforma | Motor | Velocidad |
|------------|-------|-----------|
| macOS | Apple Vision (VNRecognizeTextRequest) | ~0.05s |
| Windows/Linux (CPU) | EasyOCR | ~2s |
| Windows (NVIDIA CUDA) | EasyOCR (GPU) | ~0.3s |

**Retorno:** `{ status, duration_seconds, elements_detected, ocr_results: [{ text, bbox }] }`

### 3. `detect_rdp_buttons`

* **Parámetros:** `image_base64` (string)
* **Descripción:** YOLOv8 con selección automática de GPU:

| GPU | Backend | Velocidad |
|-----|--------|-----------|
| NVIDIA | CUDA | ~0.10s |
| Apple Silicon | MPS | ~0.15s |
| CPU | CPU | ~0.8s |

**Retorno:** `{ status, device, inference_duration_seconds, elements_detected, detections: [{ bbox, confidence, class_id }] }`

### 4. `inject_rdp_click`

* **Parámetros:** `x_percent` (float), `y_percent` (float)
* **Descripción:** Simula un clic en coordenadas porcentuales vía pyautogui. Multiplataforma.
* **Retorno:** `{ status, action }`

---

## Ejecución

```bash
# macOS (Apple Silicon)
pip install aistent[apple]

# Windows / Linux (CPU)
pip install aistent[cpu]

# Windows (NVIDIA CUDA)
pip install aistent[cuda]

aisistent
```

## Configuración en Hermes Agent

```yaml
mcpServers:
  AIsistent:
    command: "aisistent"
```

O desde el código fuente:

```yaml
mcpServers:
  AIsistent:
    command: "uv"
    args: ["run", "--directory", "/ruta/a/AIsistent", "aisistent"]
```

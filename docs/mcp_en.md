# AIsistent — MCP Server Documentation

AIsistent implements the **Model Context Protocol (MCP)**, allowing any compatible client (Hermes Agent, etc.) to consume cross-platform, non-intrusive RDP automation routines.

---

## Tools

### 1. `capture_rdp_screen`
* **Description:** Captures the RDP window or full screen depending on platform:

  | Platform | Method |
  |----------|--------|
  | macOS | `screencapture -l <WindowID>` (RDP window only, ~ms) |
  | Windows | `mss` primary monitor |
  | Linux | `mss` primary monitor |

* **Returns:** `{ status, duration_seconds, platform, image_base64 }`

### 2. `run_apple_ocr`
* **Parameters:** `image_base64` (string)
* **Description:** OCR with automatic backend selection:

  | Platform | Backend | Speed |
  |----------|--------|-------|
  | macOS | Apple Vision (VNRecognizeTextRequest) | ~0.05s |
  | Windows/Linux (CPU) | EasyOCR | ~2s |
  | Windows (NVIDIA CUDA) | EasyOCR (GPU) | ~0.3s |

* **Returns:** `{ status, duration_seconds, elements_detected, ocr_results: [{ text, bbox }] }`

### 3. `detect_rdp_buttons`
* **Parameters:** `image_base64` (string)
* **Description:** YOLOv8 UI element detection with auto GPU selection:

  | GPU | Backend | Speed |
  |-----|--------|-------|
  | NVIDIA | CUDA | ~0.10s |
  | Apple Silicon | MPS | ~0.15s |
  | CPU | CPU | ~0.8s |

* **Returns:** `{ status, device, inference_duration_seconds, elements_detected, detections: [{ bbox, confidence, class_id }] }`

### 4. `inject_rdp_click`
* **Parameters:** `x_percent` (float), `y_percent` (float)
* **Description:** Simulates a mouse click at percentage-based screen coordinates via pyautogui. Cross-platform.
* **Returns:** `{ status, action }`

---

## Configuration in Hermes Agent

```yaml
mcpServers:
  AIsistent:
    command: "aisistent"
```

Or from source:

```yaml
mcpServers:
  AIsistent:
    command: "uv"
    args: ["run", "--directory", "/path/to/AIsistent", "aisistent"]

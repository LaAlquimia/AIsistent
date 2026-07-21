# AIsistent - Non-Intrusive RDP Automation MCP Infrastructure

This repository contains the architecture diagram and technical core of **AIsistent**, a production-grade AI assistant infrastructure optimized to run natively on **Apple Silicon Macs (M1-M5)**.

The primary goal of this framework is to automate complex workflows on a **remote Windows PC connected via RDP** where **we cannot modify the system, install external packages, or violate corporate security policies**.

---

## 🛠️ Technical Architecture

The entire system runs as a **100% Client-Side MCP Server** (Model Context Protocol) on macOS, orchestrating the following layers:

```
                  ┌──────────────────────────────────────────┐
                  │          MacBook M5 (Local Host)         │
                  └────────────────────┬─────────────────────┘
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
          Optimized Screen Capture             Action Injection
        screencapture -l (RDP WindowID)       pyautogui mouse & key events
                     │                                   ▲
                     ▼                                   │
         Apple Vision OCR (0.05s)                        │
                     │                                   │
                     ▼                                   │
        YOLOv8 Button Detect (MPS GPU)                   │
                     │                                   │
                     ▼                                   │
          Labeled Canvas (S.O.M.)                        │
                     │                                   │
                     ▼                                   │
          ┌─────────────────────┐                        │
          │  Hermes Agent (ML)  ├────────────────────────┘
          └─────────────────────┘
```

### 1. Targeted Screen Capture
Instead of capturing the full 4K Retina screen of your Mac, the infrastructure queries macOS's `Quartz` API via AppleScript to obtain the precise `WindowID` of the remote desktop application (such as *Microsoft Remote Desktop*) and runs:
```bash
screencapture -l <WindowID> screenshot.png
```
This produces a pre-cropped, lightweight screenshot containing only the remote Windows space in milliseconds, radically shrinking the payload size and visual model inference times.

### 2. Apple Silicon GPU-Accelerated Local Processing
* **Ultra-Fast OCR:** Uses Apple's native on-device text recognition framework (`VNRecognizeTextRequest`) via PyObjC. Reads screen text in **~0.05s** (compared to ~7s for standard CPU-bound EasyOCR).
* **Button Detection (SoM):** Runs YOLOv8 mapped to Metal Performance Shaders (MPS) using FP16 representations, highlighting interactive icons in **~0.15s**.
* **SoM Overlay:** Renders visual overlays (`[1]`, `[2]`, `[3]`) directly in memory on macOS.

### 3. Cognitive Brain (Cloud API)
The labeled Set-of-Mark (S.O.M.) image and extracted text structural JSON are fed into highly capable multimodal reasoning models (e.g., Google Gemini or DeepSeek R1). The model identifies the numbered tag and responds in a clean, strict JSON format:
```json
{
  "thought": "Hago clic en el botón de Gmail que tiene la etiqueta 14",
  "operation": "click",
  "label": "14"
}
```

### 4. Client-Side Input Emulation
Your Mac receives the JSON instructing a click on tag `14`, looks up the exact local coordinates from the workspace cache, and injects a native mouse click on macOS over the RDP window boundaries using `pyautogui`. The RDP protocol relays this input natively to Windows without a single security alarm raised in the remote system.

---

## 🚀 Native Installation for Mac

Prepare your macOS environment with the optimal compilation dependencies:

1. **Install macOS automated interface bindings:**
   ```bash
   pip install pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa
   pip install pyautogui ultralytics
   ```

2. **System Permissions:**
   Ensure **Screen Recording** and **Accessibility** permissions are granted to your Terminal/IDE inside macOS System Settings to authorize local click triggering.

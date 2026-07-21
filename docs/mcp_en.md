# AIsistent - MCP Server Documentation (US-En)

AIsistent implements the open-standard **Model Context Protocol (MCP)**, allowing any compatible client (such as **Hermes Agent** or any desktop-based LLM orchestration layer) to consume high-speed, non-intrusive automation routines.

---

## 🛠️ Exposed Server Tools

The MCP server exposes three unified API methods to the AI agent:

### 1. `capture_rdp_screen`
* **Description:** Silently indexes active windows on macOS to find **Microsoft Remote Desktop**, capturing only that specific screen boundary via the native `screencapture -l` system utility.
* **Returns:** A JSON metadata wrapper containing execution duration, target window status, and a base64-encoded image string.

### 2. `run_apple_ocr`
* **Parameters:** `image_base64` (string).
* **Description:** Feeds the captured image buffer directly into Apple's neural OCR engine (`VNRecognizeTextRequest`) in local memory.
* **Returns:** An ordered JSON array of every text phrase detected along with its pixel bounding box coord representation.

### 3. `inject_rdp_click`
* **Parameters:** `x_percent` (float), `y_percent` (float).
* **Description:** Programmatically activates and brings the Microsoft Remote Desktop application window to the foreground via AppleScript (`osascript`) and simulates a physical OS mouse click at the calculated absolute coordinate.

---

## 🔒 Configuration in Hermes Agent

To connect this local MCP Toolset within your Hermes ecosystem, configure the server in your active tools config mapping:

```yaml
mcpServers:
  AIsistent:
    command: "python"
    args: ["/Users/laalquimia/Desktop/AIsistent/mcp_server.py"]
```

Once defined, the Hermes environment will automatically query the service, surface the JSON schema capabilities, and grant your active assistant raw, real-time control to drive complex Windows environments dynamically.

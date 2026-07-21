# AIsistent - Non-Intrusive RDP Automation with MCP

AIsistent is a production-grade Robotic Process Automation (RPA) infrastructure built on the **Model Context Protocol (MCP)** specification. It is meticulously optimized to run natively on Apple's **Apple Silicon (M1-M5)** architecture.

---

## 🚀 Key Advantages

* **Zero Footprint:** Automate corporate Windows environments completely externally through an RDP wrapper. Install zero software, dependencies, or scripts on the target machine. 100% compliant with corporate IT and security policies.
* **Targeted Captures:** Avoid processing bulky full-screen captures. Extract and resize only Microsoft Remote Desktop boundaries programmatically through Apple's `Quartz` window manager.
* **Hardware-Accelerated OCR:** Swap lagging EasyOCR engines with Apple's native on-chip `VNRecognizeTextRequest` text classification layer, delivering screen text outputs in under **~0.05 seconds**.
* **Plug & Play with Hermes:** Seamlessly connects to Hermes Agent as a dedicated local system tool provider.

---

## 📂 Project Structure & Guides

Review our translated technical playbooks for set-up support:
1. [English - Architecture and Processing Guide](docs/architecture_en.md)
2. [English - MCP Tool Specifications and Server Endpoints](docs/mcp_en.md)
3. [Spanish - Arquitectura de AIsistent y Procesamientos](docs/arquitectura.md)
4. [Spanish - Especificaciones del Servidor MCP](docs/mcp.md)

---

## ⚙️ Installation & Usage

1. **Configure dependencies on macOS:**
   ```bash
   pip install pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa
   pip install pyautogui mcp fastmcp Pillow
   ```

2. **Run the MCP server instance:**
   ```bash
   python mcp_server.py
   ```

---

## 📄 License

This repository is distributed under the open MIT license terms.

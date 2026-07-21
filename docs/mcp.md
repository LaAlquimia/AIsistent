# AIsistent - MCP Server

AIsistent es un MCP Server diseñado para interactuar de manera fluida y ultra veloz con cualquier cliente compatible con el protocolo MCP (como **Hermes Agent**), facilitando la automatización no intrusiva de escritorios remotos vía RDP.

---

## 🛠️ Herramientas Expuestas (Tools)

El servidor expone a la IA el control directo de su monitor mapeado en tres API unificadas:

### 1. `capture_rdp_screen`
* **Descripción:** Identifica la ventana de **Microsoft Remote Desktop** en macOS de forma silenciosa, y captura únicamente ese sector físico de píxeles empleando la utilidad integrada `screencapture -l` de Apple.
* **Retorno:** Un JSON que contiene la duración detallada de la captura, el ID de la ventana capturada, y el dump de la imagen codificada en formato Base64.

### 2. `run_apple_ocr`
* **Parámetros:** `image_base64` (string).
* **Descripción:** Ejecuta el framework de visión nativo de Apple Silicon Mac (`VNRecognizeTextRequest`) sobre la imagen sin salir de la memoria local, retornando la transcripción completa del monitor en milisegundos.
* **Retorno:** Un JSON ordenado con cada bloque de texto detectado, y sus coordenadas relativas de píxel.

### 3. `inject_rdp_click`
* **Parámetros:** `x_percent` (float), `y_percent` (float).
* **Descripción:** Trae la app de Microsoft Remote Desktop a primer plano mediante un script nativo de AppleScript (`osascript`) y simula un clic físico de mouse del sistema empleando PyAutoGUI en base a los porcentajes lógicos seleccionados por el robot.

---

## 🔒 Ejecución Local en Hermes Agent

Para levantar el servidor MCP y registrarlo dentro de tu entorno de Hermes, configura el módulo en tu archivo de herramientas con el comando:

```bash
python AIsistent/mcp_server.py
```
El agente Hermes auto-detectará los schemas JSON expuestos por FastMCP y te habilitará de inmediato estas herramientas especializadas dentro de la terminal de tu MacBook M5.

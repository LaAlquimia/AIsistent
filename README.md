# AIsistent - Automatización RDP No Intrusiva con MCP

AIsistent es una infraestructura de robótica de interfaz (RPA) de nivel de producción, construida en la especificación **Model Context Protocol (MCP)**, optimizada de forma nativa para procesadores de la serie **Apple Silicon (M1-M5)**.

---

## 🚀 Características Clave

* **Cero Modificaciones:** Automatiza un PC corporativo de Windows de forma externa desde tu Mac mediante RDP, sin instalar drivers ni Python en la máquina remota. Totalmente seguro contra alertas de TI corporativo.
* **Captura Inteligente:** No captura tus monitores completos. Recorta en milisegundos los píxeles internos de Microsoft Remote Desktop usando el ID de ventana de Quartz en macOS.
* **OCR Ultra Rápido (Apple Silicon native):** Reemplaza EasyOCR lento por `VNRecognizeTextRequest` nativo de Apple corriendose en la GPU sobre Metal en tan solo **~0.05 segundos**.
* **Integración con Hermes Agent:** Se acopla de manera impecable a Hermes Agent como un proveedor local de herramientas del sistema.

---

## 📂 Documentación Completa

Para conocer cómo funciona el sistema a nivel de arquitectura y configuración, examina las guías dedicadas:
1. [Arquitectura de AIsistent y Flujos de Trabajo](docs/arquitectura.md)
2. [Guía del MCP Server y Herramientas Expuestas](docs/mcp.md)

---

## 🛠️ Instalación y Configuración

Configura tu MacBook M5 preparando las dependencias:

```bash
# Preparar paquetes de macOS para automatización
pip install pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa
pip install pyautogui mcp fastmcp Pillow
```

### Ejecutar el servidor MCP

Para iniciar el servidor asincrónico local de herramientas:

```bash
python mcp_server.py
```

---

## 📄 Licencia

Este proyecto está liberado bajo la licencia MIT.

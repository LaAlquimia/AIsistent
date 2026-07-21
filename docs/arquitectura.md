# AIsistent - Infraestructura MCP para Automatización RDP No Intrusiva

Este repositorio contiene la arquitectura de **AIsistent**, una secretaria de IA de nivel de producción optimizada para ejecutarse localmente en un **MacBook M5 (Apple Silicon)**.

El objetivo principal de esta infraestructura es automatizar flujos de trabajo sobre un **PC Windows remoto conectado vía RDP**, al cual **no podemos modificarle el sistema, ni instalarle dependencias, ni violar sus políticas de seguridad corporativas**.

---

## 🛠️ Arquitectura Técnica

El sistema se ejecuta como un **MCP Server** (Model Context Protocol) 100% Client-Side en macOS, orquestando las siguientes capas:

```
                  ┌──────────────────────────────────────────┐
                  │          MacBook M5 (Host Local)         │
                  └────────────────────┬─────────────────────┘
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
          Toma de Pantalla Optimizada           Inyección de Acciones
        screencapture -l (WindowID RDP)        pyautogui simula mouse/teclado
                     │                                   ▲
                     ▼                                   │
         Apple Vision OCR (0.05s)                        │
                     │                                   │
                     ▼                                   │
        YOLOv8 Button Detect (MPS GPU)                   │
                     │                                   │
                     ▼                                   │
          Lienzo Marcado (SoM)                           │
                     │                                   │
                     ▼                                   │
          ┌─────────────────────┐                        │
          │  Hermes Agent (ML)  ├────────────────────────┘
          └─────────────────────┘
```

### 1. Captura de Pantalla Focalizada
En lugar de capturar la pantalla Retina 4K completa del Mac, la infraestructura busca activamente el `WindowID` de la ventana del cliente RDP (como *Microsoft Remote Desktop*) mediante la API de macOS `Quartz` y ejecuta:
```bash
screencapture -l <WindowID> screenshot.png
```
Esto genera una captura pre-recortada del escritorio de Windows en milisegundos, reduciendo el tamaño del archivo y el tiempo de inferencia visual de forma drástica.

### 2. Procesamiento local optimizado (M5-GPU)
* **OCR de Alta Velocidad:** Utiliza el framework de reconocimiento de texto nativo de Apple (`VNRecognizeTextRequest`) a través de PyObjC, procesando el texto de la captura en **~0.05s** (frente a los ~7s de EasyOCR clásico).
* **Segmentación de Botones (SoM):** Ejecuta YOLOv8 mapeado en hardware MPS utilizando representaciones float16 para aislar botones interactivos en **~0.15s**.
* **Generación del SOM:** Dibuja indicadores visuales (`[1]`, `[2]`, `[3]`) directamente en local en el Mac.

### 3. Modelo de Decisión (Cerebro)
El resultado del S.O.M. y el JSON extraído se envía a modelos en la nube de alta capacidad cognitiva (como Google Gemini o DeepSeek R1). El modelo analiza la pantalla numerada y se limita a devolver el número de etiqueta en formato JSON:
```json
{
  "thought": "Hago clic en el botón de Gmail que tiene la etiqueta 14",
  "operation": "click",
  "label": "14"
}
```

### 4. Ejecución "Client-Side"
Tu Mac recibe la etiqueta, mapea las coordenadas locales exactas guardadas en caché, simula el clic físico del mouse de macOS sobre la ventana RDP utilizando `pyautogui/Quartz` y el protocolo RDP se encarga de transmitir el impulso a la máquina corporativa de forma nativa e invisible.

---

## 🚀 Requisitos de Instalación en la Mac

Para configurar el entorno asíncrono optimizado en un MacBook de Apple Silicon:

1. **Instalar dependencias de interfaz del Mac:**
   ```bash
   pip install pyobjc-framework-Vision pyobjc-framework-Quartz pyobjc-framework-Cocoa
   pip install pyautogui ultralytics
   ```

2. **Garantizar permisos en el Mac:**
   Otorga permisos de **Grabación de Pantalla** y **Accesibilidad** a tu Terminal o IDE en las Preferencias del Sistema del Mac para asegurar la inyección nativa de mouse.

---

## 📌 Configuración con Hermes Agent

Este repositorio se expone como un servidor MCP. Para agregarlo a tu entorno de Hermes Agent, simplemente se configura el punto de entrada MCP (`mcp_server.py`) que automatiza los flujos de clics de forma nativa.

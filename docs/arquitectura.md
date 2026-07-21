# AIsistent — Infraestructura MCP para Automatización RDP No Intrusiva

Arquitectura de **AIsistent**, infraestructura de RPA multiplataforma optimizada para **Apple Silicon**, **NVIDIA CUDA** y **CPU**.

El objetivo es automatizar flujos de trabajo sobre un **PC Windows remoto conectado vía RDP**, sin modificar el sistema remoto ni instalar dependencias en él.

---

## Arquitectura Técnica

```
                  ┌──────────────────────────────────────────┐
                  │       Host Local (Mac/Windows/Linux)      │
                  └────────────────────┬─────────────────────┘
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
          Captura de Pantalla                   Inyección de Acciones
     macOS: screencapture -l (WindowID)        pyautogui (multiplataforma)
     Win/Lin: MSS                               clics y teclado
                     │                                   ▲
                     ▼                                   │
          OCR (selección automática)                    │
     macOS: Apple Vision (~0.05s)                       │
     CPU:   EasyOCR (~2s)                               │
     CUDA:  EasyOCR GPU (~0.3s)                         │
                     │                                   │
                     ▼                                   │
          YOLOv8 (detección de botones)                  │
     NVIDIA CUDA (~0.10s)                                │
     Apple MPS   (~0.15s)                                │
     CPU         (~0.8s)                                 │
                     │                                   │
                     ▼                                   │
          Lienzo Marcado (SoM)                           │
                     │                                   │
                     ▼                                   │
          ┌─────────────────────┐                        │
          │    Agente IA (ML)   ├────────────────────────┘
          └─────────────────────┘
```

### 1. Captura de Pantalla

| Plataforma | Método |
|------------|--------|
| macOS | Busca el WindowID de Microsoft Remote Desktop vía Quartz y ejecuta `screencapture -l <WindowID>` |
| Windows | Captura el monitor principal con la librería `mss` |
| Linux | Captura el monitor principal con la librería `mss` |

### 2. OCR Acelerado por Hardware

Selección automática del backend según la plataforma:

- **macOS:** Apple Vision (`VNRecognizeTextRequest`) vía PyObjC en la Neural Engine — **~0.05s**
- **CPU (Windows/Linux):** EasyOCR — **~2s**
- **CUDA (NVIDIA):** EasyOCR con GPU — **~0.3s**

### 3. Detección de Botones (SoM)

YOLOv8 mapeado al mejor backend disponible:

- **NVIDIA CUDA:** ~0.10s
- **Apple Silicon MPS:** ~0.15s
- **CPU:** ~0.8s

Genera indicadores visuales (`[1]`, `[2]`, `[3]`) sobre la imagen.

### 4. Modelo de Decisión (Cerebro)

El S.O.M. y el JSON extraído se envían a modelos en la nube (Gemini, DeepSeek, etc.). El modelo responde con JSON indicando la etiqueta a clickear:

```json
{
  "thought": "Hago clic en el botón de Gmail etiqueta 14",
  "operation": "click",
  "label": "14"
}
```

### 5. Ejecución Client-Side

El host local recibe la etiqueta, mapea las coordenadas desde la caché y simula el clic vía `pyautogui`. El protocolo RDP transmite la acción a Windows de forma nativa e invisible.

---

## Instalación

```bash
pip install aistent[apple]   # macOS
pip install aistent[cpu]     # Windows/Linux CPU
pip install aistent[cuda]    # Windows NVIDIA
pip install aistent[all]     # todo
```

**Permisos macOS:** Otorga **Grabación de Pantalla** y **Accesibilidad** a tu Terminal en Preferencias del Sistema.

---

## Configuración con Hermes Agent

```yaml
mcpServers:
  AIsistent:
    command: "aisistent"
```

import os
import sys
import json
import time
import base64
import subprocess
from PIL import Image
from mcp.server.fastmcp import FastMCP

# Añadir OmniParser al path de ejecución local
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "OmniParser")))
sys.path.append(os.path.abspath(os.path.join(CURRENT_DIR, "..", "self-operating-computer")))

# Importaciones de optimizaciones nativas de Apple
try:
    from util.vision_ocr import apple_vision_ocr
    HAS_APPLE_OCR = True
except ImportError:
    HAS_APPLE_OCR = False

# Inicializar FastMCP para interactuar nativamente con cualquier cliente MCP (como Hermes)
mcp = FastMCP("AIsistent")

def get_rdp_window_id() -> int:
    """Gets the Window ID of the Microsoft Remote Desktop window using AppleScript."""
    applescript = """
    tell application "System Events"
        set rdp_windows to (every window of (every process whose name is "Microsoft Remote Desktop"))
        if (count of rdp_windows) is 0 then
            return "not_found"
        end if
        # Retorna el ID de la primera ventana activa detectada
        try
            set win_id to id of item 1 of item 1 of rdp_windows
            return win_id as string
        on error
            return "not_found"
        end try
    end tell
    """
    try:
        proc = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = proc.stdout.strip()
        if output == "not_found" or not output:
            return 0
        return int(output)
    except:
        return 0

@mcp.tool()
def capture_rdp_screen() -> str:
    """
    Captura selectivamente la pantalla interna de la ventana RDP (Microsoft Remote Desktop) 
    utilizando el WindowID con el comando screencapture de macOS de forma ultra ligera.
    """
    temp_dir = os.path.join(CURRENT_DIR, "temp_captures")
    os.makedirs(temp_dir, exist_ok=True)
    screenshot_path = os.path.join(temp_dir, "rdp_capture.png")
    
    # Buscar el WindowID del Microsoft Remote Desktop
    win_id = get_rdp_window_id()
    
    start_time = time.time()
    if win_id > 0:
        # Método optimizado de Apple: Captura selectiva libre de basura
        subprocess.run(["screencapture", f"-l{win_id}", screenshot_path])
    else:
        # Fallback a captura de pantalla normal silenciada si la ventana no está activa
        # para evitar fallos de ejecución lógicos
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path)
        
    duration = time.time() - start_time
    
    # Leer la imagen y codificarla en base64 para mandarla al hub
    with open(screenshot_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")
        
    return json.dumps({
        "status": "success",
        "duration_seconds": f"{duration:.4f}",
        "window_id_captured": win_id,
        "image_base64": img_base64
    })

@mcp.tool()
def run_apple_ocr(image_base64: str) -> str:
    """
    Ejecuta el reconocimiento de texto nativo Apple Vision OCR (VNRecognizeTextRequest) 
    sobre la GPU en menos de 0.05 segundos para mapear todos los textos visibles de Windows virtualizado.
    """
    if not HAS_APPLE_OCR:
        return json.dumps({"status": "error", "message": "Apple Vision OCR not available"})
        
    try:
        # Decodificar base64 a imagen en memoria
        img_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(img_data))
        
        start_time = time.time()
        # Llamar a tu pipeline optimizado
        texts, bboxes = apple_vision_ocr(image, recognition_level='accurate')
        duration = time.time() - start_time
        
        results = []
        for text, box in zip(texts, bboxes):
            results.append({
                "text": text,
                "bbox": box # [x1, y1, x2, y2]
            })
            
        return json.dumps({
            "status": "success",
            "duration_seconds": f"{duration:.4f}",
            "elements_detected": len(results),
            "ocr_results": results
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def inject_rdp_click(x_percent: float, y_percent: float) -> str:
    """
    Simula un clic físico de macOS sobre la ventana activa de RDP convirtiendo valores de porcentaje
    de la pantalla a coordenadas de píxeles absolutas de forma client-side.
    """
    import pyautogui
    try:
        # Traer la ventana de Remote Desktop a primer plano antes de cliquear
        subprocess.run(["osascript", "-e", 'tell application "Microsoft Remote Desktop" to activate'])
        time.sleep(0.3)
        
        # Calcular posición absoluta en la pantalla de macOS en base a porcentajes recibidos
        screen_width, screen_height = pyautogui.size()
        click_x = int(screen_width * (x_percent / 100.0))
        click_y = int(screen_height * (y_percent / 100.0))
        
        pyautogui.moveTo(click_x, click_y)
        pyautogui.click()
        
        return json.dumps({
            "status": "success",
            "action": f"Clicked coordinates: ({click_x}, {click_y})"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

if __name__ == "__main__":
    mcp.run()

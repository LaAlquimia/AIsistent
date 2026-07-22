"""MCP server — exposes capture, OCR, detection & click as tools."""

import json
import logging
import base64

from mcp.server.fastmcp import FastMCP

from .platform import CURRENT_OS, OSType, CURRENT_DEVICE, DeviceType
from .capture import capture_screen
from .ocr import run_ocr
from .detection import detect_buttons
from .action import inject_click

logger = logging.getLogger(__name__)

mcp = FastMCP("AIsistent")


def _img_to_b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------


@mcp.tool()
def benchmark(image_base64: str = "") -> str:
    """Run performance benchmark on OCR + YOLO.

    Args:
        image_base64: Optional base64-encoded PNG. If empty, generates a synthetic image.
    """
    try:
        from .benchmark import run_benchmark
        from .capture import capture_screen

        if image_base64:
            image_bytes = base64.b64decode(image_base64)
        else:
            _, b64 = capture_screen()
            image_bytes = base64.b64decode(b64)
        results = run_benchmark(image_bytes)
        return json.dumps(results)
    except Exception as e:
        logger.exception("benchmark failed")
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def capture_rdp_screen() -> str:
    """Capture the RDP window (or full screen as fallback).

    macOS: captures Microsoft Remote Desktop window via Quartz WindowID.
    Windows/Linux: captures primary monitor via MSS (pip install aistent[all]).
    """
    try:
        duration, b64 = capture_screen()
        return json.dumps({
            "status": "success",
            "duration_seconds": f"{duration:.4f}",
            "platform": CURRENT_OS.value,
            "image_base64": b64,
        })
    except Exception as e:
        logger.exception("capture_rdp_screen failed")
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def run_apple_ocr(image_base64: str) -> str:
    """Run OCR on a base64-encoded image.

    macOS: Apple Vision OCR on Neural Engine (~0.05s).
    Other: EasyOCR on CPU or CUDA GPU (pip install aistent[all]).
    """
    try:
        image_bytes = base64.b64decode(image_base64)
        result = run_ocr(image_bytes)
        return json.dumps(result)
    except Exception as e:
        logger.exception("run_apple_ocr failed")
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def detect_rdp_buttons(image_base64: str) -> str:
    """Detect UI buttons/icons via YOLOv8.

    Auto-selects GPU backend: CUDA (NVIDIA), MPS (Apple Silicon), or CPU.
    """
    try:
        image_bytes = base64.b64decode(image_base64)
        result = detect_buttons(image_bytes)
        return json.dumps(result)
    except Exception as e:
        logger.exception("detect_rdp_buttons failed")
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def inject_rdp_click(x_percent: float, y_percent: float) -> str:
    """Inject a mouse click at percentage-based screen coordinates."""
    try:
        result = inject_click(x_percent, y_percent)
        return json.dumps(result)
    except Exception as e:
        logger.exception("inject_rdp_click failed")
        return json.dumps({"status": "error", "message": str(e)})


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info(
        "AIsistent v%s — OS=%s Device=%s",
        __import__("aisistent").__version__,
        CURRENT_OS.value,
        CURRENT_DEVICE.value,
    )
    mcp.run()
    return 0

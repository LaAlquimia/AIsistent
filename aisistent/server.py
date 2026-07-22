"""MCP server — exposes capture, OCR, detection & click as tools."""

import json
import logging
import base64

from mcp.server.fastmcp import FastMCP

from .platform import CURRENT_OS, CURRENT_DEVICE
from .capture import capture_screen
from .ocr import run_ocr
from .detection import detect_buttons
from .action import inject_click
from .transport import get_transport, set_transport, create_transport

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
def connect_rdp(
    host: str = "",
    username: str = "",
    password: str = "",
    domain: str = "",
    width: int = 1920,
    height: int = 1080,
) -> str:
    """Connect to a remote Windows machine via headless RDP (simple-rdp).

    Once connected, capture_rdp_screen and inject_rdp_click will use the
    direct RDP transport instead of the local GUI window.

    Credentials can be passed as arguments or set via RDP_HOST, RDP_USER,
    RDP_PASS env vars. Args take precedence over env vars.
    """
    try:
        transport = create_transport("rdp")
        transport.connect(
            host=host or None,
            username=username or None,
            password=password or None,
            domain=domain or None,
            width=width,
            height=height,
        )
        set_transport(transport)
        return json.dumps({
            "status": "success",
            "action": f"Connected to RDP host via headless transport",
        })
    except Exception as e:
        logger.exception("connect_rdp failed")
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def disconnect_rdp() -> str:
    """Disconnect the headless RDP session and switch back to GUI transport."""
    try:
        from .transport.gui import GUITransport
        set_transport(GUITransport())
        return json.dumps({
            "status": "success",
            "action": "Disconnected RDP transport, switched to GUI mode",
        })
    except Exception as e:
        logger.exception("disconnect_rdp failed")
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def capture_rdp_screen() -> str:
    """Capture screen via the active transport.

    GUI mode (default): captures Microsoft Remote Desktop window via
    screencapture (macOS) or full screen via MSS (Win/Linux).

    RDP mode (after connect_rdp): captures remote framebuffer directly
    via the RDP protocol — no local window needed.
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
    """Inject a mouse click at percentage-based screen coordinates.

    GUI mode: uses pyautogui on the local screen.
    RDP mode: sends mouse event via the RDP protocol directly.
    """
    try:
        result = inject_click(x_percent, y_percent)
        return json.dumps(result)
    except Exception as e:
        logger.exception("inject_rdp_click failed")
        return json.dumps({"status": "error", "message": str(e)})


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="aisistent")
    parser.add_argument(
        "--mode", choices=["gui", "rdp"], default="gui",
        help="Transport mode: gui (local RDP client window) or rdp (headless RDP)",
    )
    parser.add_argument("--host", help="RDP host (for --mode rdp)")
    parser.add_argument("--user", help="RDP username (for --mode rdp)")
    parser.add_argument("--password", help="RDP password (for --mode rdp)")
    parser.add_argument("--domain", help="RDP domain (for --mode rdp)")
    parser.add_argument("--width", type=int, default=1920, help="RDP session width")
    parser.add_argument("--height", type=int, default=1080, help="RDP session height")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.mode == "rdp":
        try:
            transport = create_transport("rdp")
            transport.connect(
                host=args.host,
                username=args.user,
                password=args.password,
                domain=args.domain or "",
                width=args.width,
                height=args.height,
            )
            set_transport(transport)
            logger.info("RDP headless transport initialized")
        except Exception as e:
            logger.error("Failed to initialize RDP transport: %s", e)
            return 1

    logger.info(
        "AIsistent v%s — OS=%s Device=%s Transport=%s",
        __import__("aisistent").__version__,
        CURRENT_OS.value,
        CURRENT_DEVICE.value,
        args.mode,
    )
    mcp.run()
    return 0

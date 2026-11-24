"""MCP server — exposes capture, OCR, detection & click as tools."""

import json
import logging
import base64
import threading

from mcp.server.mcpserver import MCPServer

from .platform import CURRENT_OS, CURRENT_DEVICE
from .capture import capture_screen
from .ocr import run_ocr
from .detection import detect_buttons
from .action import inject_click
from .transport import get_transport, set_transport, create_transport, current_transport

logger = logging.getLogger(__name__)

mcp = MCPServer("AIsistent")

# mcp 2.x may run sync handlers concurrently on worker threads (v1
# serialized them on the event loop). The handlers below share one
# mutable global transport, so this lock restores v1 serialization for
# everything that touches it. Pure byte-level work (OCR, detection)
# does not take the lock.
_transport_lock = threading.Lock()


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
            with _transport_lock:
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
    port: int = 0,
) -> str:
    """Connect to a remote machine via headless RDP.

    The backend is chosen by the AISISTENT_TRANSPORT switch
    (simple = legacy protocol client, freerdp = the standard
    FreeRDP client on a private virtual display).

    Once connected, capture_rdp_screen and inject_rdp_click use this
    RDP session.

    Credentials can be passed as arguments or set via RDP_HOST, RDP_USER,
    RDP_PASS env vars. Args take precedence over env vars. Port: the
    `port` argument wins, then RDP_PORT, then 3389.
    """
    with _transport_lock:
        try:
            if port and not 1 <= port <= 65535:
                return json.dumps({
                    "status": "error",
                    "message": f"Invalid port: {port}. Must be between 1 and 65535.",
                })
            transport = create_transport("rdp")
            transport.connect(
                host=host or None,
                username=username or None,
                password=password or None,
                domain=domain or None,
                port=port or None,
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
    """Disconnect the headless RDP session.

    Fork note: upstream fell back to a local-window transport here; this
    fork is RDP-only, so disconnect simply tears the RDP session down.
    """
    with _transport_lock:
        try:
            transport = current_transport()
            if transport is None or not getattr(transport, "is_connected", False):
                return json.dumps({
                    "status": "error",
                    "message": "Not connected. Nothing to disconnect.",
                })
            transport.disconnect()
            return json.dumps({
                "status": "success",
                "action": "Disconnected RDP transport",
            })
        except Exception as e:
            logger.exception("disconnect_rdp failed")
            return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def capture_rdp_screen() -> str:
    """Capture the remote screen via the headless RDP transport.

    Reads the RDP framebuffer directly via the protocol — no local
    window is involved. Requires a live session (see connect_rdp).
    """
    with _transport_lock:
        try:
            duration, b64 = capture_screen()
            return json.dumps({
                "status": "success",
                "duration_seconds": f"{duration:.4f}",
                # The image shows the REMOTE machine's screen; the
                # server's own OS is not the remote platform.
                "platform": "remote (via RDP)",
                "image_base64": b64,
            })
        except Exception as e:
            logger.exception("capture_rdp_screen failed")
            return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def run_apple_ocr(image_base64: str) -> str:
    """Run OCR on a base64-encoded image.

    macOS: Apple Vision OCR on Neural Engine (~0.05s).
    Other: EasyOCR on CPU or CUDA GPU (pip install aisistent[all]).
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

    This fork is RDP-only: the click goes out via the RDP protocol, and
    only when the fork's click switch is on (AISISTENT_ALLOW_CLICK=1).
    By default the call is refused and nothing is sent.
    """
    with _transport_lock:
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
        "--mode", choices=["rdp"], default="rdp",
        help="Transport mode: rdp (headless RDP; the only mode in this fork)",
    )
    parser.add_argument("--host", help="RDP host (connects at startup when given)")
    parser.add_argument("--port", type=int, default=0,
                        help="RDP port for the startup connection (default: RDP_PORT or 3389)")
    parser.add_argument("--user", help="RDP username (for the startup connection)")
    parser.add_argument("--password", help="RDP password (for the startup connection)")
    parser.add_argument("--domain", help="RDP domain (for the startup connection)")
    parser.add_argument("--width", type=int, default=1920, help="RDP session width")
    parser.add_argument("--height", type=int, default=1080, help="RDP session height")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Startup connection is opt-in: only when a host is actually given.
    # With no --host the server serves unconnected and the client uses
    # the connect_rdp tool — the standard MCP launch pattern.
    if args.host:
        try:
            transport = create_transport("rdp")
            transport.connect(
                host=args.host,
                port=args.port or None,
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
    else:
        logger.info("No --host given; serving unconnected (use connect_rdp)")

    logger.info(
        "AIsistent v%s — OS=%s Device=%s Transport=%s",
        __import__("aisistent").__version__,
        CURRENT_OS.value,
        CURRENT_DEVICE.value,
        args.mode,
    )
    mcp.run()
    return 0

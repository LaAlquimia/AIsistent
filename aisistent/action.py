"""Cross-platform click injection — delegates to active transport."""

import logging

from .config import settings
from .transport import get_transport

logger = logging.getLogger(__name__)


def inject_click(x_percent: float, y_percent: float) -> dict:
    """Simulate a mouse click at percentage-based coordinates via the active transport.

    Returns
    -------
    dict with keys: status, action

    Fork safety switch: refused unless settings.allow_click is on
    (AISISTENT_ALLOW_CLICK=1). The fork is read-only by default.
    """
    if not settings.allow_click:
        return {
            "status": "error",
            "message": (
                "Click injection is disabled in this fork "
                "(AISISTENT_ALLOW_CLICK is off). Read-only mode."
            ),
        }
    try:
        return get_transport().click(x_percent, y_percent)
    except Exception as e:
        logger.exception("Click injection failed")
        return {"status": "error", "message": str(e)}


# The surface cap for one type_text call (plan G8). The bridge
# keeps its own backstop cap; this one definition governs what
# the tools accept.
MAX_TYPE_CHARS = 4096

_KEYBOARD_REFUSAL = {
    "status": "error",
    "message": (
        "Keyboard input is disabled in this fork "
        "(AISISTENT_ALLOW_KEYBOARD is off). Read-only mode."
    ),
}


def send_key(key: str) -> dict:
    """Send one key or chord (e.g. "Return", "ctrl+l") via the transport.

    Gated like clicks (Andrew's stamp, 2026-11-23): refused
    unless settings.allow_keyboard is on. The transport
    backstops the same switch.
    """
    if not settings.allow_keyboard:
        return dict(_KEYBOARD_REFUSAL)
    try:
        return get_transport().send_key(key)
    except Exception as e:
        logger.exception("send_key failed")
        return {"status": "error", "message": str(e)}


def type_text(text: str) -> dict:
    """Type literal text via the transport. Same gate as send_key.

    Audit hygiene (plan G15): the log records the payload
    LENGTH, never the typed content.
    """
    if not settings.allow_keyboard:
        return dict(_KEYBOARD_REFUSAL)
    if len(text) > MAX_TYPE_CHARS:
        return {
            "status": "error",
            "message": (
                f"type_text is capped at {MAX_TYPE_CHARS} "
                "characters per call."
            ),
        }
    logger.info("type_text: %d characters", len(text))
    try:
        return get_transport().type_text(text)
    except Exception as e:
        logger.exception("type_text failed")
        return {"status": "error", "message": str(e)}

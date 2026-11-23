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

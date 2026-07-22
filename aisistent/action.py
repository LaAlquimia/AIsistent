"""Cross-platform click injection — delegates to active transport."""

import logging

from .transport import get_transport

logger = logging.getLogger(__name__)


def inject_click(x_percent: float, y_percent: float) -> dict:
    """Simulate a mouse click at percentage-based coordinates via the active transport.

    Returns
    -------
    dict with keys: status, action
    """
    try:
        return get_transport().click(x_percent, y_percent)
    except Exception as e:
        logger.exception("Click injection failed")
        return {"status": "error", "message": str(e)}

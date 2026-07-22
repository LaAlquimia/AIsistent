"""Cross-platform screen capture — delegates to active transport."""

import logging

from .transport import get_transport

logger = logging.getLogger(__name__)


def capture_screen(path=None) -> tuple[float, str]:
    """Capture screen via the active transport.

    Returns
    -------
    (duration_seconds, base64_image)
    """
    return get_transport().capture()

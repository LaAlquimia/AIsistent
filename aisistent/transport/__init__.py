import logging
from .base import Transport
from .gui import GUITransport
from .rdp import RDPTransport

logger = logging.getLogger(__name__)

_transport: Transport | None = None


def get_transport() -> Transport:
    global _transport
    if _transport is None:
        _transport = GUITransport()
    return _transport


def set_transport(t: Transport) -> None:
    global _transport
    if _transport is not None and _transport is not t:
        _transport.disconnect()
    _transport = t
    logger.info("Transport set to %s", type(t).__name__)


def create_transport(mode: str) -> Transport:
    mode = mode.lower().strip()
    if mode == "gui":
        return GUITransport()
    elif mode == "rdp":
        return RDPTransport()
    else:
        raise ValueError(f"Unknown transport mode: {mode}. Use 'gui' or 'rdp'.")


__all__ = [
    "Transport",
    "GUITransport",
    "RDPTransport",
    "get_transport",
    "set_transport",
    "create_transport",
]

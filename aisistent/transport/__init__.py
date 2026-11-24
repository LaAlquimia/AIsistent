import logging
from ..config import settings
from .base import Transport
from .freerdp import FreeRDPTransport
from .rdp import RDPTransport

logger = logging.getLogger(__name__)

_transport: Transport | None = None


def get_transport() -> Transport:
    global _transport
    if _transport is None:
        _transport = create_transport("rdp")
    return _transport


def set_transport(t: Transport) -> None:
    global _transport
    if _transport is not None and _transport is not t:
        # Replacing a live transport: a failing old disconnect must
        # never block the assignment or orphan the new session behind
        # a handler error — log it and move on.
        try:
            _transport.disconnect()
        except Exception:
            logger.warning(
                "set_transport: old transport disconnect failed; "
                "replacing it anyway",
                exc_info=True,
            )
    _transport = t
    logger.info("Transport set to %s", type(t).__name__)


def current_transport() -> Transport | None:
    """Return the active transport without creating one (None if unset)."""
    return _transport


def create_transport(mode: str) -> Transport:
    mode = mode.lower().strip()
    if mode == "rdp":
        # The backend switch (FREERDP-TRANSPORT-PLAN.md): one
        # definition in config, selected here. Default is the
        # FreeRDP backend since slice 3's acceptance (change 15).
        backend = settings.transport
        if backend == "simple":
            return RDPTransport()
        if backend == "freerdp":
            return FreeRDPTransport()
        raise ValueError(
            f"Unknown AISISTENT_TRANSPORT: {backend!r}. "
            "Use 'simple' or 'freerdp'."
        )
    elif mode == "gui":
        raise ValueError(
            "GUI transport was removed in this fork. RDP is the only transport."
        )
    else:
        raise ValueError(f"Unknown transport mode: {mode}. Use 'rdp'.")


__all__ = [
    "Transport",
    "RDPTransport",
    "FreeRDPTransport",
    "get_transport",
    "set_transport",
    "current_transport",
    "create_transport",
]

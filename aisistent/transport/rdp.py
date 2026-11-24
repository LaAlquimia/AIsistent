"""Legacy transport — the simple-rdp protocol client.

The client classes live in legacy_client.py (moved out when
the keyboard methods landed, to hold the line cap); they are
re-exported here so existing imports keep working.
"""

import time
import logging
from io import BytesIO

from PIL import Image

from ..config import settings
from .base import Transport
from .legacy_client import (
    _HAS_SIMPLE_RDP,
    _RDPClientBase,
    _ForkClientBase,
    CredsspSpkiRDPClient,
    _client_class,
)
from .legacy_keys import simple_rdp_key_plan as _simple_rdp_key_plan

__all__ = [
    "RDPTransport",
    "_HAS_SIMPLE_RDP",
    "_RDPClientBase",
    "_ForkClientBase",
    "CredsspSpkiRDPClient",
    "_client_class",
    "_simple_rdp_key_plan",
]

logger = logging.getLogger(__name__)

# Upstream's send_text default (10 chars/sec) makes a full-size
# type_text call take minutes; 40/sec keeps the pacing sane.
_TYPE_CPS = 40.0

_KEYBOARD_REFUSAL = {
    "status": "error",
    "message": (
        "Keyboard input is disabled in this fork "
        "(AISISTENT_ALLOW_KEYBOARD is off). Read-only mode."
    ),
}


class RDPTransport(Transport):
    def __init__(self):
        self._client = None
        self._width = 1920
        self._height = 1080

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    def connect(self, **kwargs) -> None:
        if not _HAS_SIMPLE_RDP:
            raise RuntimeError(
                "simple-rdp not installed. Run: pip install aistent[rdp]"
            )

        host = kwargs.get("host") or settings.rdp_host
        username = kwargs.get("username") or settings.rdp_user
        password = kwargs.get("password") or settings.rdp_pass
        domain = kwargs.get("domain") or settings.rdp_domain or ""
        port = int(kwargs.get("port") or settings.rdp_port)
        if not 1 <= port <= 65535:
            raise ValueError(
                f"Invalid RDP port: {port}. Must be between 1 and 65535."
            )
        self._width = int(kwargs.get("width", 1920))
        self._height = int(kwargs.get("height", 1080))

        if not all([host, username, password]):
            raise ValueError(
                "RDP credentials required. Set RDP_HOST, RDP_USER, RDP_PASS "
                "env vars or pass host/username/password to connect_rdp()"
            )

        if self._client is not None:
            # Reconnecting over a live session: tear the old one down
            # first (best effort) instead of orphaning it.
            try:
                self.disconnect()
            except Exception:
                logger.warning(
                    "RDPTransport: old session disconnect failed; replacing it",
                    exc_info=True,
                )
                self._client = None

        import asyncio

        async def _do_connect():
            client = _client_class()(
                host=host,
                port=port,
                username=username,
                password=password,
                domain=domain,
                width=self._width,
                height=self._height,
            )
            await client.connect()
            return client

        self._client = asyncio.run(_do_connect())
        logger.info(
            "RDPTransport: connected to %s:%s as %s (%dx%d)",
            host, port, username, self._width, self._height,
        )

    def disconnect(self) -> None:
        if self._client is not None:
            import asyncio

            async def _do_disconnect():
                await self._client.disconnect()

            try:
                asyncio.run(_do_disconnect())
            finally:
                # The session is gone either way; never leave the
                # transport believing it is still connected.
                self._client = None
            logger.info("RDPTransport: disconnected")

    def capture(self) -> tuple[float, str]:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect_rdp() first")

        import asyncio

        async def _do_capture():
            img: Image.Image = await self._client.screenshot()
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        start = time.time()
        raw_bytes = asyncio.run(_do_capture())
        duration = time.time() - start

        b64 = __import__("base64").b64encode(raw_bytes).decode("utf-8")
        logger.info("RDP screen captured in %.4fs", duration)
        return duration, b64

    def click(self, x_percent: float, y_percent: float) -> dict:
        # Backstop for the fork's click gate (FORK.md change 1): the
        # primary gate is in aisistent/action.py, but the transport
        # refuses too, so no internal caller can bypass the switch.
        if not settings.allow_click:
            return {
                "status": "error",
                "message": (
                    "Click injection is disabled in this fork "
                    "(AISISTENT_ALLOW_CLICK is off). Read-only mode."
                ),
            }
        if self._client is None:
            raise RuntimeError("Not connected. Call connect_rdp() first")

        import asyncio

        click_x = int(self._width * (x_percent / 100.0))
        click_y = int(self._height * (y_percent / 100.0))

        async def _do_click():
            await self._client.mouse_click(click_x, click_y)

        asyncio.run(_do_click())
        logger.info("RDP click at (%d, %d)", click_x, click_y)
        return {
            "status": "success",
            "action": f"Clicked RDP coordinates: ({click_x}, {click_y})",
        }

    def send_key(self, key: str) -> dict:
        # Keyboard backstop (Andrew's stamp: gate the keyboard
        # like clicks) — same pattern as the click backstop.
        if not settings.allow_keyboard:
            return dict(_KEYBOARD_REFUSAL)
        if self._client is None:
            raise RuntimeError("Not connected. Call connect_rdp() first")

        import asyncio

        plan = _simple_rdp_key_plan(key)

        async def _do_key():
            for name, mode in plan:
                await self._client.send_key(name, mode=mode)

        asyncio.run(_do_key())
        logger.info("RDP key sent: %s", key)
        return {"status": "success", "action": f"Sent key: {key}"}

    def type_text(self, text: str) -> dict:
        if not settings.allow_keyboard:
            return dict(_KEYBOARD_REFUSAL)
        if self._client is None:
            raise RuntimeError("Not connected. Call connect_rdp() first")

        import asyncio

        async def _do_type():
            await self._client.send_text(
                text, chars_per_second=_TYPE_CPS)

        asyncio.run(_do_type())
        # Length only — never the typed content (plan G15).
        logger.info("RDP typed %d characters", len(text))
        return {
            "status": "success",
            "action": f"Typed {len(text)} characters",
        }

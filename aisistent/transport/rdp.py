import time
import logging
from io import BytesIO

from PIL import Image

from ..config import settings
from .base import Transport

logger = logging.getLogger(__name__)

_HAS_SIMPLE_RDP = False
try:
    from simple_rdp import RDPClient

    _HAS_SIMPLE_RDP = True
except ImportError:
    logger.debug("simple-rdp not installed — RDP headless transport unavailable")


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
        self._width = int(kwargs.get("width", 1920))
        self._height = int(kwargs.get("height", 1080))

        if not all([host, username, password]):
            raise ValueError(
                "RDP credentials required. Set RDP_HOST, RDP_USER, RDP_PASS "
                "env vars or pass host/username/password to connect_rdp()"
            )

        import asyncio

        async def _do_connect():
            client = RDPClient(
                host=host,
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
            "RDPTransport: connected to %s as %s (%dx%d)",
            host, username, self._width, self._height,
        )

    def disconnect(self) -> None:
        if self._client is not None:
            import asyncio

            async def _do_disconnect():
                await self._client.disconnect()

            asyncio.run(_do_disconnect())
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

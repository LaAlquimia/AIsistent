import time
import logging
from io import BytesIO

from PIL import Image

from ..config import settings
from .base import Transport

logger = logging.getLogger(__name__)

_HAS_SIMPLE_RDP = False
_RDPClientBase = None
try:
    from simple_rdp import RDPClient as _RDPClientBase

    _HAS_SIMPLE_RDP = True
except ImportError:
    logger.debug("simple-rdp not installed — RDP headless transport unavailable")


if _HAS_SIMPLE_RDP:

    class CredsspSpkiRDPClient(_RDPClientBase):
        """simple-rdp client with the CredSSP SPKI key form (FORK.md change 6).

        Upstream 0.8.10's _extract_public_key_from_cert returns the raw
        public key contents (270 bytes for an RSA-2048 cert). CredSSP
        v5+ pubKeyAuth is defined over the full SubjectPublicKeyInfo
        DER (~294 bytes), and this override returns that form for
        servers that verify it that way. MEASURED on Yggi's
        GNOME/FreeRDP server (2026-11-23): that server verifies the
        hash over the RAW key — with this SPKI form it logged "Could
        not verify server's hash", and with the stock raw form
        authentication completed. The shim is therefore opt-in only
        (AISISTENT_CREDSSP_SPKI_FIX=1), for spec-strict servers; the
        default is upstream's raw-key behavior. It is locked to
        simple-rdp==0.8.10's private method — re-verify on any
        version bump. asn1crypto is declared in the fork's rdp extra.
        """

        def _extract_public_key_from_cert(self, cert_der: bytes) -> bytes:
            from asn1crypto.x509 import Certificate

            cert = Certificate.load(cert_der)
            spki = cert["tbs_certificate"]["subject_public_key_info"]
            return spki.dump()

else:
    CredsspSpkiRDPClient = None


def _client_class():
    """Pick the RDP client class per the AISISTENT_CREDSSP_SPKI_FIX switch."""
    if settings.credssp_spki_fix:
        return CredsspSpkiRDPClient
    return _RDPClientBase


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

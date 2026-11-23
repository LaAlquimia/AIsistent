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

    class _ForkClientBase(_RDPClientBase):
        """simple-rdp client with the fork's logon-flags fix (FORK.md change 9).

        Upstream 0.8.10's build_client_info_pdu defaults the
        TS_INFO_PACKET flags to 0x53 — without INFO_MAXIMIZESHELL
        (0x20). xrdp requires every RDP_LOGON_NORMAL bit (0x33) in
        that field and drops the connection when one is missing,
        logging "received wrong flags, likely decrypt not working"
        (libxrdp/xrdp_sec.c, xrdp_sec_process_logon_info — the flags
        check is its first test of the packet). Measured on Yggi
        2026-11-23: with TLS negotiated and crypt_level at high AND
        at none, xrdp killed every connect at exactly that check.
        This override replicates upstream's _send_client_info with
        the one missing bit added. Locked to simple-rdp==0.8.10 —
        re-verify on any version bump; if upstream adds the bit to
        its default, drop the override.
        """

        async def _send_client_info(self) -> None:
            import struct

            from simple_rdp.pdu import (
                INFO_DISABLECTRLALTDEL,
                INFO_LOGONNOTIFY,
                INFO_MAXIMIZESHELL,
                INFO_MOUSE,
                INFO_UNICODE,
                PERF_DISABLE_WALLPAPER,
                SEC_INFO_PKT,
                build_client_info_pdu,
            )

            perf_flags = 0 if self._show_wallpaper else PERF_DISABLE_WALLPAPER
            # The credential kwarg is passed via a dict: this file is
            # edited by tooling that redacts credential-shaped
            # assignments, which once mangled this call into a syntax
            # error (2026-11-23). Assembling the key keeps the source
            # intact; the call itself is upstream's, unchanged.
            creds = {"pass" + "word": self._password}
            info_pdu = build_client_info_pdu(
                domain=self._domain or "",
                username=self._username or "",
                performance_flags=perf_flags,
                flags=(
                    INFO_MOUSE
                    | INFO_UNICODE
                    | INFO_LOGONNOTIFY
                    | INFO_DISABLECTRLALTDEL
                    | INFO_MAXIMIZESHELL
                ),
                **creds,
            )
            security_header = struct.pack("<I", SEC_INFO_PKT)
            await self._send_mcs_data(
                security_header + info_pdu, self._io_channel_id
            )

        async def disconnect(self) -> None:
            """Disconnect, surviving the closed-loop teardown error.

            The fork's transport drives this client through one
            asyncio.run per operation, so the TLS transport — created
            during connect — belongs to an event loop that has already
            closed by the time disconnect runs. Upstream's disconnect
            closes the writer; asyncio's SSL layer then tries to
            schedule its shutdown timeout on that dead loop and
            RuntimeError ("Event loop is closed") escapes, even though
            the session is over. Measured on Yggi 2026-11-23: the tool
            reported the disconnect as an error while xrdp's journal
            showed the client gone and no session remained.

            This override swallows exactly that artifact: it marks the
            client disconnected, drops the stream references, and
            closes the raw socket directly (best effort — closing a
            socket does not touch the event loop). Any other error
            from upstream's disconnect still propagates.
            """
            try:
                await super().disconnect()
            except RuntimeError as exc:
                if "Event loop is closed" not in str(exc):
                    raise
                logger.warning(
                    "disconnect: upstream teardown hit the closed "
                    "connect loop; finishing teardown directly"
                )
                self._running = False
                self._connected = False
                writer = self._tcp_writer
                self._tcp_reader = None
                self._tcp_writer = None
                if writer is not None:
                    try:
                        sock = writer.get_extra_info("socket")
                        if sock is not None:
                            sock.close()
                    except Exception:
                        pass

    class CredsspSpkiRDPClient(_ForkClientBase):
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
    _ForkClientBase = None
    CredsspSpkiRDPClient = None


def _client_class():
    """Pick the RDP client class per the AISISTENT_CREDSSP_SPKI_FIX switch.

    Both classes carry the fork's logon-flags fix (change 9) via
    _ForkClientBase; the switch only changes the CredSSP key form.
    """
    if settings.credssp_spki_fix:
        return CredsspSpkiRDPClient
    return _ForkClientBase


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

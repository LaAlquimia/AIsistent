"""FreeRDP transport — drives xfreerdp on a private virtual display.

The standard FreeRDP client renders the session into an Xvfb
display owned by the display bridge; capture and input go
through that display (FREERDP-TRANSPORT-PLAN.md). Credentials
reach the client as the /p argument — the plan's O1 fallback,
taken after the /from-stdin route was measured not to deliver
(change 13): with stdin feeding, xfreerdp reached the server's
login screen but never filled it. The exposure is the proof's
(process listing, localhost, disposable account), accepted in
the plan for the trial and flagged for revisit before any
non-trial use. Never in the child's environment, never logged.
"""

import base64
import logging
import time
from io import BytesIO

from ..config import settings
from .base import Transport
from .display_bridge import XlibDisplayBridge
from .frame_check import frame_passes as _frame_passes
from .frame_check import looks_like_login_dialog as _looks_like_login_dialog

logger = logging.getLogger(__name__)

_POLL_S = 1.0


class FreeRDPTransport(Transport):
    def __init__(self, bridge=None):
        self._bridge = bridge
        self._pid: int | None = None
        self._width = 1920
        self._height = 1080
        self._poll_s = _POLL_S

    @property
    def is_connected(self) -> bool:
        return (
            self._pid is not None
            and self._bridge is not None
            and self._bridge.client_alive(self._pid)
        )

    def _get_bridge(self):
        if self._bridge is None:
            self._bridge = XlibDisplayBridge(
                width=settings.session_w,
                height=settings.session_h,
                display_spec=settings.display_spec,
            )
        return self._bridge

    # -- connection ---------------------------------------------------

    def connect(self, **kwargs) -> None:
        if self._pid is not None:
            # Single-operator policy (plan G6): one connection at
            # a time; a second connect spawns nothing.
            raise RuntimeError(
                "Already connected. Disconnect before reconnecting."
            )
        host = kwargs.get("host") or settings.rdp_host
        username = kwargs.get("username") or settings.rdp_user
        cred = kwargs.get("password") or settings.rdp_pass
        domain = kwargs.get("domain") or settings.rdp_domain or ""
        port = int(kwargs.get("port") or settings.rdp_port)
        if not 1 <= port <= 65535:
            raise ValueError(
                f"Invalid RDP port: {port}. Must be between 1 and 65535."
            )
        width = int(kwargs.get("width") or settings.session_w)
        height = int(kwargs.get("height") or settings.session_h)
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Invalid session size: {width}x{height}. "
                "Both dimensions must be positive."
            )
        if not all([host, username, cred]):
            raise ValueError(
                "RDP credentials required. Set RDP_HOST, RDP_USER, "
                "RDP_PASS env vars or pass host/username/password "
                "to connect_rdp()"
            )
        self._width, self._height = width, height

        # Binding argv (plan G5): localhost endpoint, self-signed
        # cert ignored, no device/drive/clipboard redirection
        # unless the clipboard switch is on, audio off.
        argv = [
            "xfreerdp",
            f"/v:{host}:{port}",
            f"/u:{username}",
            f"/p:{cred}",
            "/cert:ignore",
            f"/w:{width}",
            f"/h:{height}",
            "+clipboard" if settings.clipboard else "-clipboard",
            "/audio-mode:2",
            "/log-level:WARN",
        ]
        if domain:
            argv.append(f"/d:{domain}")

        bridge = self._get_bridge()
        try:
            bridge.start_display()
            log_file = None
            try:
                settings.temp_dir.mkdir(parents=True, exist_ok=True)
                log_file = str(settings.temp_dir / "freerdp-client.log")
            except Exception:
                pass
            self._pid = bridge.spawn_client(argv, log_file=log_file)
            self._await_render(bridge)
        except Exception:
            self._cleanup()
            raise
        logger.info(
            "FreeRDPTransport: connected to %s:%s as %s (%dx%d)",
            host, port, username, self._width, self._height,
        )

    def _await_render(self, bridge) -> None:
        deadline = time.time() + settings.connect_timeout_s
        focused = False
        saw_dialog = False
        while time.time() < deadline:
            if not bridge.client_alive(self._pid):
                raise RuntimeError(
                    "xfreerdp exited during connect. See the client "
                    "log in the temp captures directory."
                )
            if not focused:
                try:
                    bridge.focus_window(
                        bridge.client_window(self._pid))
                    focused = True
                except Exception:
                    pass  # window not up yet; the render poll waits
            frame = bridge.grab_frame()
            if _looks_like_login_dialog(frame):
                # The render bar alone cannot tell the server's
                # login screen from a desktop — the 2026-11-23
                # acceptance run "connected" onto the login
                # screen and every later step failed. A connect
                # counts only once the dialog clears (change 13).
                saw_dialog = True
            elif _frame_passes(frame):
                # Adopt the ACTUAL geometry (plan G10): a
                # reattached persistent session may differ from
                # the configured size.
                self._width, self._height = frame.size
                return
            time.sleep(self._poll_s)
        if saw_dialog:
            raise RuntimeError(
                "Connect failed: the server is still showing its "
                "login screen — the credentials were rejected or "
                "never reached it. No session was started."
            )
        raise RuntimeError(
            "Connect timed out: no rendered desktop within "
            f"{settings.connect_timeout_s:.0f}s. If the credentials "
            "were rejected, this timeout is how that surfaces on "
            "this path (plan G8)."
        )

    def _cleanup(self) -> None:
        if self._bridge is not None:
            if self._pid is not None:
                try:
                    self._bridge.kill_client(self._pid)
                except Exception:
                    pass
            try:
                self._bridge.stop_display()
            except Exception:
                pass
        self._pid = None

    def disconnect(self) -> None:
        # Ends the client and the virtual display. It does NOT
        # end the server-side desktop session (plan gap G1):
        # the session persists and the next connect reattaches.
        self._cleanup()
        logger.info("FreeRDPTransport: disconnected")

    # -- operations -----------------------------------------------------

    def _require_live(self) -> None:
        if self._pid is None:
            raise RuntimeError("Not connected. Call connect_rdp() first")
        if not self._bridge.client_alive(self._pid):
            self._cleanup()
            raise RuntimeError(
                "Not connected: the RDP client has exited. "
                "Call connect_rdp() to reconnect."
            )

    def capture(self) -> tuple[float, str]:
        self._require_live()
        start = time.time()
        img = self._bridge.grab_frame()
        buf = BytesIO()
        img.save(buf, format="PNG")
        duration = time.time() - start
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        logger.info("FreeRDP screen captured in %.4fs", duration)
        return duration, b64

    def click(self, x_percent: float, y_percent: float) -> dict:
        # Backstop for the fork's click gate, same as the legacy
        # transport: action.py is the primary gate, but no
        # internal caller can bypass the switch through here.
        if not settings.allow_click:
            return {
                "status": "error",
                "message": (
                    "Click injection is disabled in this fork "
                    "(AISISTENT_ALLOW_CLICK is off). Read-only mode."
                ),
            }
        self._require_live()
        click_x = int(self._width * (x_percent / 100.0))
        click_y = int(self._height * (y_percent / 100.0))
        bridge = self._bridge
        bridge.pointer_move(click_x, click_y)
        bridge.pointer_down(1)
        bridge.pointer_up(1)
        logger.info("FreeRDP click at (%d, %d)", click_x, click_y)
        return {
            "status": "success",
            "action": f"Clicked RDP coordinates: ({click_x}, {click_y})",
        }

    def send_key(self, key: str) -> dict:
        # Keyboard backstop, same pattern as the click backstop
        # (Andrew's stamp: gate the keyboard like clicks).
        if not settings.allow_keyboard:
            return {
                "status": "error",
                "message": (
                    "Keyboard input is disabled in this fork "
                    "(AISISTENT_ALLOW_KEYBOARD is off). "
                    "Read-only mode."
                ),
            }
        self._require_live()
        self._bridge.key(key)
        logger.info("FreeRDP key sent: %s", key)
        return {"status": "success", "action": f"Sent key: {key}"}

    def type_text(self, text: str) -> dict:
        if not settings.allow_keyboard:
            return {
                "status": "error",
                "message": (
                    "Keyboard input is disabled in this fork "
                    "(AISISTENT_ALLOW_KEYBOARD is off). "
                    "Read-only mode."
                ),
            }
        self._require_live()
        self._bridge.type_text(text)
        # Length only in the result and the log — never the
        # typed content (plan G15).
        logger.info("FreeRDP typed %d characters", len(text))
        return {
            "status": "success",
            "action": f"Typed {len(text)} characters",
        }

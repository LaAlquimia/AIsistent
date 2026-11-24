"""Configuration management."""

import os
from pathlib import Path
from dataclasses import dataclass, field


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    project_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
    )

    temp_dir: Path = field(init=False)
    yolo_weights: Path = field(init=False)

    def __post_init__(self):
        self.temp_dir = self.project_root / "temp_captures"
        self.yolo_weights = (
            self.project_root
            / "models"
            / "weights"
            / "best.pt"
        )

        # RDP settings (for headless transport)
        self.rdp_host: str | None = None
        self.rdp_user: str | None = None
        self.rdp_pass: str | None = None
        self.rdp_domain: str | None = None
        # Fork change 7 (FORK.md): RDP port. Upstream had no way to
        # reach a server on a nonstandard port; simple-rdp defaulted
        # to 3389. RDP_PORT env overrides.
        self.rdp_port: int = 3389

        # Fork safety switch: click injection is OFF unless explicitly
        # enabled. Only the exact value "1" opens it
        # (AISISTENT_ALLOW_CLICK=1, as FORK.md states) — any other
        # value, including "true"/"yes"/garbage, leaves it off.
        self.allow_click: bool = (
            os.getenv("AISISTENT_ALLOW_CLICK", "").strip() == "1"
        )

        # Fork compatibility shim (FORK.md change 6): simple-rdp 0.8.10's
        # CredSSP pubKeyAuth feeds the hash the RAW public key. CredSSP
        # v5+ defines it over the full SubjectPublicKeyInfo DER, and the
        # shim class can supply that form — but measured against Yggi's
        # GNOME/FreeRDP server (2026-11-23), the RAW form is what that
        # server verifies: with the shim ON the server logged "Could
        # not verify server's hash"; with it OFF, authentication
        # completed. Default is therefore OFF (stock behavior); set
        # AISISTENT_CREDSSP_SPKI_FIX=1 only for a server that rejects
        # the raw-key proof (spec-strict servers, e.g. Windows).
        # Parsed as a whitelist — only the exact value "1" turns it
        # on; a blank or garbage value stays OFF (the measured-good
        # default) instead of silently flipping behavior.
        self.credssp_spki_fix: bool = (
            os.getenv("AISISTENT_CREDSSP_SPKI_FIX", "").strip() == "1"
        )

        # FreeRDP transport build (FREERDP-TRANSPORT-PLAN.md):
        # every changeable value for the new backend, defined once
        # here. The transport switch defaulted to the legacy
        # backend until slice 3's live acceptance passed
        # (2026-11-23) and flipped it to FreeRDP.
        self.transport: str = (
            os.getenv("AISISTENT_TRANSPORT", "freerdp").strip().lower()
            or "freerdp"
        )
        # Session size: applied when a fresh session is created;
        # connect adopts the ACTUAL frame geometry when a
        # persistent session is reattached. Positivity is
        # validated at connect.
        self.session_w: int = _env_int("AISISTENT_SESSION_W", 1920)
        self.session_h: int = _env_int("AISISTENT_SESSION_H", 1080)
        # Virtual display for the FreeRDP backend: "auto" picks
        # the first free display in :90-:99, or an explicit number.
        self.display_spec: str = (
            os.getenv("AISISTENT_DISPLAY", "auto").strip().lower()
            or "auto"
        )
        self.connect_timeout_s: float = _env_float(
            "AISISTENT_CONNECT_TIMEOUT_S", 45.0)
        self.op_timeout_s: float = _env_float(
            "AISISTENT_OP_TIMEOUT_S", 10.0)
        # Clipboard redirection stays OFF unless explicitly on.
        self.clipboard: bool = (
            os.getenv("AISISTENT_CLIPBOARD", "").strip().lower()
            == "on"
        )
        # Keyboard gate (Andrew's stamp, 2026-11-23: "Gate the
        # keyboard like clicks") — same whitelist style as the
        # click switch: only the exact value "1" opens it. The
        # keyboard tools land in slice 2; the switch is defined
        # here, once, with the rest of the table.
        self.allow_keyboard: bool = (
            os.getenv("AISISTENT_ALLOW_KEYBOARD", "").strip() == "1"
        )

        # Override from env
        if env := os.getenv("AISISTENT_YOLO_WEIGHTS"):
            self.yolo_weights = Path(env)
        if env := os.getenv("AISISTENT_TEMP_DIR"):
            self.temp_dir = Path(env)
        if env := os.getenv("RDP_HOST"):
            self.rdp_host = env
        if env := os.getenv("RDP_USER"):
            self.rdp_user = env
        if env := os.getenv("RDP_PASS"):
            self.rdp_pass = env
        if env := os.getenv("RDP_DOMAIN"):
            self.rdp_domain = env
        if env := os.getenv("RDP_PORT"):
            try:
                _port = int(env)
            except ValueError:
                pass
            else:
                # Only a usable TCP port may override the default;
                # 0, negatives and >65535 keep 3389.
                if 1 <= _port <= 65535:
                    self.rdp_port = _port


settings = Settings()

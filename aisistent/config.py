"""Configuration management."""

import os
from pathlib import Path
from dataclasses import dataclass, field


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

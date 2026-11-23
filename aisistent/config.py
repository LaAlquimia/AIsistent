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

    # External project paths (OmniParser, self-operating-computer)
    omniparser_path: Path | None = field(init=False)
    soc_path: Path | None = field(init=False)

    def __post_init__(self):
        self.temp_dir = self.project_root / "temp_captures"
        self.yolo_weights = (
            self.project_root
            / "models"
            / "weights"
            / "best.pt"
        )

        # External dependencies (optional, for backward compat)
        desktop = self.project_root.parent
        omni = desktop / "OmniParser"
        soc = desktop / "self-operating-computer"
        self.omniparser_path = omni if omni.is_dir() else None
        self.soc_path = soc if soc.is_dir() else None

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
        # enabled with AISISTENT_ALLOW_CLICK=1. Default is read-only.
        self.allow_click: bool = os.getenv(
            "AISISTENT_ALLOW_CLICK", ""
        ).strip().lower() in ("1", "true", "yes", "on")

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
        self.credssp_spki_fix: bool = os.getenv(
            "AISISTENT_CREDSSP_SPKI_FIX", "0"
        ).strip().lower() not in ("0", "false", "no", "off")

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
                self.rdp_port = int(env)
            except ValueError:
                pass


settings = Settings()

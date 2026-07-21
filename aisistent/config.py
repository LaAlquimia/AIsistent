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

        # Override from env
        if env := os.getenv("AISISTENT_YOLO_WEIGHTS"):
            self.yolo_weights = Path(env)
        if env := os.getenv("AISISTENT_TEMP_DIR"):
            self.temp_dir = Path(env)


settings = Settings()

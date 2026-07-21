"""Cross-platform screen capture — macOS RDP window + MSS fallback."""

import os
import subprocess
import time
import logging
from pathlib import Path
from io import BytesIO

from PIL import Image

from .platform import CURRENT_OS, OSType

logger = logging.getLogger(__name__)


def _get_rdp_window_id_macos() -> int:
    applescript = """
    tell application "System Events"
        set rdp_windows to (every window of (every process whose name is "Microsoft Remote Desktop"))
        if (count of rdp_windows) is 0 then return "not_found"
        try
            set win_id to id of item 1 of item 1 of rdp_windows
            return win_id as string
        on error
            return "not_found"
        end try
    end tell
    """
    try:
        proc = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = proc.stdout.strip()
        if out == "not_found" or not out:
            return 0
        return int(out)
    except Exception as e:
        logger.warning("Failed to get RDP window ID: %s", e)
        return 0


def _capture_macos_rdp(path: Path) -> float:
    win_id = _get_rdp_window_id_macos()
    start = time.time()

    if win_id > 0:
        subprocess.run(
            ["screencapture", f"-l{win_id}", str(path)],
            check=True,
            capture_output=True,
        )
        logger.debug("Captured RDP window %d via screencapture -l", win_id)
    else:
        _capture_mss(path)

    return time.time() - start


def _capture_mss(path: Path) -> float:
    start = time.time()
    try:
        import mss

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(path)
        logger.debug("Captured full screen via MSS")
    except ImportError:
        logger.warning("MSS not installed, using PIL ImageGrab fallback")
        from PIL import ImageGrab

        ImageGrab.grab().save(path)

    return time.time() - start


def _capture_macos(path: Path) -> float:
    return _capture_macos_rdp(path)


def _capture_windows(path: Path) -> float:
    return _capture_mss(path)


def _capture_linux(path: Path) -> float:
    return _capture_mss(path)


def capture_screen(path: Path | str | None = None) -> tuple[float, str]:
    """Capture the RDP window (or full screen as fallback).

    Returns
    -------
    (duration_seconds, base64_image)
    """
    if path is None:
        from .config import settings

        settings.temp_dir.mkdir(parents=True, exist_ok=True)
        path = settings.temp_dir / "capture.png"

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    dispatcher = {
        OSType.MACOS: _capture_macos,
        OSType.WINDOWS: _capture_windows,
        OSType.LINUX: _capture_linux,
    }

    fn = dispatcher.get(CURRENT_OS, _capture_linux)
    duration = fn(path)

    with open(path, "rb") as f:
        b64 = __import__("base64").b64encode(f.read()).decode("utf-8")

    logger.info("Screen captured in %.4fs on %s", duration, CURRENT_OS.value)
    return duration, b64

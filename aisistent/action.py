"""Cross-platform click injection via pyautogui."""

import time
import subprocess
import logging

from .platform import CURRENT_OS, OSType

logger = logging.getLogger(__name__)


def _activate_rdp_window() -> None:
    """Bring RDP window to foreground (macOS only, noop on other OS)."""
    if CURRENT_OS == OSType.MACOS:
        try:
            subprocess.run(
                ["osascript", "-e", 'tell application "Microsoft Remote Desktop" to activate'],
                capture_output=True,
                timeout=3,
            )
            time.sleep(0.3)
        except Exception as e:
            logger.warning("Failed to activate RDP window: %s", e)


def inject_click(x_percent: float, y_percent: float) -> dict:
    """Simulate a mouse click at percentage-based coordinates.

    Returns
    -------
    dict with keys: status, action
    """
    try:
        import pyautogui

        _activate_rdp_window()

        screen_w, screen_h = pyautogui.size()
        click_x = int(screen_w * (x_percent / 100.0))
        click_y = int(screen_h * (y_percent / 100.0))

        pyautogui.moveTo(click_x, click_y)
        pyautogui.click()

        logger.info("Clicked at (%d, %d) on %s", click_x, click_y, CURRENT_OS.value)
        return {"status": "success", "action": f"Clicked coordinates: ({click_x}, {click_y})"}
    except Exception as e:
        logger.exception("Click injection failed")
        return {"status": "error", "message": str(e)}

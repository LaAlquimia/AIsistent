"""Platform and hardware detection."""

import sys
import logging
from enum import Enum

try:
    import torch
except ImportError:  # fork: torch is an optional `detect` extra
    torch = None

logger = logging.getLogger(__name__)


class OSType(str, Enum):
    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"


class DeviceType(str, Enum):
    CUDA = "cuda"
    MPS = "mps"
    CPU = "cpu"


def detect_os() -> OSType:
    if sys.platform == "darwin":
        return OSType.MACOS
    elif sys.platform == "win32":
        return OSType.WINDOWS
    else:
        return OSType.LINUX


def detect_device() -> DeviceType:
    if torch is None:
        logger.info("torch not installed, using CPU")
        return DeviceType.CPU
    if torch.cuda.is_available():
        logger.info("CUDA GPU detected")
        return DeviceType.CUDA
    elif torch.backends.mps.is_available():
        logger.info("Apple Silicon MPS GPU detected")
        return DeviceType.MPS
    else:
        logger.info("No GPU detected, using CPU")
        return DeviceType.CPU


CURRENT_OS = detect_os()
CURRENT_DEVICE = detect_device()

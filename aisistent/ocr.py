"""Cross-platform OCR — Apple Vision (macOS) + EasyOCR fallback (CPU/CUDA)."""

import time
import sys
import os
import logging
from io import BytesIO

from PIL import Image

from .platform import CURRENT_OS, OSType, CURRENT_DEVICE, DeviceType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# macOS Apple Vision OCR (native, ~0.05s)
# ---------------------------------------------------------------------------

_HAS_APPLE_VISION = False
_apple_vision_ocr_fn = None

if CURRENT_OS == OSType.MACOS:
    try:
        import Vision
        from Cocoa import NSURL
        from Quartz import (
            CGImageSourceCreateWithURL,
            CGImageSourceCreateImageAtIndex,
            kCGImageSourceShouldCache,
        )
        import tempfile

        _HAS_APPLE_VISION = True
    except ImportError:
        logger.warning("pyobjc-framework-Vision not installed. Install with: pip install aisistent[apple]")

    if _HAS_APPLE_VISION:
        def _apple_vision_ocr(image: Image.Image, recognition_level: str = "accurate") -> tuple[list[str], list[list[float]]]:
            w, h = image.size
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                img_path = f.name
                image.save(img_path, format="PNG")
            try:
                ns_url = NSURL.fileURLWithPath_(img_path)
                src = CGImageSourceCreateWithURL(ns_url, {kCGImageSourceShouldCache: False})
                cg_image = CGImageSourceCreateImageAtIndex(src, 0, None)

                request = Vision.VNRecognizeTextRequest.alloc().init()
                level = (
                    Vision.VNRequestTextRecognitionLevelFast
                    if recognition_level == "fast"
                    else Vision.VNRequestTextRecognitionLevelAccurate
                )
                request.setRecognitionLevel_(level)
                request.setUsesLanguageCorrection_(False)

                handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
                success, _ = handler.performRequests_error_([request], None)
                if not success:
                    return [], []

                texts, bboxes = [], []
                for obs in request.results() or []:
                    candidates = obs.topCandidates_(1)
                    if not candidates:
                        continue
                    text = candidates[0].string()
                    box = obs.boundingBox()
                    x, y, bw, bh = box.origin.x, box.origin.y, box.size.width, box.size.height
                    x1 = x * w
                    y1 = (1.0 - y - bh) * h
                    x2 = (x + bw) * w
                    y2 = (1.0 - y) * h
                    texts.append(text)
                    bboxes.append([x1, y1, x2, y2])
                return texts, bboxes
            finally:
                try:
                    os.unlink(img_path)
                except OSError:
                    pass

        _apple_vision_ocr_fn = _apple_vision_ocr

# ---------------------------------------------------------------------------
# EasyOCR fallback (CPU / CUDA NVIDIA)
# ---------------------------------------------------------------------------

_HAS_EASY_OCR = False
_easy_ocr_fn = None

try:
    import easyocr

    _HAS_EASY_OCR = True
except ImportError:
    logger.debug("easyocr not installed — CPU/CUDA OCR will not be available")

if _HAS_EASY_OCR:
    _reader = None

    def _get_easyocr_reader():
        global _reader
        if _reader is None:
            gpu = CURRENT_DEVICE == DeviceType.CUDA
            logger.info("Initializing EasyOCR (gpu=%s)", gpu)
            _reader = easyocr.Reader(["en"], gpu=gpu)
        return _reader

    def _easy_ocr_fn(image: Image.Image) -> tuple[list[str], list[list[float]]]:
        import numpy as np

        reader = _get_easyocr_reader()
        result = reader.readtext(np.array(image))
        texts = [item[1] for item in result]
        bboxes = []
        for item in result:
            pts = item[0]
            x1 = min(p[0] for p in pts)
            y1 = min(p[1] for p in pts)
            x2 = max(p[0] for p in pts)
            y2 = max(p[1] for p in pts)
            bboxes.append([x1, y1, x2, y2])
        return texts, bboxes

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_ocr(image_bytes: bytes, recognition_level: str = "accurate") -> dict:
    """Run OCR on raw image bytes.

    Returns
    -------
    dict with keys: status, duration_seconds, elements_detected, ocr_results
    """
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    start = time.time()

    if _apple_vision_ocr_fn and CURRENT_OS == OSType.MACOS:
        texts, bboxes = _apple_vision_ocr_fn(image, recognition_level)
    elif _easy_ocr_fn:
        texts, bboxes = _easy_ocr_fn(image)
    else:
        return {"status": "error", "message": "No OCR backend available. Install: pip install aisistent[all]"}

    duration = time.time() - start
    results = [{"text": t, "bbox": b} for t, b in zip(texts, bboxes)]

    logger.info("OCR done in %.4fs — %d elements", duration, len(results))
    return {
        "status": "success",
        "duration_seconds": f"{duration:.4f}",
        "elements_detected": len(results),
        "ocr_results": results,
    }

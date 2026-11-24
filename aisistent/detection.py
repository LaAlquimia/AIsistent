"""YOLOv8 button detection — auto device (CUDA / MPS / CPU)."""

import time
import os
import logging
from io import BytesIO

from PIL import Image

from .platform import CURRENT_DEVICE, DeviceType
from .config import settings

logger = logging.getLogger(__name__)

_has_ultralytics = False
try:
    from ultralytics import YOLO

    _has_ultralytics = True
except ImportError:
    logger.debug("ultralytics not installed — YOLO detection unavailable")


def detect_buttons(image_bytes: bytes, conf_threshold: float = 0.25) -> dict:
    """Run YOLOv8 button detection on raw image bytes.

    Returns
    -------
    dict with keys: status, device, load_duration_seconds,
                    inference_duration_seconds, elements_detected, detections
    """
    if not _has_ultralytics:
        return {
            "status": "error",
            "message": "ultralytics not installed. Run: pip install aisistent[all]",
        }

    # Fork (EGM F16): only the fork's own weights path is consulted.
    # Upstream silently fell back to weights in sibling projects
    # outside this tree (self-operating-computer, OmniParser) — code
    # and models outside the reviewed tree never load in this fork.
    weights = settings.yolo_weights

    if not weights.exists():
        return {
            "status": "error",
            "message": (
                f"YOLO weights not found. Place best.pt at {settings.yolo_weights} "
                f"or set AISISTENT_YOLO_WEIGHTS env var"
            ),
        }

    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    try:
        device = CURRENT_DEVICE.value

        t0 = time.time()
        model = YOLO(str(weights)).to(device)
        load_dur = time.time() - t0

        t1 = time.time()
        results = model(image, imgsz=640, verbose=False)
        infer_dur = time.time() - t1

        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                if conf < conf_threshold:
                    continue
                cls = int(box.cls[0])
                detections.append(
                    {
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(conf, 4),
                        "class_id": cls,
                    }
                )

        logger.info(
            "YOLO detection done in %.4fs (load %.4fs) — %d elements on %s",
            infer_dur,
            load_dur,
            len(detections),
            device,
        )
        return {
            "status": "success",
            "device": device,
            "load_duration_seconds": f"{load_dur:.4f}",
            "inference_duration_seconds": f"{infer_dur:.4f}",
            "elements_detected": len(detections),
            "detections": detections,
        }
    except Exception as e:
        logger.exception("YOLO detection failed")
        return {"status": "error", "message": str(e)}

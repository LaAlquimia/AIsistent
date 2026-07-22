"""Performance benchmark — OCR + YOLO across all backends."""

import argparse
import logging
import sys
import time
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from .platform import CURRENT_OS, OSType, CURRENT_DEVICE, DeviceType, detect_device

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("benchmark")


def create_test_image(size=(1920, 1080)) -> bytes:
    img = Image.new("RGB", size, color=(230, 230, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([(100, 100), (300, 150)], fill=(70, 130, 180), outline="black")
    d.text((120, 115), "Enviar Mensaje", fill="white")
    d.rectangle([(500, 200), (700, 250)], fill=(34, 139, 34), outline="black")
    d.text((520, 215), "Click here", fill="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def run_benchmark(image_bytes: bytes, skip_ocr: bool = False) -> dict:
    results = {"platform": CURRENT_OS.value, "device": CURRENT_DEVICE.value}

    # OCR
    if not skip_ocr and CURRENT_OS == OSType.MACOS:
        log.info("[1/3] Apple Vision OCR (macOS native)...")
        from .ocr import run_ocr

        t0 = time.perf_counter()
        ocr_result = run_ocr(image_bytes)
        elapsed = time.perf_counter() - t0
        log.info(f"  -> {ocr_result.get('elements_detected', 0)} elements in {elapsed:.4f}s")
        results["ocr_duration"] = f"{elapsed:.4f}"
        results["ocr_elements"] = ocr_result.get("elements_detected", 0)
    elif skip_ocr:
        log.info("[1/3] OCR — SKIPPED")
    else:
        log.info("[1/3] EasyOCR (CPU/CUDA)...")
        from .ocr import run_ocr

        t0 = time.perf_counter()
        ocr_result = run_ocr(image_bytes)
        elapsed = time.perf_counter() - t0
        log.info(f"  -> {ocr_result.get('elements_detected', 0)} elements in {elapsed:.4f}s")
        results["ocr_duration"] = f"{elapsed:.4f}"
        results["ocr_elements"] = ocr_result.get("elements_detected", 0)

    # YOLO
    log.info(f"[2/3] Loading YOLO model on {CURRENT_DEVICE.value.upper()}...")
    from .detection import detect_buttons

    t0 = time.perf_counter()
    yolo_result = detect_buttons(image_bytes)
    elapsed = time.perf_counter() - t0
    log.info(f"  -> {yolo_result.get('elements_detected', 0)} detections in {elapsed:.4f}s")
    results["yolo_duration"] = yolo_result.get("inference_duration_seconds", "0")
    results["yolo_load_duration"] = yolo_result.get("load_duration_seconds", "0")
    results["yolo_detections"] = yolo_result.get("elements_detected", 0)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="AIsistent cross-platform benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  aisistent-bench                         # full benchmark\n"
            "  aisistent-bench --skip-ocr              # YOLO only\n"
            "  aisistent-bench --image test.png         # use existing image\n"
        ),
    )
    parser.add_argument("--image", type=Path, help="Path to a PNG screenshot")
    parser.add_argument("--skip-ocr", action="store_true", help="Skip OCR test")
    parser.add_argument(
        "--device",
        choices=["auto", "cuda", "mps", "cpu"],
        default="auto",
        help="Override device (default: auto-detect)",
    )
    args = parser.parse_args()

    if args.device != "auto":
        log.info(f"Device override: {args.device}")
        # Force re-detect if needed — currently platform.CURRENT_DEVICE is set at import

    log.info("=" * 57)
    log.info("      AISISTENT — PERFORMANCE BENCHMARK")
    log.info("=" * 57)
    log.info(f"  Platform : {CURRENT_OS.value}")
    log.info(f"  Device   : {CURRENT_DEVICE.value}")

    if args.image:
        image_bytes = args.image.read_bytes()
        log.info(f"  Image    : {args.image}")
    else:
        log.info("  Image    : synthetic (1920x1080)")
        image_bytes = create_test_image()

    log.info("=" * 57)

    results = run_benchmark(image_bytes, skip_ocr=args.skip_ocr)

    log.info("\n" + "=" * 57)
    log.info("  BENCHMARK RESULTS")
    log.info("=" * 57)
    log.info(f"  Platform : {results['platform']}")
    log.info(f"  Device   : {results['device']}")
    if not args.skip_ocr:
        log.info(f"  OCR      : {results.get('ocr_duration', 'N/A')}s  ({results.get('ocr_elements', 0)} elem)")
    log.info(f"  YOLO     : {results['yolo_duration']}s  ({results['yolo_detections']} det)")
    log.info("=" * 57)


if __name__ == "__main__":
    main()

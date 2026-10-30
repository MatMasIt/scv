"""Optional Optical Character Recognition (OCR) support via Tesseract."""

from __future__ import annotations
from pathlib import Path
from .ffmpeg import tesseract_bin


def ocr_image(image: Path, language: str) -> str:
    """Extract text from one image with the installed Tesseract executable."""
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "pytesseract is required for OCR. Install it with: pip install pytesseract"
        ) from exc

    pytesseract.pytesseract.tesseract_cmd = tesseract_bin()
    if not image.is_file():
        raise FileNotFoundError(f"OCR image does not exist: {image}")
    try:
        return " ".join(
            pytesseract.image_to_string(
                str(image), lang=language, config="--psm 11"
            ).split()
        )
    except (pytesseract.TesseractError, pytesseract.TesseractNotFoundError) as exc:
        raise RuntimeError(
            f"OCR failed for {image.name} using language '{language}': {exc}"
        ) from exc

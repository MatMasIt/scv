"""FFmpeg and external tool discovery and execution wrappers."""

from __future__ import annotations
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys


def ffmpeg_bin(name: str) -> str:
    """Resolve an FFmpeg executable from a bundle, package, or system PATH."""
    executable = name + (".exe" if os.name == "nt" else "")
    roots = [
        Path(sys.executable).resolve().parent,
        Path(getattr(sys, "_MEIPASS", "") or ".").resolve(),
        Path(__file__).resolve().parents[2],
    ]
    for root in roots:
        for candidate in (root / "bin" / executable, root / executable):
            if candidate.is_file():
                return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise RuntimeError(
        f"{name} not found. Install FFmpeg or place {executable} in the app bin/ directory"
    )


def tesseract_bin() -> str:
    """Resolve the optional Tesseract OCR executable."""
    executable = "tesseract.exe" if os.name == "nt" else "tesseract"
    roots = [
        Path(sys.executable).resolve().parent,
        Path(getattr(sys, "_MEIPASS", "") or ".").resolve(),
        Path(__file__).resolve().parents[2],
    ]
    for root in roots:
        for candidate in (root / "bin" / executable, root / executable):
            if candidate.is_file():
                return str(candidate)
    found = shutil.which("tesseract")
    if found:
        return found
    raise RuntimeError(
        "Tesseract not found. Install Tesseract or place it in the app bin/ directory"
    )


def require_ffmpeg():
    """Verify that both FFmpeg and FFprobe can be resolved."""
    for name in ("ffmpeg", "ffprobe"):
        ffmpeg_bin(name)


def _command(args) -> list[str]:
    """Normalize command arguments and replace logical FFmpeg names."""
    normalized = list(map(str, args))
    if normalized and normalized[0] in ("ffmpeg", "ffprobe"):
        normalized[0] = ffmpeg_bin(normalized[0])
    return normalized


def probe(source: Path | str) -> float:
    """Return the positive duration, in seconds, reported for a media file."""
    p = subprocess.run(
        _command(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(source),
            ]
        ),
        capture_output=True,
        text=True,
        check=True,
    )
    duration = float(json.loads(p.stdout)["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid video duration")
    return duration

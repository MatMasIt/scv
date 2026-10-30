"""SCV storage and encoding core package.

No Qt dependency; safe for CLI, background workers, and headless batch jobs.
"""

from __future__ import annotations

from .models import (
    VERSION,
    FORMAT_VERSION,
    Progress,
    PRESETS,
    Settings,
    Cancelled,
    Job,
)
from .ffmpeg import (
    ffmpeg_bin,
    tesseract_bin,
    require_ffmpeg,
    _command,
    probe,
)
from .ocr import ocr_image
from .detection import (
    _difference,
    detect_slides,
)
from .archive import (
    LectureManifest,
    SlideManifest,
    _safe_member,
    inspect,
    extract,
    frame_at,
)
from .encode import encode
from .lecture import LectureSession
from .errors import (
    SCVError,
    ArchiveError,
    InvalidManifestError,
    UnsafeArchiveError,
)

__all__ = [
    "VERSION",
    "FORMAT_VERSION",
    "Progress",
    "PRESETS",
    "Settings",
    "Cancelled",
    "Job",
    "ffmpeg_bin",
    "tesseract_bin",
    "ocr_image",
    "require_ffmpeg",
    "_command",
    "probe",
    "_difference",
    "detect_slides",
    "_safe_member",
    "inspect",
    "extract",
    "frame_at",
    "LectureManifest",
    "SlideManifest",
    "encode",
    "LectureSession",
    "SCVError",
    "ArchiveError",
    "InvalidManifestError",
    "UnsafeArchiveError",
]

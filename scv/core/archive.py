"""SCV package inspection, extraction, and slide loading."""

from __future__ import annotations
import bisect
import json
import math
import shutil
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import TypedDict, cast

from PIL import Image

from .errors import ArchiveError, InvalidManifestError, UnsafeArchiveError
from .models import FORMAT_VERSION


class SlideManifest(TypedDict, total=False):
    """Validated slide entry stored in an SCV manifest."""

    time: float
    image: str
    text: str


class LectureManifest(TypedDict):
    """Validated metadata required to play an SCV lecture."""

    format: str
    format_version: int
    duration_seconds: float
    audio: dict[str, str]
    slides: list[SlideManifest]
    title: str


def _safe_member(name: str) -> bool:
    """Return whether an archive member path stays within the archive root."""
    p = PurePosixPath(name)
    return bool(
        name
        and not name.startswith("/")
        and not name.startswith("\\")
        and "\\" not in name
        and ".." not in p.parts
        and p.parts[0] not in (".", "")
    )


def inspect(path: Path | str) -> LectureManifest:
    """Validate an SCV archive and return its trusted manifest."""
    try:
        with zipfile.ZipFile(path) as archive:
            return _inspect_archive(archive)
    except ArchiveError:
        raise
    except (
        OSError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        EOFError,
        RuntimeError,
        zlib.error,
    ) as exc:
        raise ArchiveError(f"Unable to read SCV archive: {exc}") from exc


def _inspect_archive(archive: zipfile.ZipFile) -> LectureManifest:
    """Validate archive contents after opening the ZIP container."""
    try:
        info = archive.getinfo("manifest.json")
    except KeyError as exc:
        raise InvalidManifestError("Missing manifest.json") from exc
    if info.file_size > 2_000_000:
        raise InvalidManifestError("Manifest exceeds limit")
    try:
        manifest = json.loads(archive.read("manifest.json"))
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise InvalidManifestError("Invalid manifest JSON") from exc
    if not isinstance(manifest, dict):
        raise InvalidManifestError("Manifest must be a JSON object")
    format_version = manifest.get("format_version")
    if (
        manifest.get("format") != "SCV"
        or isinstance(format_version, bool)
        or not isinstance(format_version, int)
        or format_version != FORMAT_VERSION
    ):
        raise InvalidManifestError("Unsupported SCV version")

    slides = manifest.get("slides")
    if not isinstance(slides, list) or not (1 <= len(slides) <= 100000):
        raise InvalidManifestError("Invalid slide timeline")
    audio = manifest.get("audio")
    if not isinstance(audio, dict) or audio.get("file") != "audio.opus":
        raise InvalidManifestError("Unsupported audio path")

    names = {item.filename: item for item in archive.infolist()}
    last = -1.0
    first = None
    total = 0
    for slide in slides:
        if not isinstance(slide, dict):
            raise InvalidManifestError("Invalid slide entry")
        name, raw_time = slide.get("image"), slide.get("time")
        if (
            not isinstance(name, str)
            or not name.startswith("slides/")
            or not name.endswith(".webp")
            or not _safe_member(name)
        ):
            raise UnsafeArchiveError("Unsafe slide path")
        if isinstance(raw_time, bool) or not isinstance(raw_time, (float, int)):
            raise InvalidManifestError("Invalid slide timestamp")
        try:
            timestamp = float(raw_time)
        except (OverflowError, ValueError) as exc:
            raise InvalidManifestError("Invalid slide timestamp") from exc
        if not math.isfinite(timestamp) or timestamp < last or timestamp < 0:
            raise InvalidManifestError("Invalid slide timestamp")
        if set(slide) - {"time", "image", "text"} or (
            "text" in slide and not isinstance(slide["text"], str)
        ):
            raise InvalidManifestError("Only full slide images are supported")
        if first is None:
            first = timestamp
        last = timestamp
        if name not in names:
            raise UnsafeArchiveError(f"Missing {name}")
        total += names[name].file_size

    if first != 0:
        raise InvalidManifestError("Initial slide must start at zero")
    if "audio.opus" not in names:
        raise UnsafeArchiveError("Missing audio.opus")
    if total + names["audio.opus"].file_size > 4 * 1024**3:
        raise UnsafeArchiveError("SCV extraction exceeds size limit")

    raw_duration = manifest.get("duration_seconds")
    if isinstance(raw_duration, bool) or not isinstance(raw_duration, (int, float)):
        raise InvalidManifestError("Invalid duration")
    try:
        duration = float(raw_duration)
    except (OverflowError, ValueError) as exc:
        raise InvalidManifestError("Invalid duration") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise InvalidManifestError("Invalid duration")
    if last > duration + 0.5:
        raise InvalidManifestError("Slide timestamp beyond audio duration")
    if any(
        item.file_size > 200 * 1024**2
        for item in names.values()
        if item.filename.startswith("slides/")
    ):
        raise UnsafeArchiveError("Oversized slide image")
    return cast(LectureManifest, manifest)


def extract(path: Path | str, destination: Path | str) -> LectureManifest:
    """Validate and safely extract an SCV archive into ``destination``."""
    manifest = inspect(path)
    base = Path(destination)
    members = {"audio.opus"} | {s["image"] for s in manifest["slides"]}
    with zipfile.ZipFile(path) as z:
        for name in members:
            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    return manifest


def frame_at(manifest: LectureManifest, base: Path, position: float) -> Image.Image:
    """Load the slide image active at ``position`` seconds."""
    slides = manifest["slides"]
    index = max(0, bisect.bisect_right([s["time"] for s in slides], position) - 1)
    with Image.open(base / slides[index]["image"]) as image:
        return image.convert("RGB")

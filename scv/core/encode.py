"""Video to SCV encoding pipeline."""

from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import zipfile
from PIL import Image

from .archive import inspect
from .detection import detect_slides
from .ffmpeg import require_ffmpeg, probe
from .models import Settings, Job, Progress, VERSION, FORMAT_VERSION
from .ocr import ocr_image


def encode(
    source: Path | str,
    destination: Path | str,
    settings: Settings | None = None,
    progress: Progress | None = None,
    job: Job | None = None,
) -> dict:
    """Encode a source video into an SCV archive and return its manifest."""
    source, destination = Path(source).expanduser(), Path(destination).expanduser()
    settings = settings or Settings()
    settings.validate()
    progress = progress or (lambda p, msg: None)
    job = job or Job()
    require_ffmpeg()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == destination.resolve():
        raise ValueError("Source and destination must differ")
    duration = probe(source)
    progress(0.01, "Reading video")
    with tempfile.TemporaryDirectory(prefix="scv_encode_") as temp:
        root = Path(temp)
        (root / "slides").mkdir()
        progress(0.04, "Encoding Opus audio")
        job.run(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-vn",
                "-sn",
                "-c:a",
                "libopus",
                "-b:a",
                f"{settings.bitrate}k",
                "-vbr",
                "on",
                "-compression_level",
                "10",
                "-application",
                "voip" if not settings.stereo else "audio",
                "-ac",
                "2" if settings.stereo else "1",
                str(root / "audio.opus"),
            ],
            progress=lambda p, msg: progress(0.04 + 0.16 * p, msg),
            duration=duration,
        )
        progress(0.20, "Detecting slide transitions")
        scenes = detect_slides(source, duration, settings, job, progress)
        slides = []
        for i, scene in enumerate(scenes, 1):
            job.check()
            capture = root / "capture.png"
            job.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-ss",
                    str(scene["capture"]),
                    "-i",
                    str(source),
                    "-map",
                    "0:v:0",
                    "-frames:v",
                    "1",
                    "-an",
                    str(capture),
                ]
            )
            if not capture.exists():
                raise RuntimeError(f"Could not extract slide {i}")
            with Image.open(capture) as image:
                out_name = f"slides/{i:05}.webp"
                image.convert("RGB").save(
                    root / out_name, "WEBP", quality=settings.quality, method=6
                )
            text = ""
            if settings.ocr:
                progress(
                    0.70 + 0.26 * (i - 0.5) / len(scenes),
                    f"OCR slide {i}/{len(scenes)}",
                )
                text = ocr_image(capture, settings.ocr_lang)
                progress(
                    0.70 + 0.26 * i / len(scenes),
                    f"OCR slide {i}/{len(scenes)}"
                    + (
                        f" · {len(text)} characters"
                        if text
                        else " · no text detected"
                    ),
                )
            capture.unlink()
            slide = {"time": scene["time"], "image": out_name}
            if settings.ocr:
                slide["text"] = text
            slides.append(slide)
            progress(
                0.70 + 0.26 * i / len(scenes), f"Encoding slide {i}/{len(scenes)}"
            )
        manifest = {
            "format": "SCV",
            "format_version": FORMAT_VERSION,
            "format_name": "Slide Compressed Video",
            "generator": "SCV Suite " + VERSION,
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "title": source.stem,
            "duration_seconds": round(duration, 3),
            "audio": {
                "file": "audio.opus",
                "codec": "opus",
                "bitrate": f"{settings.bitrate}k",
                "channels": 2 if settings.stereo else 1,
            },
            "image": {"codec": "webp", "quality": settings.quality, "deltas": False},
            "ocr": (
                {"enabled": settings.ocr, "language": settings.ocr_lang}
                if settings.ocr
                else {"enabled": False}
            ),
            "timing": "start_time_seconds",
            "slides": slides,
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        part = destination.with_name(destination.name + ".part")
        try:
            with zipfile.ZipFile(part, "w", compression=zipfile.ZIP_STORED) as archive:
                for path in [root / "manifest.json", root / "audio.opus"] + [
                    root / s["image"] for s in slides
                ]:
                    job.check()
                    archive.write(path, path.relative_to(root).as_posix())
            job.check()
            os.replace(part, destination)
        finally:
            part.unlink(missing_ok=True)
    progress(1, f"Created {destination.name} · {len(slides)} slides")
    return manifest

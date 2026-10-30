"""Core data structures and constants for SCV."""

from __future__ import annotations
from dataclasses import dataclass
import subprocess
import threading
from typing import Callable

VERSION = "1.0.0"
FORMAT_VERSION = 1  # SCV 1.0; only supported archive format
Progress = Callable[[float, str], None]

PRESETS = {
    "Compact voice": {
        "bitrate": 12,
        "quality": 75,
        "fps": 2,
        "change": 9,
        "stable": 3,
        "settle": 3,
        "stereo": False,
        "ocr": False,
        "ocr_lang": "eng",
    },
    "Balanced": {
        "bitrate": 24,
        "quality": 80,
        "fps": 2,
        "change": 9,
        "stable": 3,
        "settle": 3,
        "stereo": False,
        "ocr": False,
        "ocr_lang": "eng",
    },
    "High quality": {
        "bitrate": 48,
        "quality": 90,
        "fps": 2,
        "change": 7,
        "stable": 3,
        "settle": 3,
        "stereo": True,
        "ocr": False,
        "ocr_lang": "eng",
    },
}


@dataclass
class Settings:
    """Validated options controlling audio, slide detection, and image output."""

    bitrate: int = 24
    quality: int = 80
    fps: float = 2
    change: float = 9
    stable: float = 3
    settle: int = 3
    stereo: bool = False
    ocr: bool = False
    ocr_lang: str = "eng"

    @classmethod
    def from_preset(cls, name: str, **overrides: object) -> Settings:
        """Create Settings initialized from a named preset with optional overrides."""
        if name not in PRESETS:
            raise KeyError(f"Unknown preset: {name}. Choose from: {list(PRESETS.keys())}")
        config = dict(PRESETS[name])
        for key, val in overrides.items():
            if val is not None:
                config[key] = val
        return cls(**config)

    def validate(self) -> None:
        """Validate codec and slide-detection settings before starting a job."""
        if not 6 <= self.bitrate <= 256:
            raise ValueError("Opus bitrate must be 6-256 kbps")
        if not 1 <= self.quality <= 100:
            raise ValueError("WebP quality must be 1-100")
        if not self.ocr_lang or any(char.isspace() for char in self.ocr_lang):
            raise ValueError("OCR language must be a non-empty Tesseract language code")
        if not 0.2 <= self.fps <= 12:
            raise ValueError("scan FPS must be 0.2-12")
        if not 0 < self.change <= 100 or not 0 <= self.stable <= 100:
            raise ValueError("Invalid change/stability threshold")
        if not 1 <= self.settle <= 20:
            raise ValueError("settle must be 1-20 samples")


class Cancelled(Exception):
    """Raised when a running conversion is cancelled by the caller."""

    pass


class Job:
    """Run one cancellable FFmpeg job from a worker thread."""

    def __init__(self) -> None:
        """Create a cancellable job with no active subprocess."""
        self.cancel_event = threading.Event()
        self.process: subprocess.Popen | None = None

    def cancel(self) -> None:
        """Request cancellation and terminate the active FFmpeg process."""
        self.cancel_event.set()
        if self.process and self.process.poll() is None:
            self.process.kill()

    def check(self) -> None:
        """Raise :class:`Cancelled` if cancellation has been requested."""
        if self.cancel_event.is_set():
            raise Cancelled("Conversion cancelled")

    def run(
        self, args: list[str] | tuple[str, ...], *, progress: Progress | None = None, duration: float | None = None
    ) -> None:
        """Run an FFmpeg command and optionally report media-time progress.

        ``args`` is passed as an argument list, never through a shell. When a
        duration is supplied, FFmpeg's machine-readable progress stream is
        translated into fractions for the caller.
        """
        from .ffmpeg import _command

        self.check()
        command = _command(args)
        if progress and duration and duration > 0:
            command = command[:-1] + ["-progress", "pipe:1", "-nostats", command[-1]]
        p = subprocess.Popen(
            command,
            stdout=subprocess.PIPE if progress else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.process = p
        try:
            if progress and duration and duration > 0:
                assert p.stdout is not None
                for line in p.stdout:
                    if line.startswith("out_time_ms="):
                        try:
                            fraction = min(
                                1.0,
                                max(
                                    0.0,
                                    float(line.split("=", 1)[1]) / 1_000_000 / duration,
                                ),
                            )
                            progress(
                                fraction,
                                (
                                    "Encoding audio"
                                    if "libopus" in command
                                    else "Rendering MP4"
                                ),
                            )
                        except ValueError:
                            pass
                    elif line.startswith("progress=end"):
                        progress(
                            1.0,
                            (
                                "Encoding audio"
                                if "libopus" in command
                                else "Rendering MP4"
                            ),
                        )
                assert p.stderr is not None
                err = p.stderr.read()
                p.wait()
            else:
                _, err = p.communicate()
            self.check()
            if p.returncode:
                raise RuntimeError(
                    f"Command failed: {' '.join(map(str, args[:4]))}\n{err[-1800:]}"
                )
        finally:
            self.process = None

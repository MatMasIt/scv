"""Visual transition detection and slide extraction logic."""

from __future__ import annotations
from pathlib import Path
import subprocess
import numpy as np
from .ffmpeg import _command
from .models import Settings, Job, Progress


def _difference(a: np.ndarray, b: np.ndarray) -> float:
    """Return the mean absolute pixel difference between two arrays."""
    return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())


def detect_slides(
    source: Path, duration: float, settings: Settings, job: Job, progress: Progress
) -> list[dict]:
    """Detect stable visual transitions and return their capture timestamps."""
    width, height = 480, 270
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-vf",
        f"fps={settings.fps},scale={width}:{height},format=gray",
        "-an",
        "-sn",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-",
    ]
    p = subprocess.Popen(
        _command(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=width * height * 2,
    )
    job.process = p
    previous = accepted = None
    consecutive = 0
    stable_start = 0.0
    frames = []
    index = 0
    try:
        while True:
            job.check()
            raw = p.stdout.read(width * height)
            if not raw:
                break
            if len(raw) != width * height:
                raise ValueError("Incomplete decoded frame")
            current = np.frombuffer(raw, np.uint8).reshape((height, width)).copy()
            t = index / settings.fps
            if accepted is None:
                frames.append({"time": 0.0, "capture": 0.0})
                accepted = current
                consecutive = 1
            else:
                if _difference(current, previous) <= settings.stable:
                    consecutive += 1
                else:
                    consecutive = 1
                    stable_start = t
                if (
                    consecutive >= settings.settle
                    and _difference(current, accepted) >= settings.change
                ):
                    frames.append(
                        {"time": round(stable_start, 3), "capture": round(t, 3)}
                    )
                    accepted = current
            previous = current
            index += 1
            if index % 16 == 0:
                progress(
                    0.20 + 0.50 * min(1, t / duration),
                    f"Scanning {t:.0f}/{duration:.0f}s · {len(frames)} slides",
                )
        if p.wait() != 0:
            raise RuntimeError("FFmpeg slide scan failed")
    finally:
        if p.poll() is None:
            p.kill()
        p.stdout.close()
        job.process = None
    if not frames:
        raise ValueError("No video frames decoded")
    return frames

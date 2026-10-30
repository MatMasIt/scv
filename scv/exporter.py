"""Render SCV slides and audio into a normal MP4. CLI and Qt frontend."""

from __future__ import annotations
import argparse
from collections.abc import Callable
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image

from .core import inspect, extract, frame_at, Job, ffmpeg_bin


def export_video(source: Path | str, destination: Path | str, *, crf: int=20, progress: Callable[[float, str], None] | None=None, job: Job | None=None) -> Path:
    """Convert an SCV archive to an H.264/AAC MP4 file.

    Frame preparation is reported separately from FFmpeg rendering. The
    destination is replaced only after a successful render.
    """
    source, destination = Path(source), Path(destination)
    if not 0 <= crf <= 51:
        raise ValueError("CRF must be between 0 and 51")
    if source.resolve() == destination.resolve():
        raise ValueError("Input and output paths must differ")
    manifest = inspect(source)
    job = job or Job()
    progress = progress or (lambda fraction, status: None)
    duration = float(manifest["duration_seconds"])
    with tempfile.TemporaryDirectory(prefix="scv_export_") as t:
        root = Path(t)
        extract(source, root)
        slides = manifest["slides"]
        # Constant dimensions required for MP4; scale/pad happens inside FFmpeg.
        concat = root / "frames.txt"
        frames = []
        for idx, slide in enumerate(slides):
            job.check()
            image_name = slide.get("image")
            if image_name is None:
                raise ValueError(f"Slide {idx + 1} has no image")
            image = Image.open(root / image_name)
            name = f"frame_{idx:06d}.png"
            image.save(root / name)
            frames.append(name)
            progress(
                0.35 * (idx + 1) / len(slides), f"Preparing frame {idx+1}/{len(slides)}"
            )
        with concat.open("w", encoding="utf-8") as f:
            for idx, slide in enumerate(slides):
                start = float(slide["time"])
                end = (
                    float(slides[idx + 1]["time"])
                    if idx + 1 < len(slides)
                    else duration
                )
                # concat demuxer holds each frame for the specified duration.
                f.write(f"file '{frames[idx]}'\n")
                f.write(f"duration {max(.001, end-start):.6f}\n")
            f.write(f"file '{frames[-1]}'\n")
        destination.parent.mkdir(parents=True, exist_ok=True)
        part = destination.with_name(destination.stem + ".partial.mp4")
        try:
            cmd = [
                ffmpeg_bin("ffmpeg"),
                "-nostdin",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-safe",
                "0",
                "-f",
                "concat",
                "-i",
                str(concat),
                "-i",
                str(root / "audio.opus"),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-vf",
                "fps=25,scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                str(crf),
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-t",
                f"{duration:.6f}",
                "-movflags",
                "+faststart",
                str(part),
            ]
            progress(0.4, "Rendering MP4")
            job.run(
                cmd,
                progress=lambda p, msg: progress(0.4 + 0.6 * p, msg),
                duration=duration,
            )
            job.check()
            part.replace(destination)
        finally:
            part.unlink(missing_ok=True)
    progress(1.0, f"Created {destination}")
    return destination


def main(argv: list[str] | None=None) -> int:
    """Parse exporter CLI arguments and return a process exit status."""
    parser = argparse.ArgumentParser(description="Export an SCV lecture to MP4")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--crf", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        export_video(
            args.input,
            args.output,
            crf=args.crf,
            progress=lambda p, msg: print(f"\r{p:.0%} {msg}", end="", flush=True),
        )
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

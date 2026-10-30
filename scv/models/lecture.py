"""Runtime lecture models independent from archive serialization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class Slide:
    """A validated lecture slide."""

    time: float
    image: PurePosixPath
    text: str | None = None


@dataclass(frozen=True)
class Lecture:
    """Immutable runtime representation of an SCV lecture manifest."""

    duration_seconds: float
    slides: tuple[Slide, ...]
    format_version: int
    title: str | None = None

    @classmethod
    def from_manifest(cls, manifest: dict) -> Lecture:
        """Build a runtime model from a validated archive manifest."""
        slides = tuple(
            Slide(
                time=float(slide["time"]),
                image=PurePosixPath(str(slide["image"])),
                text=slide.get("text"),
            )
            for slide in manifest["slides"]
        )
        return cls(
            duration_seconds=float(manifest["duration_seconds"]),
            slides=slides,
            format_version=int(manifest["format_version"]),
            title=manifest.get("title"),
        )

    @property
    def slide_times(self) -> list[float]:
        """Return slide start times for playback adapters."""
        return [slide.time for slide in self.slides]

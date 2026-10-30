"""Application service for opening and managing an extracted SCV lecture."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import TracebackType
from PIL import Image

from .archive import LectureManifest, SlideManifest, extract, frame_at, inspect
from scv.models.lecture import Lecture, Slide


class LectureSession:
    """Own a validated SCV manifest and its temporary extracted resources."""

    def __init__(
        self,
        source_path: Path,
        manifest: LectureManifest,
        temporary_directory: tempfile.TemporaryDirectory[str],
    ) -> None:
        """Keep the validated manifest and own its extracted temporary files."""
        self.source_path = source_path
        self.manifest = manifest
        self.lecture = Lecture.from_manifest(manifest)
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = (
            temporary_directory
        )
        self.root = Path(temporary_directory.name)

    @classmethod
    def open(cls, source: Path | str) -> LectureSession:
        """Validate and extract an SCV archive into an isolated temp directory."""
        source_path = Path(source).expanduser().resolve()
        manifest = inspect(source_path)
        temporary_directory = tempfile.TemporaryDirectory(prefix="scv_player_")
        try:
            extract(source_path, temporary_directory.name)
        except Exception:
            temporary_directory.cleanup()
            raise
        return cls(source_path, manifest, temporary_directory)

    @property
    def slides(self) -> list[SlideManifest]:
        """Return the manifest slide entries."""
        return self.manifest["slides"]

    @property
    def slide_models(self) -> tuple[Slide, ...]:
        """Return immutable runtime slide models."""
        return self.lecture.slides

    @property
    def slide_times(self) -> list[float]:
        """Return slide start times in seconds."""
        return self.lecture.slide_times

    @property
    def duration_seconds(self) -> float:
        """Return the validated audio duration."""
        return self.lecture.duration_seconds

    @property
    def audio_path(self) -> Path:
        """Return the extracted audio path."""
        return self.root / "audio.opus"

    def frame_at(self, position_seconds: float) -> Image.Image:
        """Load the slide image active at the given playback position."""
        return frame_at(self.manifest, self.root, position_seconds)

    def close(self) -> None:
        """Release extracted resources; safe to call more than once."""
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None

    def __enter__(self) -> LectureSession:
        """Return this session for use in a context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release the extracted lecture files when the context ends."""
        self.close()

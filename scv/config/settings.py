"""Application configuration model with validation and defaults."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path


@dataclass
class AppSettings:
    """Strongly-typed application settings model."""

    # General / Localization
    language: str = "en"  # "en", "it", "fr"
    theme: str = "system"  # "system", "dark", "light"

    # Recent files
    recent_files: list[str] = field(default_factory=list)
    max_recent_files: int = 10

    # Player defaults
    default_playback_rate: float = 1.0
    seek_step_seconds: int = 5
    note_display_duration_seconds: int = 20
    auto_save_notes: bool = False
    resume_playback: bool = True

    # Encoder & Exporter defaults
    default_output_dir: str = field(default_factory=lambda: str(Path.home() / "Videos"))
    default_preset: str = "Balanced"
    default_crf: int = 20
    default_ocr_lang: str = "eng"

    def validate(self):
        """Sanitize settings values to bounded ranges."""
        if self.language not in ("en", "it", "fr"):
            self.language = "en"
        if self.theme not in ("system", "dark", "light"):
            self.theme = "system"
        if not (0.25 <= self.default_playback_rate <= 4.0):
            self.default_playback_rate = 1.0
        if not (1 <= self.seek_step_seconds <= 60):
            self.seek_step_seconds = 5
        if not (5 <= self.note_display_duration_seconds <= 120):
            self.note_display_duration_seconds = 20
        if not isinstance(self.resume_playback, bool):
            self.resume_playback = True
        if not (0 <= self.default_crf <= 51):
            self.default_crf = 20

    def add_recent_file(self, path: str | Path):
        """Prepend a file path to recent files list and enforce limit."""
        path_str = str(Path(path).expanduser().resolve())
        filtered = [p for p in self.recent_files if p != path_str]
        self.recent_files = [path_str] + filtered[: self.max_recent_files - 1]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AppSettings:
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        instance = cls(**filtered)
        instance.validate()
        return instance

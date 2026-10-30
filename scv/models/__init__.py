"""Data models and business logic abstractions for SCV."""

from typing import Any

from .geometry import NormalizedPoint, distance_point_to_segment
from .tools import DrawingTool
from .study import Bookmark, Note, AnnotationStroke, StudyDocument
from .encoding import EncodeTask, EncodeTaskStatus
from .timeline import SlideTimeline
from .lecture import Lecture, Slide
from .playback import PlaybackState

__all__ = [
    "NormalizedPoint",
    "distance_point_to_segment",
    "DrawingTool",
    "Bookmark",
    "Note",
    "AnnotationStroke",
    "StudyDocument",
    "EncodeTask",
    "EncodeTaskStatus",
    "SlideTimeline",
    "Lecture",
    "Slide",
    "PlaybackState",
    "StudyCoordinator",
]


def __getattr__(name: str) -> Any:
    """Provide a backwards-compatible lazy import for the moved coordinator."""
    if name == "StudyCoordinator":
        from scv.application import StudyCoordinator

        return StudyCoordinator
    raise AttributeError(name)

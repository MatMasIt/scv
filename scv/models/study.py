"""Domain models for bookmarks, notes, and slide annotations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from scv.bookmarks import load as load_bookmarks, save as save_bookmarks
from .geometry import NormalizedPoint, distance_point_to_segment
from .tools import DrawingTool


@dataclass
class Bookmark:
    """A named point in time within a lecture."""

    time: float
    label: str

    def to_dict(self) -> dict[str, object]:
        """Serialize this study item to JSON-compatible data."""
        return {"time": round(float(self.time), 3), "label": self.label.strip()}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Bookmark:
        """Create this study item from decoded sidecar data."""
        return cls(time=float(data.get("time", 0.0)), label=str(data.get("label", "")))


@dataclass
class Note:
    """A timestamped study note with optional in-video overlay banner."""

    time: float
    label: str
    show: bool = True

    def to_dict(self) -> dict[str, object]:
        """Serialize this study item to JSON-compatible data."""
        return {
            "time": round(float(self.time), 3),
            "label": self.label.strip(),
            "show": bool(self.show),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Note:
        """Create this study item from decoded sidecar data."""
        return cls(
            time=float(data.get("time", 0.0)),
            label=str(data.get("label", "")),
            show=bool(data.get("show", True)),
        )


@dataclass
class AnnotationStroke:
    """A freehand pen or highlighter stroke drawn over a slide."""

    points: list[NormalizedPoint]
    tool: DrawingTool
    label: str | None = None

    @property
    def color(self) -> str:
        """Return the active drawing tool’s color."""
        return self.tool.color

    @property
    def width(self) -> int:
        """Return the active drawing tool’s stroke width."""
        return self.tool.stroke_width

    @property
    def kind(self) -> str:
        """Return the annotation kind used by the sidecar format."""
        return self.tool.kind

    @property
    def style(self) -> str:
        """Return the drawing tool style identifier."""
        return self.tool.style_id

    def hit_test(self, point: NormalizedPoint, threshold: float) -> bool:
        """Check if ``point`` is within ``threshold`` distance of any stroke segment."""
        if len(self.points) < 2:
            return False
        for start, end in zip(self.points, self.points[1:]):
            if distance_point_to_segment(point, start, end) <= threshold:
                return True
        return False

    def to_dict(self) -> dict[str, object]:
        """Serialize this study item to JSON-compatible data."""
        data: dict[str, object] = {
            "kind": self.kind,
            "style": self.style,
            "color": self.color,
            "width": self.width,
            "points": [p.to_list() for p in self.points],
        }
        if self.label:
            data["label"] = self.label
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AnnotationStroke:
        """Create this study item from decoded sidecar data."""
        tool = DrawingTool.from_style(data.get("style", data.get("kind")))
        pts = [
            NormalizedPoint.from_tuple_or_list(pt)
            for pt in data.get("points", [])
            if len(pt) >= 2
        ]
        return cls(points=pts, tool=tool, label=data.get("label"))


class StudyDocument:
    """Domain document for study data, persistence, and dirty state."""

    def __init__(self, source_path: Path | str | None = None) -> None:
        """Initialize an empty document or load one from its sidecar."""
        self.source_path = (
            Path(source_path).expanduser().resolve() if source_path else None
        )
        self.bookmarks: list[Bookmark] = []
        self.notes: list[Note] = []
        self.annotations: dict[int, list[AnnotationStroke]] = {}
        self.dirty: bool = False

        if self.source_path:
            self.reload()

    # --- Persistence ---
    def reload(self) -> None:
        """Reload document state from its sidecar file."""
        if not self.source_path:
            return
        try:
            raw = load_bookmarks(self.source_path)
            self._load_from_dict(raw)
        finally:
            self.dirty = False

    def save(self) -> None:
        """Serialize and atomically save to sidecar storage."""
        if not self.source_path:
            return
        save_bookmarks(self.source_path, self.to_dict())
        self.dirty = False

    def to_dict(self) -> dict[str, object]:
        """Serialize to standard JSON-compatible sidecar format."""
        anno_dict: dict[str, list[dict[str, object]]] = {}
        for slide_idx, strokes in sorted(self.annotations.items()):
            if strokes:
                anno_dict[str(slide_idx)] = [s.to_dict() for s in strokes]

        return {
            "version": 1,
            "bookmarks": [b.to_dict() for b in self.bookmarks],
            "notes": [n.to_dict() for n in self.notes],
            "annotations": anno_dict,
        }

    def _load_from_dict(self, raw: Mapping[str, Any]) -> None:
        """Replace document contents with decoded sidecar data."""
        self.bookmarks = [Bookmark.from_dict(b) for b in raw.get("bookmarks", [])]
        self.notes = [Note.from_dict(n) for n in raw.get("notes", [])]
        self.annotations = {}
        for slide_str, strokes in raw.get("annotations", {}).items():
            try:
                slide_idx = int(slide_str)
                self.annotations[slide_idx] = [
                    AnnotationStroke.from_dict(s) for s in strokes
                ]
            except ValueError:
                continue

    # --- Bookmarks ---
    def add_bookmark(self, time_seconds: float, label: str) -> Bookmark:
        """Add a bookmark and mark the document dirty."""
        b = Bookmark(time=time_seconds, label=label.strip())
        self.bookmarks.append(b)
        self.dirty = True
        return b

    def edit_bookmark(self, index: int, label: str) -> None:
        """Change a bookmark label and mark the document dirty."""
        if 0 <= index < len(self.bookmarks):
            self.bookmarks[index].label = label.strip()
            self.dirty = True

    def delete_bookmark(self, index: int) -> None:
        """Remove a bookmark and mark the document dirty."""
        if 0 <= index < len(self.bookmarks):
            self.bookmarks.pop(index)
            self.dirty = True

    # --- Notes ---
    def add_note(self, time_seconds: float, label: str, show: bool = True) -> Note:
        """Add a note and mark the document dirty."""
        n = Note(time=time_seconds, label=label.strip(), show=show)
        self.notes.append(n)
        self.dirty = True
        return n

    def edit_note(self, index: int, label: str) -> None:
        """Change a note label and mark the document dirty."""
        if 0 <= index < len(self.notes):
            self.notes[index].label = label.strip()
            self.dirty = True

    def set_note_visibility(self, index: int, show: bool) -> None:
        """Change whether a note is shown during playback."""
        if 0 <= index < len(self.notes):
            self.notes[index].show = bool(show)
            self.dirty = True

    def delete_note(self, index: int) -> None:
        """Remove a note and mark the document dirty."""
        if 0 <= index < len(self.notes):
            self.notes.pop(index)
            self.dirty = True

    def active_notes_at(
        self, position_seconds: float, window_seconds: float = 20.0
    ) -> list[tuple[int, Note]]:
        """Return (index, note) tuples for notes active at ``position_seconds``."""
        return [
            (idx, note)
            for idx, note in enumerate(self.notes)
            if note.show and (note.time <= position_seconds <= note.time + window_seconds)
        ]

    # --- Slide Annotations ---
    def get_slide_annotations(self, slide_index: int) -> list[AnnotationStroke]:
        """Return the strokes stored for one slide."""
        return self.annotations.get(slide_index, [])

    def set_slide_annotations(
        self, slide_index: int, strokes: list[AnnotationStroke]
    ) -> None:
        """Replace the strokes stored for one slide."""
        current = self.annotations.get(slide_index, [])
        if current == strokes:
            return
        if strokes:
            self.annotations[slide_index] = list(strokes)
        else:
            self.annotations.pop(slide_index, None)
        self.dirty = True

    def clear_slide_annotations(self, slide_index: int) -> None:
        """Remove every stroke stored for one slide."""
        if slide_index in self.annotations:
            del self.annotations[slide_index]
            self.dirty = True

    def delete_annotation(self, slide_index: int, annotation_index: int) -> None:
        """Remove one stroke from a slide."""
        strokes = self.annotations.get(slide_index, [])
        if 0 <= annotation_index < len(strokes):
            strokes.pop(annotation_index)
            self.dirty = True
            if not strokes:
                self.annotations.pop(slide_index, None)

    def update_annotation_tool(
        self, slide_index: int, annotation_index: int, tool: DrawingTool
    ) -> None:
        """Change the drawing tool saved on one stroke."""
        strokes = self.annotations.get(slide_index, [])
        if 0 <= annotation_index < len(strokes):
            strokes[annotation_index].tool = tool
            strokes[annotation_index].label = self.annotation_label(
                strokes[annotation_index], slide_index, annotation_index
            )
            self.dirty = True

    @staticmethod
    def annotation_label(
        stroke: AnnotationStroke, slide_index: int, annotation_index: int
    ) -> str:
        """Format a readable label for a saved slide annotation."""
        if stroke.label:
            return stroke.label
        return f"Slide {slide_index + 1} — {stroke.tool.display_name} {annotation_index + 1}"

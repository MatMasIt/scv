"""Application service for study-document workflows."""

from __future__ import annotations

from pathlib import Path

from scv.models.study import AnnotationStroke, StudyDocument


class StudyCoordinator:
    """Coordinate study persistence without depending on a UI toolkit."""

    def __init__(self, source_path: Path | None = None):
        self.document = StudyDocument(source_path)

    @property
    def dirty(self) -> bool:
        """Return whether the current document has unsaved changes."""
        return self.document.dirty

    def attach(self, source_path: Path | None):
        """Load the study document associated with a lecture."""
        self.document = StudyDocument(source_path)

    def save(self):
        """Persist the current study document."""
        self.document.save()

    def reload(self):
        """Reload the current study document from disk."""
        self.document.reload()

    def sync_annotations(self, slide_index: int, strokes: list[AnnotationStroke]):
        """Replace annotations on one slide."""
        self.document.set_slide_annotations(slide_index, strokes)

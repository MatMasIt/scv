"""Tests for StudyDocument manager and sidecar persistence."""

import tempfile
import unittest
from pathlib import Path

from scv.models import (
    StudyDocument,
    StudyCoordinator,
    Bookmark,
    Note,
    AnnotationStroke,
    DrawingTool,
    NormalizedPoint,
)


class TestStudyDocument(unittest.TestCase):
    """Test study document CRUD, sidecar roundtrip, and dirty flag tracking."""

    def test_empty_document(self):
        doc = StudyDocument()
        self.assertEqual(doc.bookmarks, [])
        self.assertEqual(doc.notes, [])
        self.assertEqual(doc.annotations, {})
        self.assertFalse(doc.dirty)

    def test_study_coordinator_manages_document_lifecycle(self):
        coordinator = StudyCoordinator()
        self.assertFalse(coordinator.dirty)
        coordinator.document.add_bookmark(2.0, "Review")
        self.assertTrue(coordinator.dirty)
        coordinator.attach(None)
        self.assertFalse(coordinator.dirty)

    def test_bookmarks_crud(self):
        doc = StudyDocument()
        b = doc.add_bookmark(12.5, "Introduction")
        self.assertTrue(doc.dirty)
        self.assertEqual(len(doc.bookmarks), 1)
        self.assertEqual(doc.bookmarks[0].time, 12.5)
        self.assertEqual(doc.bookmarks[0].label, "Introduction")

        doc.edit_bookmark(0, "Introduction to Algorithms")
        self.assertEqual(doc.bookmarks[0].label, "Introduction to Algorithms")

        doc.delete_bookmark(0)
        self.assertEqual(len(doc.bookmarks), 0)

    def test_notes_crud_and_visibility(self):
        doc = StudyDocument()
        n = doc.add_note(45.0, "Key formula: E = mc^2", show=True)
        self.assertEqual(len(doc.notes), 1)
        self.assertTrue(doc.notes[0].show)

        # Active note lookup
        active = doc.active_notes_at(50.0, window_seconds=20.0)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0][1].label, "Key formula: E = mc^2")

        # Outside window
        outside = doc.active_notes_at(70.0, window_seconds=20.0)
        self.assertEqual(len(outside), 0)

        # Toggle visibility
        doc.set_note_visibility(0, False)
        self.assertFalse(doc.notes[0].show)
        self.assertEqual(len(doc.active_notes_at(50.0)), 0)

        # Delete note
        doc.delete_note(0)
        self.assertEqual(len(doc.notes), 0)

    def test_annotations_crud_and_hit_testing(self):
        doc = StudyDocument()
        stroke = AnnotationStroke(
            points=[NormalizedPoint(0.1, 0.1), NormalizedPoint(0.2, 0.2)],
            tool=DrawingTool.PEN,
        )
        doc.set_slide_annotations(0, [stroke])
        self.assertEqual(len(doc.get_slide_annotations(0)), 1)
        self.assertEqual(doc.get_slide_annotations(1), [])

        # Hit testing
        self.assertTrue(stroke.hit_test(NormalizedPoint(0.15, 0.15), threshold=0.01))
        self.assertFalse(stroke.hit_test(NormalizedPoint(0.9, 0.9), threshold=0.01))

        # Label generation
        label = doc.annotation_label(stroke, 0, 0)
        self.assertIn("Slide 1", label)
        self.assertIn("Pen", label)

        # Tool style update
        doc.update_annotation_tool(0, 0, DrawingTool.HIGHLIGHT_YELLOW)
        updated = doc.get_slide_annotations(0)[0]
        self.assertEqual(updated.tool, DrawingTool.HIGHLIGHT_YELLOW)
        self.assertEqual(updated.kind, "highlight")
        self.assertEqual(updated.style, "highlight-yellow")
        self.assertEqual(updated.width, 18)

        # Clear annotations
        doc.clear_slide_annotations(0)
        self.assertEqual(doc.get_slide_annotations(0), [])

    def test_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            scv_file = Path(tmp) / "lecture.scv"
            doc = StudyDocument(scv_file)
            doc.add_bookmark(10.0, "Bookmark 1")
            doc.add_note(15.0, "Note 1")
            doc.set_slide_annotations(
                0,
                [
                    AnnotationStroke(
                        points=[NormalizedPoint(0, 0), NormalizedPoint(1, 1)],
                        tool=DrawingTool.PEN,
                    )
                ],
            )
            doc.save()

            self.assertFalse(doc.dirty)

            # Reload into another instance
            doc2 = StudyDocument(scv_file)
            self.assertEqual(len(doc2.bookmarks), 1)
            self.assertEqual(doc2.bookmarks[0].label, "Bookmark 1")
            self.assertEqual(len(doc2.notes), 1)
            self.assertEqual(doc2.notes[0].label, "Note 1")
            self.assertEqual(len(doc2.get_slide_annotations(0)), 1)
            self.assertEqual(doc2.get_slide_annotations(0)[0].tool, DrawingTool.PEN)


if __name__ == "__main__":
    unittest.main()

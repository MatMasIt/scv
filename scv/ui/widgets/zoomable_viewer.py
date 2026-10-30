"""Interactive slide canvas widget with zoom, pan, and annotation tools."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QPaintEvent,
    QMouseEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QLabel, QWidget

from scv.models.geometry import NormalizedPoint
from scv.models.study import AnnotationStroke
from scv.models.tools import DrawingTool
from scv.i18n import t
from .transform import ViewportTransform


class ZoomableViewer(QLabel):
    """Display a slide with cursor-centered zooming, drag panning, and drawing."""

    annotationClicked = Signal(int)
    annotationCompleted = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the slide canvas, navigation state, and annotation tools."""
        super().__init__(t("open_scv_to_begin"), parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: #111827; color: #f9fafb; border-radius: 6px;")

        self._pixmap = QPixmap()
        self._zoom: float = 1.0
        self._offset = QPointF()

        self._active_tool = DrawingTool.SELECT_PAN
        self._drag_start: QPointF | None = None
        self._current_stroke_points: list[NormalizedPoint] | None = None

        self.annotations: list[AnnotationStroke] = []
        self.selected_annotation: int | None = None

        self.setMouseTracking(True)
        self.setToolTip(t("viewer_tooltip"))

    @property
    def transform(self) -> ViewportTransform:
        """Return the current mapping between image and widget coordinates."""
        return ViewportTransform(
            widget_size=self.size(),
            image_size=self._pixmap.size(),
            zoom=self._zoom,
            offset=self._offset,
        )

    def setPixmap(self, pixmap: QPixmap) -> None:
        """Set the slide image and schedule the viewer to repaint."""
        self._pixmap = pixmap
        self.update()

    def set_annotations(
        self,
        annotations: Sequence[AnnotationStroke | Mapping[str, object]] | None,
    ) -> None:
        """Replace annotations with typed strokes."""
        typed_annotations = []
        for a in annotations or []:
            if isinstance(a, AnnotationStroke):
                typed_annotations.append(a)
            elif isinstance(a, dict):
                typed_annotations.append(AnnotationStroke.from_dict(a))
        self.annotations = typed_annotations
        self.selected_annotation = None
        self.update()

    def set_selected_annotation(self, index: int | None) -> None:
        """Select an annotation by index, or clear the selection with None."""
        self.selected_annotation = index
        self.update()

    def set_annotation_mode(self, mode: DrawingTool | str | None) -> None:
        """Choose a drawing tool or return to selection and panning mode."""
        if isinstance(mode, DrawingTool):
            self._active_tool = mode
        elif isinstance(mode, str):
            self._active_tool = DrawingTool.from_style(mode)
        else:
            self._active_tool = DrawingTool.SELECT_PAN

        cursor = (
            Qt.CursorShape.CrossCursor
            if self._active_tool.is_drawing_tool
            else Qt.CursorShape.ArrowCursor
        )
        self.setCursor(cursor)

    def clear_annotations(self) -> None:
        """Remove all strokes and clear the selected annotation."""
        self.annotations.clear()
        self.selected_annotation = None
        self.update()

    def reset_view(self) -> None:
        """Reset zoom and panning to the image-fit view."""
        self._zoom = 1.0
        self._offset = QPointF()
        self.update()

    def zoom_in(self) -> None:
        """Increase zoom around the center of the widget."""
        self._set_zoom(self._zoom * 1.25, QPointF(self.rect().center()))

    def zoom_out(self) -> None:
        """Decrease zoom around the center of the widget."""
        self._set_zoom(self._zoom / 1.25, QPointF(self.rect().center()))

    def _set_zoom(self, zoom: float, anchor: QPointF) -> None:
        """Set a bounded zoom factor while keeping the anchor point fixed."""
        trans = self.transform
        old_scale = trans.scale
        new_zoom = max(1.0, min(8.0, zoom))
        new_scale = trans.base_scale * new_zoom
        if old_scale > 0:
            image_point = (anchor - QPointF(self.rect().center()) - self._offset) / old_scale
            self._offset = anchor - QPointF(self.rect().center()) - image_point * new_scale
        self._zoom = new_zoom
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the widget’s current visual state."""
        if self._pixmap.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        trans = self.transform

        # Let QPainter scale the source image instead of allocating a new pixmap
        # for every repaint (mouse movement can trigger many repaints per second).
        painter.drawPixmap(
            trans.image_rect,
            self._pixmap,
            QRectF(self._pixmap.rect()),
        )

        # Draw persistent and in-progress strokes
        all_strokes = list(self.annotations)
        if self._current_stroke_points and self._active_tool.is_drawing_tool:
            all_strokes.append(
                AnnotationStroke(points=self._current_stroke_points, tool=self._active_tool)
            )

        for index, stroke in enumerate(all_strokes):
            if len(stroke.points) < 2:
                continue

            points = [trans.to_widget(p) for p in stroke.points]
            color = QColor(stroke.color)
            color.setAlpha(stroke.tool.opacity)

            width_boost = 3 if index == self.selected_annotation else 0
            effective_width = (stroke.width + width_boost) * trans.scale

            pen = QPen(
                color,
                effective_width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(pen)
            painter.drawPolyline(points)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle pointer-wheel input for the viewer."""
        delta = event.angleDelta().y()
        factor = 1.2 if delta > 0 else (1.0 / 1.2)
        self._set_zoom(self._zoom * factor, event.position())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle a pointer press on this widget."""
        if event.button() != Qt.MouseButton.LeftButton or self._pixmap.isNull():
            super().mousePressEvent(event)
            return

        # 1. Drawing mode
        if self._active_tool.is_drawing_tool:
            norm_pt = self.transform.to_normalized(event.position())
            if norm_pt:
                self._current_stroke_points = [norm_pt]
                self.update()
                event.accept()
                return

        # 2. Hit testing existing annotations
        clicked_idx = self._annotation_at(event.position())
        if clicked_idx is not None:
            self.set_selected_annotation(clicked_idx)
            self.annotationClicked.emit(clicked_idx)
            event.accept()
            return

        # 3. Canvas panning
        self._drag_start = event.position()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # 1. Extending active drawing stroke
        """Handle pointer movement over this widget."""
        if self._current_stroke_points is not None:
            norm_pt = self.transform.to_normalized(event.position())
            if norm_pt:
                self._current_stroke_points.append(norm_pt)
                self.update()
            event.accept()
            return

        # 2. Canvas panning
        if self._drag_start is not None:
            self._offset += event.position() - self._drag_start
            self._drag_start = event.position()
            self.update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle a pointer release on this widget."""
        if event.button() == Qt.MouseButton.LeftButton:
            # 1. Complete drawing stroke
            if self._current_stroke_points is not None:
                if len(self._current_stroke_points) > 1:
                    new_stroke = AnnotationStroke(
                        points=self._current_stroke_points,
                        tool=self._active_tool,
                    )
                    self.annotations.append(new_stroke)
                    self.annotationCompleted.emit()
                self._current_stroke_points = None
                self.update()
                event.accept()
                return

            # 2. Release canvas pan
            if self._drag_start is not None:
                self._drag_start = None
                cursor = (
                    Qt.CursorShape.CrossCursor
                    if self._active_tool.is_drawing_tool
                    else Qt.CursorShape.ArrowCursor
                )
                self.setCursor(cursor)
                event.accept()
                return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle a double-click on this widget."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.reset_view()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def _annotation_at(self, position: QPointF) -> int | None:
        """Return the topmost stroke hit by the widget-space pointer position."""
        trans = self.transform
        point = trans.to_normalized(position)
        if not point:
            return None

        threshold = trans.hit_threshold(pixel_radius=8.0)
        # Search backward from top-most stroke to bottom-most
        for index in range(len(self.annotations) - 1, -1, -1):
            if self.annotations[index].hit_test(point, threshold):
                return index
        return None

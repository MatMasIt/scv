"""Coordinate transformation abstraction between widget and slide image."""

from __future__ import annotations
from dataclasses import dataclass
from PySide6.QtCore import QPointF, QSize, QRectF
from scv.models.geometry import NormalizedPoint


@dataclass(frozen=True)
class ViewportTransform:
    """Handles mapping between widget canvas space and normalized slide space."""

    widget_size: QSize
    image_size: QSize
    zoom: float
    offset: QPointF

    @property
    def is_valid(self) -> bool:
        return (
            not self.widget_size.isEmpty()
            and not self.image_size.isEmpty()
            and self.image_size.width() > 0
            and self.image_size.height() > 0
        )

    @property
    def base_scale(self) -> float:
        if not self.is_valid:
            return 1.0
        return min(
            self.widget_size.width() / self.image_size.width(),
            self.widget_size.height() / self.image_size.height(),
        )

    @property
    def scale(self) -> float:
        return self.base_scale * self.zoom

    @property
    def rendered_size(self) -> QSize:
        if not self.is_valid:
            return QSize(0, 0)
        return QSize(
            max(1, round(self.image_size.width() * self.scale)),
            max(1, round(self.image_size.height() * self.scale)),
        )

    @property
    def top_left(self) -> QPointF:
        if not self.is_valid:
            return QPointF(0, 0)
        center = QPointF(self.widget_size.width() / 2.0, self.widget_size.height() / 2.0)
        half_render = QPointF(self.rendered_size.width() / 2.0, self.rendered_size.height() / 2.0)
        return center - half_render + self.offset

    @property
    def image_rect(self) -> QRectF:
        return QRectF(self.top_left, self.rendered_size)

    def to_normalized(self, widget_pos: QPointF) -> NormalizedPoint | None:
        """Map widget pixel coordinate to normalized [0, 1] slide space."""
        if not self.is_valid:
            return None
        size = self.rendered_size
        top_left = self.top_left
        x = (widget_pos.x() - top_left.x()) / size.width()
        y = (widget_pos.y() - top_left.y()) / size.height()
        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
            return NormalizedPoint(x, y)
        return None

    def to_widget(self, norm_pt: NormalizedPoint) -> QPointF:
        """Map normalized [0, 1] slide point back to widget coordinate."""
        top_left = self.top_left
        return QPointF(
            top_left.x() + norm_pt.x * self.image_size.width() * self.scale,
            top_left.y() + norm_pt.y * self.image_size.height() * self.scale,
        )

    def hit_threshold(self, pixel_radius: float = 8.0) -> float:
        """Return hit detection tolerance in normalized space."""
        if not self.is_valid:
            return 0.05
        size = self.rendered_size
        return max(pixel_radius / size.width(), pixel_radius / size.height())


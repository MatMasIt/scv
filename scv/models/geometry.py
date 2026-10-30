"""Geometry abstractions for slide canvas coordinates and hit testing."""

from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class NormalizedPoint:
    """A point in normalized slide coordinates [0.0, 1.0]."""

    x: float
    y: float

    def distance_to(self, other: NormalizedPoint) -> float:
        """Calculate Euclidean distance between two points."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def to_tuple(self) -> tuple[float, float]:
        """Return the point coordinates as an immutable pair."""
        return (self.x, self.y)

    def to_list(self) -> list[float]:
        """Return rounded point coordinates as a JSON-friendly list."""
        return [round(self.x, 5), round(self.y, 5)]

    @classmethod
    def from_tuple_or_list(cls, coords: tuple[float, float] | list[float]) -> NormalizedPoint:
        """Create a normalized point from a coordinate pair."""
        return cls(float(coords[0]), float(coords[1]))


def distance_point_to_segment(
    point: NormalizedPoint, start: NormalizedPoint, end: NormalizedPoint
) -> float:
    """Calculate the shortest distance from a point to a line segment."""
    dx = end.x - start.x
    dy = end.y - start.y
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return point.distance_to(start)

    # Project point onto the segment line parameterized by t in [0, 1]
    t = max(0.0, min(1.0, ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_squared))
    projection = NormalizedPoint(start.x + t * dx, start.y + t * dy)
    return point.distance_to(projection)


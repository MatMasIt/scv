"""Tests for geometry and viewport coordinate transformations."""

import unittest
from scv.models.geometry import NormalizedPoint, distance_point_to_segment


class TestGeometry(unittest.TestCase):
    def test_normalized_point_distance(self):
        p1 = NormalizedPoint(0.0, 0.0)
        p2 = NormalizedPoint(3.0, 4.0)
        self.assertAlmostEqual(p1.distance_to(p2), 5.0)

    def test_distance_point_to_segment(self):
        start = NormalizedPoint(0.0, 0.0)
        end = NormalizedPoint(10.0, 0.0)

        # Point directly on segment
        on_segment = NormalizedPoint(5.0, 0.0)
        self.assertAlmostEqual(distance_point_to_segment(on_segment, start, end), 0.0)

        # Point perpendicular to segment midpoint
        above = NormalizedPoint(5.0, 2.0)
        self.assertAlmostEqual(distance_point_to_segment(above, start, end), 2.0)

        # Point past segment end
        beyond_end = NormalizedPoint(13.0, 4.0)
        self.assertAlmostEqual(distance_point_to_segment(beyond_end, start, end), 5.0)


if __name__ == "__main__":
    unittest.main()


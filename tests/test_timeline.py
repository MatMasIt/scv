import unittest

from scv.models import SlideTimeline


class TestSlideTimeline(unittest.TestCase):
    def test_current_slide_is_position_based(self):
        timeline = SlideTimeline([0, 4.5, 10])
        self.assertEqual(timeline.current_index(0), 0)
        self.assertEqual(timeline.current_index(9.9), 1)
        self.assertEqual(timeline.current_index(10), 2)

    def test_adjacent_slide_is_bounded(self):
        timeline = SlideTimeline([0, 4.5, 10])
        self.assertEqual(timeline.adjacent_index(0, -1), 0)
        self.assertEqual(timeline.adjacent_index(5, 1), 2)

    def test_invalid_timestamps_are_rejected(self):
        with self.assertRaises(ValueError):
            SlideTimeline([0, -1])
        with self.assertRaises(ValueError):
            SlideTimeline([2, 1])

    def test_position_for_invalid_index_returns_none(self):
        timeline = SlideTimeline([0])
        self.assertIsNone(timeline.position_for(-1))
        self.assertIsNone(timeline.position_for(1))


if __name__ == "__main__":
    unittest.main()

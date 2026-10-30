"""Tests for UI formatting and utility functions."""

import unittest
from scv.ui.common.utils import fmt_time


class TestUIUtils(unittest.TestCase):
    """Test formatting helper functions."""

    def test_fmt_time(self):
        self.assertEqual(fmt_time(0), "00:00:00")
        self.assertEqual(fmt_time(5000), "00:00:05")
        self.assertEqual(fmt_time(65000), "00:01:05")
        self.assertEqual(fmt_time(3665000), "01:01:05")
        self.assertEqual(fmt_time(-1000), "00:00:00")


if __name__ == "__main__":
    unittest.main()

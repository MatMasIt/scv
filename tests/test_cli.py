"""Tests for the SCV CLI interface."""

import unittest
from unittest.mock import patch
from scv.cli import main


class TestCLI(unittest.TestCase):
    """Test CLI commands and options parsing."""

    def test_help_no_display(self):
        with patch.dict("os.environ", {}, clear=True):
            # No args should print help and return 0
            with patch("sys.stdout"):
                self.assertEqual(main([]), 0)

    def test_version(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()

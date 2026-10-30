import tempfile
import unittest
from pathlib import Path

from scv.config.manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    def test_unknown_setting_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = ConfigManager(Path(tmp) / "settings.json")
            with self.assertRaises(AttributeError):
                manager.update(unknown_setting=True)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path
from unittest.mock import patch

from scv.application import EncodingService, ExportService
from scv.core import Settings
from scv.models import EncodeTask


class TestApplicationServices(unittest.TestCase):
    def test_encoding_service_updates_task_lifecycle(self):
        task = EncodeTask(Path("input.mp4"), Path("output.scv"))
        with patch("scv.application.encoding_service.encode", return_value={}):
            manifest = EncodingService().encode_task(task, settings=Settings())
        self.assertEqual(manifest, {})
        self.assertEqual(task.status.value, "completed")

    def test_encoding_service_records_failure(self):
        task = EncodeTask(Path("input.mp4"), Path("output.scv"))
        with patch(
            "scv.application.encoding_service.encode",
            side_effect=RuntimeError("encoder failed"),
        ):
            with self.assertRaises(RuntimeError):
                EncodingService().encode_task(task, settings=Settings())
        self.assertEqual(task.error, "encoder failed")

    def test_export_service_delegates_to_core_export(self):
        with patch(
            "scv.application.export_service.export_video",
            return_value=Path("output.mp4"),
        ) as export:
            result = ExportService().export("input.scv", "output.mp4")
        export.assert_called_once()
        self.assertEqual(result, Path("output.mp4"))


if __name__ == "__main__":
    unittest.main()

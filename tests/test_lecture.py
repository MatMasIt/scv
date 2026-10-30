import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from scv.core import LectureSession


class TestLectureSession(unittest.TestCase):
    def test_open_exposes_runtime_lecture_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            slides = base / "slides"
            slides.mkdir()
            image = slides / "00001.webp"
            Image.new("RGB", (4, 4), "white").save(image)
            archive = base / "lecture.scv"
            manifest = {
                "format": "SCV",
                "format_version": 1,
                "duration_seconds": 4,
                "audio": {"file": "audio.opus"},
                "slides": [{"time": 0, "image": "slides/00001.webp"}],
            }
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("manifest.json", json.dumps(manifest))
                output.writestr("audio.opus", b"audio")
                output.write(image, "slides/00001.webp")

            session = LectureSession.open(archive)
            root = session.root
            self.assertEqual(
                session.lecture.slides[0].image.as_posix(),
                "slides/00001.webp",
            )
            self.assertEqual(session.slide_times, [0.0])
            self.assertEqual(session.duration_seconds, 4.0)
            self.assertTrue(session.audio_path.is_file())
            session.close()
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()

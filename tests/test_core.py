import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from scv.core import inspect, frame_at, Settings
from scv.bookmarks import load, save, sidecar_path

class Tests(unittest.TestCase):
    """Test validation and round-trip behavior of the SCV core."""

    def test_settings(self):
        """Accept valid settings and reject invalid bitrate values."""
        Settings(bitrate=12, quality=80).validate()
        with self.assertRaises(ValueError): Settings(bitrate=2).validate()

    def test_settings_from_preset(self):
        """Verify preset initialization and override behavior."""
        balanced = Settings.from_preset("Balanced")
        self.assertEqual(balanced.bitrate, 24)
        self.assertEqual(balanced.quality, 80)
        custom = Settings.from_preset("Balanced", bitrate=32, ocr=True)
        self.assertEqual(custom.bitrate, 32)
        self.assertTrue(custom.ocr)
        with self.assertRaises(KeyError):
            Settings.from_preset("NonExistentPreset")

    def test_v1_roundtrip_manifest(self):
        """Validate a minimal archive and reject unsupported versions."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'slides').mkdir()
            im = Image.new('RGB', (100, 60), 'white')
            im.save(base / 'slides/00001.webp')
            manifest = {'format': 'SCV', 'format_version': 1, 'duration_seconds': 25,
                        'audio': {'file': 'audio.opus'}, 'slides': [{'time': 0, 'image': 'slides/00001.webp',
                        'text': 'Optional slide text'}]}
            archive = base / 'test.scv'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('manifest.json', json.dumps(manifest))
                z.writestr('audio.opus', b'fake')
                z.write(base / 'slides/00001.webp', 'slides/00001.webp')
            self.assertEqual(inspect(archive)['format_version'], 1)
            self.assertEqual(frame_at(manifest, base, 12).size, (100, 60))
            bad = base / 'old.scv'
            with zipfile.ZipFile(bad, 'w') as z:
                z.writestr('manifest.json', json.dumps({**manifest, 'format_version': 3}))
                z.writestr('audio.opus', b'fake')
                z.write(base / 'slides/00001.webp', 'slides/00001.webp')
            with self.assertRaises(ValueError): inspect(bad)

    def test_bookmark_sidecar_roundtrip(self):
        """Store bookmarks and annotations without modifying the SCV archive."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'lecture.scv'
            document = {'bookmarks': [{'time': 2.5, 'label': 'Important'}],
                        'notes': [{'time': 4.0, 'label': 'Review this'}],
                        'annotations': {'0': [{'kind': 'pen', 'points': [[0, 0], [1, 1]]}]}}
            self.assertEqual(save(source, document), sidecar_path(source))
            self.assertEqual(sidecar_path(source).name, 'lecture.scvnotes')
            self.assertEqual(load(source), {'version': 1, **document})

if __name__ == '__main__': unittest.main()

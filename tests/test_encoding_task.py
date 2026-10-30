import unittest
from pathlib import Path

from scv.models import EncodeTask, EncodeTaskStatus
from scv.models import PlaybackState


class TestEncodeTask(unittest.TestCase):
    def test_playback_states_are_application_values(self):
        self.assertEqual(PlaybackState.PLAYING.value, "playing")

    def test_task_lifecycle(self):
        task = EncodeTask(Path("input.mp4"), Path("output.scv"))
        self.assertEqual(task.status, EncodeTaskStatus.WAITING)
        task.mark_encoding(0.25)
        self.assertEqual(task.status, EncodeTaskStatus.ENCODING)
        self.assertEqual(task.progress, 0.25)
        task.mark_completed()
        self.assertEqual(task.status, EncodeTaskStatus.COMPLETED)
        self.assertEqual(task.progress, 1.0)

    def test_failed_task_keeps_error(self):
        task = EncodeTask(Path("input.mp4"), Path("output.scv"))
        task.mark_failed("ffmpeg failed")
        self.assertEqual(task.status, EncodeTaskStatus.FAILED)
        self.assertEqual(task.error, "ffmpeg failed")


if __name__ == "__main__":
    unittest.main()

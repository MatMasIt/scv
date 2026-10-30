"""Media playback controller decoupling QMediaPlayer logic from UI views."""

from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from scv.models.timeline import SlideTimeline
from scv.models.playback import PlaybackState


class PlayerController(QObject):
    """Controls lecture media playback, volume, rate, and seeking."""

    positionChanged = Signal(int)
    stateChanged = Signal(str)
    durationChanged = Signal(int)
    errorOccurred = Signal(str)
    slideChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.media = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.media.setAudioOutput(self.audio)
        self.audio.setVolume(0.8)

        self._timeline = SlideTimeline()
        self._current_slide_index: int = -1
        self._pending_position_ms: int | None = None

        self.media.positionChanged.connect(self._on_position_changed)
        self.media.playbackStateChanged.connect(self._on_state_changed)
        self.media.mediaStatusChanged.connect(self._on_media_status_changed)
        self.media.errorOccurred.connect(lambda err, msg: self.errorOccurred.emit(msg))

    def load_audio(self, audio_file: Path | str, slide_times: list[float]):
        """Load audio source file and register slide timestamps in seconds."""
        self.stop()
        self._timeline = SlideTimeline(slide_times)
        self._current_slide_index = -1
        self._pending_position_ms = None
        self.media.setSource(QUrl.fromLocalFile(str(audio_file)))

    def clear(self):
        """Stop and unload current media source."""
        self.stop()
        self.media.setSource(QUrl())
        self._timeline = SlideTimeline()
        self._current_slide_index = -1
        self._pending_position_ms = None

    def play(self):
        self.media.play()

    def pause(self):
        self.media.pause()

    def stop(self):
        self.media.stop()

    def toggle(self):
        """Toggle playback between play and pause."""
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def is_playing(self) -> bool:
        return self.media.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def position(self) -> int:
        """Current playback position in milliseconds."""
        return self.media.position()

    def position_seconds(self) -> float:
        return self.media.position() / 1000.0

    def set_position(self, ms: int):
        position = max(0, ms)
        if self.media.mediaStatus() in (
            QMediaPlayer.MediaStatus.NoMedia,
            QMediaPlayer.MediaStatus.LoadingMedia,
        ):
            self._pending_position_ms = position
            return
        self.media.setPosition(position)

    def seek_by(self, delta_ms: int):
        self.set_position(self.media.position() + delta_ms)

    def set_volume(self, value_0_to_100: int):
        self.audio.setVolume(max(0, min(100, value_0_to_100)) / 100.0)

    def set_muted(self, muted: bool):
        self.audio.setMuted(muted)

    def set_playback_rate(self, rate: float):
        self.media.setPlaybackRate(rate)

    @property
    def current_slide_index(self) -> int:
        """Return the slide currently active at the media position."""
        return self._current_slide_index

    @property
    def slide_count(self) -> int:
        """Return the number of slides in the loaded timeline."""
        return len(self._timeline)

    def jump_slide(self, direction: int):
        """Move playback to the adjacent slide (+1 next, -1 previous)."""
        target = self._timeline.adjacent_index(self.position_seconds(), direction)
        position = self._timeline.position_for(target)
        if position is not None:
            self.set_position(round(position * 1000))

    def seek_to_slide(self, index: int):
        """Seek playback to the start of a given slide index."""
        position = self._timeline.position_for(index)
        if position is not None:
            self.set_position(round(position * 1000))

    def _on_position_changed(self, ms: int):
        self.positionChanged.emit(ms)
        ix = self._timeline.current_index(ms / 1000.0)
        if ix != self._current_slide_index:
            self._current_slide_index = ix
            if ix >= 0:
                self.slideChanged.emit(ix)

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState):
        state_map = {
            QMediaPlayer.PlaybackState.StoppedState: PlaybackState.STOPPED,
            QMediaPlayer.PlaybackState.PlayingState: PlaybackState.PLAYING,
            QMediaPlayer.PlaybackState.PausedState: PlaybackState.PAUSED,
        }
        self.stateChanged.emit(state_map.get(state, PlaybackState.STOPPED).value)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus):
        if (
            self._pending_position_ms is not None
            and status
            in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia)
        ):
            position = self._pending_position_ms
            self._pending_position_ms = None
            self.media.setPosition(position)

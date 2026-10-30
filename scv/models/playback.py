"""Playback domain values shared by media adapters and views."""

from enum import Enum


class PlaybackState(str, Enum):
    """Application-level playback state independent of Qt multimedia types."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"

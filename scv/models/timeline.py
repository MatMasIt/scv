"""Pure slide-timeline domain model used by the media player."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence


class SlideTimeline:
    """Map playback positions to ordered slide timestamps.

    The class deliberately has no Qt dependency so timeline navigation can be
    tested independently from the multimedia backend and the UI.
    """

    def __init__(self, timestamps: Sequence[float] = ()):
        values = tuple(float(timestamp) for timestamp in timestamps)
        if any(timestamp < 0 for timestamp in values):
            raise ValueError("Slide timestamps cannot be negative")
        if any(current > following for current, following in zip(values, values[1:])):
            raise ValueError("Slide timestamps must be ordered")
        self._timestamps = values

    @property
    def timestamps(self) -> tuple[float, ...]:
        """Return the immutable slide timestamps in seconds."""
        return self._timestamps

    def __len__(self) -> int:
        return len(self._timestamps)

    def current_index(self, position_seconds: float) -> int:
        """Return the active slide index, or ``-1`` when the timeline is empty."""
        if not self._timestamps:
            return -1
        return max(0, bisect_right(self._timestamps, position_seconds) - 1)

    def adjacent_index(self, position_seconds: float, direction: int) -> int:
        """Return the bounded index adjacent to the slide active at a position."""
        if not self._timestamps:
            return -1
        current = self.current_index(position_seconds)
        return max(0, min(current + direction, len(self._timestamps) - 1))

    def position_for(self, index: int) -> float | None:
        """Return a slide start position, or ``None`` for an invalid index."""
        if 0 <= index < len(self._timestamps):
            return self._timestamps[index]
        return None

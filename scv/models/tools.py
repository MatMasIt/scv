"""Drawing tool enumerations and presentation attributes."""

from __future__ import annotations
from enum import Enum


class DrawingTool(Enum):
    """Supported canvas interaction and annotation tools."""

    SELECT_PAN = "select_pan"
    PEN = "pen"
    HIGHLIGHT_YELLOW = "yellow"
    HIGHLIGHT_GREEN = "green"

    @property
    def is_drawing_tool(self) -> bool:
        """Return whether this tool creates annotation strokes."""
        return self != DrawingTool.SELECT_PAN

    @property
    def is_highlighter(self) -> bool:
        """Return whether this tool is a highlighter."""
        return self in (DrawingTool.HIGHLIGHT_YELLOW, DrawingTool.HIGHLIGHT_GREEN)

    @property
    def kind(self) -> str:
        """Logical kind matching storage schema ('pen' or 'highlight')."""
        return "highlight" if self.is_highlighter else "pen"

    @property
    def style_id(self) -> str:
        """Storage style identifier."""
        match self:
            case DrawingTool.PEN:
                return "pen"
            case DrawingTool.HIGHLIGHT_YELLOW:
                return "highlight-yellow"
            case DrawingTool.HIGHLIGHT_GREEN:
                return "highlight-green"
            case _:
                return "none"

    @property
    def display_name(self) -> str:
        """Return the user-facing name of this drawing tool."""
        match self:
            case DrawingTool.SELECT_PAN:
                return "Select / pan"
            case DrawingTool.PEN:
                return "Pen"
            case DrawingTool.HIGHLIGHT_YELLOW:
                return "Yellow highlighter"
            case DrawingTool.HIGHLIGHT_GREEN:
                return "Green highlighter"

    @property
    def color(self) -> str:
        """Hex color code for rendering and UI icons."""
        match self:
            case DrawingTool.SELECT_PAN:
                return "#374151"
            case DrawingTool.PEN:
                return "#ef4444"
            case DrawingTool.HIGHLIGHT_YELLOW:
                return "#fde047"
            case DrawingTool.HIGHLIGHT_GREEN:
                return "#86efac"

    @property
    def stroke_width(self) -> int:
        """Default stroke width in image pixels."""
        return 18 if self.is_highlighter else 4

    @property
    def opacity(self) -> int:
        """Alpha channel (0-255) for painting."""
        return 110 if self.is_highlighter else 255

    @property
    def icon_symbol(self) -> str:
        """Return the symbol used for this tool’s button."""
        match self:
            case DrawingTool.SELECT_PAN:
                return "↖"
            case DrawingTool.PEN:
                return "✎"
            case _:
                return "▰"

    @classmethod
    def from_style(cls, style: str | None) -> DrawingTool:
        """Resolve a drawing tool from stored style or kind string."""
        if not style:
            return cls.SELECT_PAN
        clean = style.lower()
        if "yellow" in clean:
            return cls.HIGHLIGHT_YELLOW
        if "green" in clean:
            return cls.HIGHLIGHT_GREEN
        if "pen" in clean or "mark" in clean:
            return cls.PEN
        if "highlight" in clean:
            return cls.HIGHLIGHT_YELLOW
        return cls.SELECT_PAN


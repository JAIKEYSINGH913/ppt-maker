"""Grid-based layout engine for precise element positioning in PPTX slides.

Prevents text overlap by enforcing a virtual grid with safe margins.
All positioning is done through this engine instead of hardcoded Inches values.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pptx.util import Inches, Emu


# Standard slide dimensions (16:9 Widescreen: 13.333" x 7.5")
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Safe margins: content must stay within these bounds
MARGIN_LEFT = Inches(0.6)
MARGIN_RIGHT = Inches(0.5)
MARGIN_TOP = Inches(0.4)
MARGIN_BOTTOM = Inches(0.4)

# Title area reservation
TITLE_HEIGHT = Inches(0.7)
SUBTITLE_HEIGHT = Inches(0.5)
TITLE_TOP = MARGIN_TOP
SUBTITLE_TOP = TITLE_TOP + TITLE_HEIGHT

# Content safe zone (below title/subtitle, above footer)
CONTENT_TOP = SUBTITLE_TOP + SUBTITLE_HEIGHT + Inches(0.15)
CONTENT_BOTTOM = SLIDE_H - MARGIN_BOTTOM - Inches(0.3)  # Leave room for slide number
CONTENT_LEFT = MARGIN_LEFT
CONTENT_RIGHT = SLIDE_W - MARGIN_RIGHT

CONTENT_WIDTH = CONTENT_RIGHT - CONTENT_LEFT
CONTENT_HEIGHT = CONTENT_BOTTOM - CONTENT_TOP

# Shape internal padding
SHAPE_PAD_LEFT = Inches(0.12)
SHAPE_PAD_RIGHT = Inches(0.12)
SHAPE_PAD_TOP = Inches(0.08)
SHAPE_PAD_BOTTOM = Inches(0.08)

# Slide number area
SLIDE_NUM_LEFT = SLIDE_W - Inches(1.0)
SLIDE_NUM_TOP = SLIDE_H - Inches(0.35)
SLIDE_NUM_WIDTH = Inches(0.6)
SLIDE_NUM_HEIGHT = Inches(0.25)


@dataclass(slots=True)
class Rect:
    """A positioned rectangle in EMU units."""
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def overlaps(self, other: Rect) -> bool:
        """Check if this rect overlaps with another."""
        return not (
            self.right <= other.left
            or other.right <= self.left
            or self.bottom <= other.top
            or other.bottom <= self.top
        )


@dataclass(slots=True)
class GridLayout:
    """Configurable grid for element placement within the content safe zone."""
    columns: int = 12
    rows: int = 8
    gap: int = Inches(0.2)  # Gap between cells
    placed: list[Rect] = field(default_factory=list)

    @property
    def cell_width(self) -> int:
        """Width of a single grid cell."""
        usable = CONTENT_WIDTH - self.gap * (self.columns - 1)
        return int(usable / self.columns)

    @property
    def cell_height(self) -> int:
        """Height of a single grid cell."""
        usable = CONTENT_HEIGHT - self.gap * (self.rows - 1)
        return int(usable / self.rows)

    def cell_rect(self, col: int, row: int, col_span: int = 1, row_span: int = 1) -> Rect:
        """Get the rectangle for a grid cell (or span of cells)."""
        left = int(CONTENT_LEFT) + col * (self.cell_width + int(self.gap))
        top = int(CONTENT_TOP) + row * (self.cell_height + int(self.gap))
        width = col_span * self.cell_width + (col_span - 1) * int(self.gap)
        height = row_span * self.cell_height + (row_span - 1) * int(self.gap)
        return Rect(left=left, top=top, width=width, height=height)

    def place(self, rect: Rect) -> bool:
        """Register a placed element. Returns True if no collision."""
        for existing in self.placed:
            if rect.overlaps(existing):
                return False
        self.placed.append(rect)
        return True

    def reset(self) -> None:
        """Clear all placed elements."""
        self.placed.clear()

    # --- Pre-built layout patterns ---

    def title_rect(self) -> Rect:
        """Rectangle for the slide title."""
        return Rect(
            left=int(MARGIN_LEFT),
            top=int(TITLE_TOP),
            width=int(SLIDE_W - MARGIN_LEFT - MARGIN_RIGHT),
            height=int(TITLE_HEIGHT),
        )

    def subtitle_rect(self) -> Rect:
        """Rectangle for the slide subtitle."""
        return Rect(
            left=int(MARGIN_LEFT),
            top=int(SUBTITLE_TOP),
            width=int(SLIDE_W - MARGIN_LEFT - MARGIN_RIGHT),
            height=int(SUBTITLE_HEIGHT),
        )

    def full_content_rect(self) -> Rect:
        """Full content area rectangle."""
        return Rect(
            left=int(CONTENT_LEFT),
            top=int(CONTENT_TOP),
            width=int(CONTENT_WIDTH),
            height=int(CONTENT_HEIGHT),
        )

    def card_row(self, count: int, row_start: int = 0, row_span: int = 3) -> list[Rect]:
        """Generate evenly-spaced card rectangles in a row."""
        if count <= 0:
            return []
        cols_per_card = max(1, self.columns // count)
        gap_cols = max(0, self.columns - cols_per_card * count)
        rects = []
        for i in range(count):
            col = i * cols_per_card + min(i, gap_cols)
            span = cols_per_card
            rects.append(self.cell_rect(col, row_start, col_span=span, row_span=row_span))
        return rects

    def card_column(self, count: int, col_start: int = 0, col_span: int = 4) -> list[Rect]:
        """Generate evenly-spaced card rectangles in a column."""
        if count <= 0:
            return []
        rows_per_card = max(1, self.rows // count)
        rects = []
        for i in range(min(count, self.rows)):
            row = i * rows_per_card
            rects.append(self.cell_rect(col_start, row, col_span=col_span, row_span=rows_per_card))
        return rects

    def two_column_split(self, row_start: int = 0, row_span: int = 6) -> tuple[Rect, Rect]:
        """Split content area into two columns (e.g., chart + text)."""
        left_rect = self.cell_rect(0, row_start, col_span=6, row_span=row_span)
        right_rect = self.cell_rect(6, row_start, col_span=6, row_span=row_span)
        return left_rect, right_rect

    def quadrant_grid(self, row_start: int = 0, row_span: int = 3) -> list[Rect]:
        """4-quadrant layout for SWOT, comparisons, etc."""
        return [
            self.cell_rect(0, row_start, col_span=6, row_span=row_span),
            self.cell_rect(6, row_start, col_span=6, row_span=row_span),
            self.cell_rect(0, row_start + row_span, col_span=6, row_span=row_span),
            self.cell_rect(6, row_start + row_span, col_span=6, row_span=row_span),
        ]

    def icon_badge_rect(self, parent: Rect, position: str = "top-left") -> Rect:
        """Small icon badge positioned relative to a parent rectangle."""
        badge_size = Inches(0.4)
        if position == "top-left":
            return Rect(
                left=parent.left + int(Inches(0.1)),
                top=parent.top + int(Inches(0.1)),
                width=int(badge_size),
                height=int(badge_size),
            )
        elif position == "top-right":
            return Rect(
                left=parent.right - int(badge_size) - int(Inches(0.1)),
                top=parent.top + int(Inches(0.1)),
                width=int(badge_size),
                height=int(badge_size),
            )
        return Rect(
            left=parent.left + int(Inches(0.1)),
            top=parent.top + int(Inches(0.1)),
            width=int(badge_size),
            height=int(badge_size),
        )

    def slide_number_rect(self) -> Rect:
        """Rectangle for the slide number footer."""
        return Rect(
            left=int(SLIDE_NUM_LEFT),
            top=int(SLIDE_NUM_TOP),
            width=int(SLIDE_NUM_WIDTH),
            height=int(SLIDE_NUM_HEIGHT),
        )


def clamp_text(text: str, max_words: int = 35, max_chars: int = 160) -> str:
    """Clamp text to max words OR max characters, whichever is shorter."""
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "…"
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def clamp_lines(text: str, max_lines: int = 6) -> str:
    """Clamp text to max number of lines."""
    lines = text.split("\n")
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + "…"
    return text

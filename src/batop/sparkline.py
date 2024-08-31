"""A sparkline gadget with an append method for discrete-time data."""

from collections import deque

from batgrl.colors import Color, lerp_colors
from batgrl.gadgets.text import Point, PosHint, Size, SizeHint, Text
from batgrl.text_tools import new_cell, smooth_vertical_bar

from .colors import BG_COLOR, FG_COLOR, MAX_COLOR, MIN_COLOR

MAX_DATA = 200


class SparkLine(Text):
    """A sparkline gadget with an append method for discrete-time data."""

    def __init__(
        self,
        *,
        is_flipped: bool = False,
        min_color: Color = MIN_COLOR,
        max_color: Color = MAX_COLOR,
        fg_color: Color = FG_COLOR,
        bg_color: Color = BG_COLOR,
        alpha: float = 0.0,
        size: Size = Size(10, 10),
        pos: Point = Point(0, 0),
        size_hint: SizeHint | None = None,
        pos_hint: PosHint | None = None,
        is_transparent: bool = False,
        is_visible: bool = True,
        is_enabled: bool = True,
    ) -> None:
        default_cell = new_cell(fg_color=fg_color, bg_color=bg_color)
        super().__init__(
            size=size,
            pos=pos,
            default_cell=default_cell,
            alpha=alpha,
            size_hint=size_hint,
            pos_hint=pos_hint,
            is_transparent=is_transparent,
            is_visible=is_visible,
            is_enabled=is_enabled,
        )
        self._is_flipped = is_flipped
        self._min_color = min_color
        self._max_color = max_color
        self._data = deque(maxlen=MAX_DATA)

    @property
    def is_flipped(self) -> bool:
        """Whether sparkline is drawn bottom-to-top (false) or top-to-bottom (true)."""
        return self._is_flipped

    @is_flipped.setter
    def is_flipped(self, is_flipped: bool):
        self._is_flipped = is_flipped
        self._refresh_display()

    @property
    def min_color(self) -> Color:
        """Color of minimum value of sparkline."""
        return self._min_color

    @min_color.setter
    def min_color(self, min_color: Color):
        self._min_color = min_color
        self._refresh_display()

    @property
    def max_color(self) -> Color:
        """Color of maximum value of sparkline."""
        return self._max_color

    @max_color.setter
    def max_color(self, max_color: Color):
        self._max_color = max_color
        self._refresh_display()

    def append(self, p: float) -> None:
        """Add new data ``p`` (0 <= p <= 1) to sparkline."""
        self._data.appendleft(p)
        self._refresh_display()

    def on_size(self) -> None:
        """Refresh display on resize."""
        super().on_size()
        self.clear()
        w = self.width
        for i, p in enumerate(self._data):
            x = w - 1 - i
            if x < 0:
                break
            self._draw_bar(x, p)

    def _draw_bar(self, x: int, p: float) -> None:
        """Draw a smooth bar with proportion ``p`` at ``x``."""
        bar = smooth_vertical_bar(self.height, p, reversed=self.is_flipped)
        view = self.canvas if self.is_flipped else self.canvas[::-1]
        bar_view = view[: len(bar), x]
        bar_view["char"] = bar
        bar_view["reverse"] = self.is_flipped
        bar_view["fg_color"] = lerp_colors(self.min_color, self.max_color, p)

    def _refresh_display(self) -> None:
        self.canvas[:, :-1] = self.canvas[:, 1:]
        self.canvas[:, -1] = self.default_cell
        self._draw_bar(-1, self._data[0])

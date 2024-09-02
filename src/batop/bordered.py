"""A gadget for bordered content."""

import asyncio
from time import monotonic

import numpy as np
from batgrl.gadgets.gadget import Gadget
from batgrl.gadgets.pane import Pane
from batgrl.gadgets.text import Border, PosHint, Text

from .colors import BG_COLOR, DEFAULT_CELL


def rainbow(texture):
    """Add a radial rainbow gradient to a texture."""
    h, w, _ = texture.shape
    ys, xs = np.indices((h, w), dtype=float)
    ys -= 0.5 * h
    xs -= 0.5 * w

    colors = 0.5 + 0.5 * np.cos(
        np.arctan2(xs, ys)[..., None] + 3.0 * monotonic() + (0, 23, 21)
    )
    texture[:] = (colors * 255).astype(int)


class Bordered(Text):
    """A gadget for bordered content."""

    def __init__(
        self,
        left_header: Gadget | str | None = None,
        center_header: Gadget | str | None = None,
        right_header: Gadget | str | None = None,
        border: Border = "curved",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.default_bg_color = BG_COLOR
        self.clear()

        self._content = Pane(
            pos=(1, 1),
            bg_color=BG_COLOR,
            size_hint={
                "height_hint": 1.0,
                "width_hint": 1.0,
                "height_offset": -2,
                "width_offset": -2,
            },
            is_transparent=False,
        )
        self.add_gadget(self._content)
        self._rainbow_task: asyncio.Task | None = None

        self.border = border
        self.add_border(border)
        hints: tuple[PosHint, ...] = (
            {"x_hint": 0, "x_offset": 2, "anchor": "left"},
            {"x_hint": 0.5},
            {"x_hint": 1.0, "x_offset": -2, "anchor": "right"},
        )
        for title, hint in zip((left_header, center_header, right_header), hints):
            if isinstance(title, str):
                label = Text(default_cell=DEFAULT_CELL, pos_hint=hint)
                label.set_text(title)
                self.add_gadget(label)
            elif isinstance(title, Gadget):
                title.pos_hint = hint
                self.add_gadget(title)

    def on_add(self):
        """Start rainbow effect."""
        super().on_add()
        self._rainbow_task = asyncio.create_task(self._rainbow())

    def on_remove(self):
        """Stop rainbow effect."""
        if self._rainbow_task is not None:
            self._rainbow_task.cancel()
            self._rainbow_task = None
        super().on_remove()

    async def _rainbow(self):
        while True:
            rainbow(self.canvas["fg_color"])
            await asyncio.sleep(0)

    @property
    def content(self):
        """Content that is bordered."""
        return self._content

    def on_size(self):
        """Redraw border on resize."""
        super().on_size()
        self.clear()
        if self.height > 2 and self.width > 2:
            self.add_border(self.border)
            rainbow(self.canvas["fg_color"])

"""Network Monitor."""

import asyncio
from time import monotonic

import psutil
from batgrl.colors import lerp_colors
from batgrl.gadgets.stack_layout import VStackLayout
from batgrl.gadgets.text import Text
from batgrl.text_tools import smooth_vertical_bar

from .bordered import Bordered
from .colors import DEFAULT_CELL
from .memory_monitor import format_mem
from .sparkline import SparkLine


class _ScalingSparkline(SparkLine):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._max = 0.0

    def on_size(self) -> None:
        """Refresh display on resize."""
        Text.on_size(self)
        # super(SparkLine, self).on_size()
        self._max = self._calculate_max()
        self._rescale_bars()

    def append(self, p: float) -> None:
        """Add new data ``p`` to sparkline."""
        self._data.appendleft(p)
        new_max = self._calculate_max()
        if new_max != self._max:
            self._max = new_max
            self._rescale_bars()
        else:
            self._refresh_display()

    def _calculate_max(self) -> float:
        w = self.width
        mx = 0.0
        for i, datum in enumerate(self._data):
            if i == w:
                break
            if datum > mx:
                mx = datum
        return mx

    def _draw_bar(self, x: int, value: float) -> None:
        """Draw a smooth bar with proportion ``value/self._max`` at ``x``."""
        if self._max == 0:
            return
        p = value / self._max
        bar = smooth_vertical_bar(self.height, p, reversed=self.is_flipped)
        view = self.canvas if self.is_flipped else self.canvas[::-1]
        bar_view = view[: len(bar), x]
        bar_view["char"] = bar
        bar_view["reverse"] = self.is_flipped
        bar_view["fg_color"] = lerp_colors(self.min_color, self.max_color, p)

    def _rescale_bars(self) -> None:
        self.clear()
        w = self.width
        for i, p in enumerate(self._data):
            x = w - 1 - i
            if x < 0:
                break
            self._draw_bar(x, p)

    def _refresh_display(self) -> None:
        self.canvas[:, :-1] = self.canvas[:, 1:]
        self.canvas[:, -1] = self.default_cell
        self._draw_bar(-1, self._data[0])


class NetworkMonitor(Bordered):
    """Network Monitor."""

    def __init__(self, **kwargs):
        super().__init__(left_header="network", **kwargs)
        self._last_io = psutil.net_io_counters(), monotonic()
        self._network_task: asyncio.Task | None = None
        self._download_top = Text(default_cell=DEFAULT_CELL)
        self._download_total = Text(default_cell=DEFAULT_CELL, pos_hint={"x_hint": 0.5})
        self._download_current = Text(
            default_cell=DEFAULT_CELL, pos_hint={"x_hint": 1.0, "anchor": "right"}
        )
        self._upload_top = Text(
            default_cell=DEFAULT_CELL, pos_hint={"y_hint": 1.0, "anchor": "bottom"}
        )
        self._upload_total = Text(
            default_cell=DEFAULT_CELL,
            pos_hint={"y_hint": 1.0, "x_hint": 0.5, "anchor": "bottom"},
        )
        self._upload_current = Text(
            default_cell=DEFAULT_CELL,
            pos_hint={"y_hint": 1.0, "x_hint": 1.0, "anchor": "bottom-right"},
        )

        self._download_spark = _ScalingSparkline()
        self._upload_spark = _ScalingSparkline(is_flipped=True)
        stack = VStackLayout(
            pos=(1, 0),
            size_hint={"height_hint": 1.0, "height_offset": -2, "width_hint": 1.0},
        )
        stack.add_gadgets(self._download_spark, self._upload_spark)
        self.content.add_gadgets(
            self._download_top,
            self._download_total,
            self._download_current,
            self._upload_top,
            self._upload_total,
            self._upload_current,
            stack,
        )

    def on_add(self):
        """Start monitoring network on add."""
        super().on_add()
        self._network_task = asyncio.create_task(self._monitor_network())

    def on_remove(self):
        """Stop monitoring network on remove."""
        if self._network_task is not None:
            self._network_task.cancel()
            self._network_task = None
        super().on_remove()

    async def _monitor_network(self):
        while True:
            last_net, last_time = self._last_io
            current_net, current_time = psutil.net_io_counters(), monotonic()
            elapsed_time = current_time - last_time

            new_bytes_recv = current_net.bytes_recv - last_net.bytes_recv
            down_speed = new_bytes_recv / elapsed_time
            self._download_spark.append(down_speed)
            self._download_top.set_text(
                f"top: ▼ {format_mem(self._download_spark._max)}/s"
            )
            self._download_total.set_text(
                f"total: ▼ {format_mem(current_net.bytes_recv)}"
            )
            self._download_current.set_text(f"current: ▼ {format_mem(down_speed)}/s")

            new_bytes_sent = current_net.bytes_sent - last_net.bytes_sent
            up_speed = new_bytes_sent / elapsed_time
            self._upload_spark.append(up_speed)
            self._upload_top.set_text(f"top: ▲ {format_mem(self._upload_spark._max)}/s")
            self._upload_total.set_text(
                f"total: ▲ {format_mem(current_net.bytes_sent)}"
            )
            self._upload_current.set_text(f"current: ▲ {format_mem(up_speed)}/s")

            self._last_io = current_net, current_time
            await asyncio.sleep(1)

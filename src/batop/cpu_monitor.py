"""CPU monitor."""

from __future__ import annotations

import asyncio
import platform
from datetime import datetime
from math import ceil

import psutil
from batgrl.gadgets.behaviors.button_behavior import ButtonBehavior
from batgrl.gadgets.behaviors.movable import Movable
from batgrl.gadgets.gadget import Gadget
from batgrl.gadgets.grid_layout import GridLayout
from batgrl.gadgets.slider import Slider
from batgrl.gadgets.text import Text
from batgrl.terminal.events import MouseEvent
from batgrl.text_tools import new_cell

from .bordered import Bordered
from .colors import BG_COLOR, DEFAULT_CELL, FG_COLOR, MAX_COLOR
from .context_menu import ContextMenu
from .sparkline import SparkLine

REFRESH_RATE = 0.1


class _UpdateRefreshRateButton(ButtonBehavior, Gadget):
    def __init__(self, cpu_monitor: CpuMonitor):
        super().__init__(size=(1, 40), is_transparent=True)
        self._label = Text(default_cell=DEFAULT_CELL, size=(1, 20), pos=(0, 20))

        def slider_callback(value):
            cpu_monitor.refresh_rate = value
            self._label.add_str(f"refresh rate: {round(value * 1000):4d}ms")

        self._slider = Slider(
            min=0.0,
            max=0.95,
            start_value=REFRESH_RATE,
            callback=slider_callback,
            handle_color=FG_COLOR,
            slider_color=FG_COLOR,
            fill_color=MAX_COLOR,
            bg_color=BG_COLOR,
            size=(1, 20),
            pos=(0, 20),
        )
        self._tween_task = None
        self.add_gadgets(self._slider, self._label)

    def update_hover(self):
        if self._tween_task is not None:
            self._tween_task.cancel()
        self._tween_task = asyncio.create_task(
            self._label.tween(duration=0.5, easing="out_bounce", pos=(0, 0))
        )

    def update_normal(self):
        if self._tween_task is not None:
            self._tween_task.cancel()
        self._tween_task = asyncio.create_task(
            self._label.tween(duration=0.5, easing="out_bounce", pos=(0, 20))
        )


class _Clock(Text):
    def __init__(self):
        super().__init__(size=(1, 8), default_cell=DEFAULT_CELL)
        self._update_task = None

    def on_add(self):
        super().on_add()
        if self._update_task is not None:
            self._update_task.cancel()
        self._update_task = asyncio.create_task(self._update_time())

    def on_remove(self):
        if self._update_task is not None:
            self._update_task.cancel()
            self._update_task = None
        super().on_remove()

    async def _update_time(self):
        while True:
            self.add_str(datetime.now().strftime("%H:%M:%S"))
            await asyncio.sleep(1)


class _CoreSpark(Gadget):
    def __init__(self, label, bar_width, **kwargs):
        super().__init__(**kwargs)
        default_cell = new_cell(fg_color=FG_COLOR, bg_color=BG_COLOR)
        self._label = Text(default_cell=default_cell)
        self._label.set_text(label)
        self._sparkline = SparkLine(size=(1, bar_width))
        self._percent = Text(default_cell=default_cell, size=(1, 6))
        self._sparkline.left = self._label.right
        self._percent.left = self._sparkline.right
        self.add_gadgets(self._label, self._sparkline, self._percent)
        self.size = 1, self._percent.right


class _CoreMonitor(Movable, Bordered):
    def __init__(self, bar_width=10, **kwargs):
        super().__init__(**kwargs)
        ncpus = psutil.cpu_count()

        self._grid = GridLayout(
            grid_rows=ceil(ncpus / 2),
            grid_columns=2,
            orientation="tb-lr",
            horizontal_spacing=1,
            is_transparent=True,
        )

        ndigits = len(str(ncpus + 1))
        for i in range(ncpus):
            spark = _CoreSpark(f"core {i + 1:{ndigits}} ", bar_width)
            self._grid.add_gadget(spark)

        h, w = self._grid.size = self._grid.min_grid_size
        self.size = h + 2, w + 2
        self.content.add_gadget(self._grid)
        self._monitor_cpu_task = None

    def on_add(self):
        super().on_add()
        self._monitor_cpu_task = asyncio.create_task(self._monitor_cpu())

    def on_remove(self):
        if self._monitor_cpu_task is not None:
            self._monitor_cpu_task.cancel()
        super().on_remove()

    async def _monitor_cpu(self):
        cpu_monitor: CpuMonitor = self.parent.parent
        while True:
            self._refresh_display()
            await asyncio.sleep(cpu_monitor.refresh_rate)

    def _refresh_display(self):
        total = psutil.cpu_percent() / 100
        times = psutil.cpu_times_percent()
        cpu_monitor: CpuMonitor = self.parent.parent
        if cpu_monitor._top_spark_option == "total":
            cpu_monitor._top_spark.append(total)
        else:
            cpu_monitor._top_spark.append(
                getattr(times, cpu_monitor._top_spark_option) / 100
            )

        if cpu_monitor._bottom_spark_option == "total":
            cpu_monitor._bottom_spark.append(total)
        else:
            cpu_monitor._bottom_spark.append(
                getattr(times, cpu_monitor._bottom_spark_option) / 100
            )

        spark: _CoreSpark
        for spark, p in zip(self._grid.children, psutil.cpu_percent(percpu=True)):
            spark._sparkline.append(p / 100)
            spark._percent.add_str(f" {p:4.3g}%")


class CpuMonitor(Bordered):
    """CPU monitor."""

    def __init__(self, **kwargs):
        super().__init__(
            left_header="cpu",
            center_header=_Clock(),
            right_header=_UpdateRefreshRateButton(self),
            **kwargs,
        )
        self.refresh_rate = REFRESH_RATE
        self._top_spark = SparkLine(
            size=(4, 1),
            size_hint={"width_hint": 1.0},
            pos_hint={"y_hint": 0.5, "anchor": "bottom"},
        )
        self._bottom_spark = SparkLine(
            size=(4, 1),
            size_hint={"width_hint": 1.0},
            pos_hint={"y_hint": 0.5, "anchor": "top"},
            is_flipped=True,
        )
        self._core_monitor = _CoreMonitor(
            left_header=platform.machine(),
            right_header=f"{psutil.cpu_freq().current / 1000:g} GHz",
            disable_oob=True,
        )
        self.content.add_gadgets(
            self._top_spark, self._bottom_spark, self._core_monitor
        )
        self._top_spark_option = "total"
        self._bottom_spark_option = "total"
        fields = ["total", *psutil.cpu_times_percent()._fields]

        def attrsetter(attr, field):
            def setter():
                setattr(self, attr, field)

            return setter

        top_spark_menu = {
            field: attrsetter("top_spark_option", field) for field in fields
        }
        bottom_spark_menu = {
            field: attrsetter("bottom_spark_option", field) for field in fields
        }
        self.add_gadgets(
            ContextMenu.from_dict_of_dicts(
                {"Top Spark": top_spark_menu, "Bottom Spark": bottom_spark_menu}
            )
        )
        self._context_menu: ContextMenu = self.children[-1]
        self._context_menu.close_menu()

    @property
    def top_spark_option(self) -> str:
        """Determines the display of top sparkline."""
        return self._top_spark_option

    @top_spark_option.setter
    def top_spark_option(self, option: str):
        if option != self._top_spark_option:
            self._top_spark_option = option
            self._top_spark._data.clear()
            self._top_spark.on_size()

    @property
    def bottom_spark_option(self) -> str:
        """Determines the display of bottom sparkline."""
        return self._bottom_spark_option

    @bottom_spark_option.setter
    def bottom_spark_option(self, option: str):
        if option != self._bottom_spark_option:
            self._bottom_spark_option = option
            self._bottom_spark._data.clear()
            self._bottom_spark.on_size()

    def on_add(self):
        """Reposition core monitor on add."""
        super().on_add()
        self._core_monitor.y = (self.content.height - self._core_monitor.height) // 2
        self._core_monitor.right = self.content.width - 3

    def on_mouse(self, mouse_event: MouseEvent) -> bool | None:
        """Open context-menu on right-click."""
        if mouse_event.button == "right" and self.collides_point(mouse_event.pos):
            self._context_menu.pos = self.to_local(mouse_event.pos)
            self._context_menu.open_menu()
            return True
        return super().on_mouse(mouse_event)

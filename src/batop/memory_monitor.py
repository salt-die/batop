"""Memory monitor."""

import asyncio

import psutil
from batgrl.gadgets.text import Text
from batgrl.text_tools import smooth_horizontal_bar, str_width

from .bordered import Bordered
from .colors import DEFAULT_CELL, GREEN, RED


def format_mem(mem: float) -> str:
    """Return ``mem`` bytes as tera-, giga-, or mega-bytes."""
    TRILLION = 1_000_000_000_000
    BILLION = 1_000_000_000
    MILLION = 1_000_000
    if mem >= TRILLION:
        return f"{mem / TRILLION:.3g} TiB"
    if mem >= BILLION:
        return f"{mem / BILLION:.3g} GiB"
    return f"{mem / MILLION:.3g} MiB"


class _MemInfo(Text):
    def __init__(self, label: str, meminfo):
        super().__init__(
            size=(2, 10), size_hint={"width_hint": 1.0}, default_cell=DEFAULT_CELL
        )
        self._label = label
        self._meminfo = meminfo
        self.update()

    def on_size(self):
        super().on_size()
        self.update()

    def update(self, meminfo=None) -> None:
        if meminfo is None:
            meminfo = self._meminfo
        else:
            self._meminfo = meminfo

        self.clear()
        total = f"{self._label} {format_mem(meminfo.total)}"
        used = f"{format_mem(meminfo.used)} {meminfo.percent:4.3g}%"
        free = f"{format_mem(meminfo.free)} {100 - meminfo.percent:4.3g}%"
        self.add_str(total, truncate_str=True)
        x = str_width(total) + 2
        if x < self.width:
            self.add_str(used, pos=(0, x), fg_color=RED, truncate_str=True)
        x += str_width(used) + 2
        if x < self.width:
            self.add_str(free, pos=(0, x), fg_color=GREEN, truncate_str=True)

        bar_line = self.canvas[1]
        bar_line["fg_color"] = RED
        bar_line["bg_color"] = GREEN
        bar = smooth_horizontal_bar(self.width, meminfo.percent / 100)
        # raise SystemExit(self.canvas.shape, bar_line.shape, self.width, len(bar))
        bar_line["char"][: len(bar)] = bar


class MemoryMonitor(Bordered):
    """Memory monitor."""

    def __init__(self, **kwargs):
        super().__init__(left_header="memory", **kwargs)
        parts = psutil.disk_partitions()
        self.height = len(parts) * 2 + 6
        self._meminfo: dict[str, _MemInfo] = {}
        self._meminfo["virtual"] = _MemInfo("virtual", psutil.virtual_memory())
        self._meminfo["swap"] = _MemInfo("swap", psutil.swap_memory())
        for part in parts:
            self._meminfo[part.mountpoint] = _MemInfo(
                part.mountpoint, psutil.disk_usage(part.mountpoint)
            )

        self.content.add_gadgets(self._meminfo.values())
        it = iter(self._meminfo.values())
        last = next(it)
        for meminfo in it:
            meminfo.top = last.bottom
            last = meminfo

        self._virtual_task = None
        self._swap_task = None
        self._disks_task = None

    def on_add(self):
        """Start memory monitoring tasks on add."""
        super().on_add()
        self._virtual_task = asyncio.create_task(self._monitor_virtual())
        self._swap_task = asyncio.create_task(self._monitor_swap())
        self._disks_task = asyncio.create_task(self._monitor_disks())

    def on_remove(self):
        """Stop memory monitoring tasks on remove."""
        if self._virtual_task is not None:
            self._virtual_task.cancel()
            self._virtual_task = None
        if self._swap_task is not None:
            self._swap_task.cancel()
            self._swap_task = None
        if self._disks_task is not None:
            self._disks_task.cancel()
            self._disks_task = None
        super().on_remove()

    async def _monitor_virtual(self):
        while True:
            self._meminfo["virtual"].update(psutil.virtual_memory())
            await asyncio.sleep(2)

    async def _monitor_swap(self):
        while True:
            self._meminfo["swap"].update(psutil.swap_memory())
            await asyncio.sleep(5)

    async def _monitor_disks(self):
        while True:
            for disk in psutil.disk_partitions():
                if disk.mountpoint in self._meminfo:
                    self._meminfo[disk.mountpoint].update(
                        psutil.disk_usage(disk.mountpoint)
                    )
            await asyncio.sleep(60)

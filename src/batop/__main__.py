"""A badass, top-like app."""

from batgrl.app import App
from batgrl.gadgets.split_layout import HSplitLayout, VSplitLayout

from .cpu_monitor import CpuMonitor
from .memory_monitor import MemoryMonitor


class Batop(App):
    """A badass, top-like app."""

    async def on_start(self):
        """Add gadgets on start."""
        hsplit = HSplitLayout(
            size_hint={"height_hint": 1.0, "width_hint": 1.0}, min_split_height=15
        )
        vsplit = VSplitLayout(
            size_hint={"height_hint": 1.0, "width_hint": 1.0}, min_split_width=50
        )
        cpu = CpuMonitor(size_hint={"height_hint": 1.0, "width_hint": 1.0})
        mem = MemoryMonitor(size_hint={"width_hint": 1.0})
        hsplit.top_pane.add_gadget(cpu)
        hsplit.bottom_pane.add_gadget(vsplit)
        vsplit.left_pane.add_gadget(mem)
        self.add_gadget(hsplit)


Batop(title="batop").run()

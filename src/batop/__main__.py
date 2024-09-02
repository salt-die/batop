"""A badass, top-like app."""

from batgrl.app import App
from batgrl.gadgets.split_layout import HSplitLayout, VSplitLayout

from .cpu_monitor import CpuMonitor
from .memory_monitor import MemoryMonitor
from .network_monitor import NetworkMonitor
from .process_monitor import ProcessMonitor


class Batop(App):
    """A badass, top-like app."""

    async def on_start(self):
        """Add gadgets on start."""
        cpu = CpuMonitor(size_hint={"height_hint": 1.0, "width_hint": 1.0})
        mem = MemoryMonitor(size_hint={"width_hint": 1.0})
        net = NetworkMonitor(
            pos=(mem.height, 0),
            size_hint={
                "height_hint": 1.0,
                "height_offset": -mem.height,
                "width_hint": 1.0,
            },
        )
        process = ProcessMonitor(size_hint={"height_hint": 1.0, "width_hint": 1.0})

        hsplit = HSplitLayout(
            size_hint={"height_hint": 1.0, "width_hint": 1.0}, min_split_height=15
        )
        vsplit = VSplitLayout(
            size_hint={"height_hint": 1.0, "width_hint": 1.0}, min_split_width=50
        )
        hsplit.top_pane.add_gadget(cpu)
        hsplit.bottom_pane.add_gadget(vsplit)
        vsplit.left_pane.add_gadget(mem)
        vsplit.left_pane.add_gadget(net)
        vsplit.right_pane.add_gadget(process)
        self.add_gadget(hsplit)


Batop(title="batop").run()

"""Process Monitor."""

import psutil
from batgrl.gadgets.data_table import DataTable

from .bordered import Bordered


class ProcessMonitor(Bordered):
    """Process Monitor."""

    def __init__(self, **kwargs):
        super().__init__(left_header="processes", **kwargs)
        data = {}
        processes = [psutil.Process(pid) for pid in psutil.pids()]
        data["pid"] = [p.pid for p in processes]
        data["name"] = [p.name() for p in processes]
        data["threads"] = [p.num_threads() for p in processes]
        data["mem%"] = [round(p.memory_percent(), 3) for p in processes]
        # data["cpu%"] = [p.cpu_percent() for p in processes]
        self._data_table = DataTable(
            data=data, size_hint={"height_hint": 1.0, "width_hint": 1.0}
        )
        self.content.add_gadget(self._data_table)

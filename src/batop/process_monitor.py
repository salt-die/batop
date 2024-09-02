"""Process Monitor."""

from .bordered import Bordered


class ProcessMonitor(Bordered):
    """Process Monitor."""

    def __init__(self, **kwargs):
        super().__init__(left_header="processes", **kwargs)

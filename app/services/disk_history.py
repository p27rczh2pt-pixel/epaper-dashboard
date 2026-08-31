"""
Rolling history of the Pi Zero's disk usage percentage, sampled once per
call to get_system_health() — driven by the dashboard page's background
refresh (60s) now that there's no separate poller process — for the
dashboard's disk sparkline.

State lives in a single process-global tracker instance, kept alive by the
Flask API process running continuously under systemd — same tradeoff as
memory_history's tracker: NOT persisted to disk, so a restart of that
process resets the history and the chart starts collecting again.
"""

from collections import deque

from flask import current_app


class DiskHistoryTracker:
    def __init__(self, maxlen):
        self._history = deque(maxlen=maxlen)

    def record(self, percent_used):
        if isinstance(percent_used, (int, float)):
            self._history.append(round(percent_used, 1))
        return list(self._history)


def get_tracker():
    if not hasattr(current_app, "_system_disk_tracker"):
        current_app._system_disk_tracker = DiskHistoryTracker(maxlen=current_app.config["DISK_HISTORY_SIZE"])
    return current_app._system_disk_tracker

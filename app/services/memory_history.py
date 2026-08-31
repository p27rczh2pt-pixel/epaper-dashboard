"""
Rolling history of Pi-hole's memory usage, sampled once per call to
get_pihole_system_health() — driven by the dashboard page's background
refresh (60s) now that there's no separate poller process — for the
dashboard's memory sparkline.

State lives in a single process-global tracker instance, kept alive by the
Flask API process running continuously under systemd — same tradeoff as
anomaly_service's QueryRateTracker: NOT persisted to disk, so a restart of
that process resets the history and the chart starts collecting again.
"""

from collections import deque

from flask import current_app


class MemoryHistoryTracker:
    def __init__(self, maxlen):
        self._history = deque(maxlen=maxlen)

    def record(self, percent_used):
        if isinstance(percent_used, (int, float)):
            self._history.append(round(percent_used, 1))
        return list(self._history)


def get_tracker():
    if not hasattr(current_app, "_pihole_mem_tracker"):
        current_app._pihole_mem_tracker = MemoryHistoryTracker(maxlen=current_app.config["PIHOLE_MEM_HISTORY_SIZE"])
    return current_app._pihole_mem_tracker

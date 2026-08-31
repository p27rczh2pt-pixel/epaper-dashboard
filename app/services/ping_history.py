"""
Rolling history of ping latency + packet loss, sampled once per call to
get_network_health() — driven by the dashboard page's background refresh
(60s) now that there's no separate poller process — for the Network
page's latency chart.

Unlike memory_history/disk_history, a failed or lossy sample is still
recorded (as None / the loss percent) rather than skipped, so an outage
shows up as a gap in the latency line instead of silently vanishing from
the chart — the whole point of this chart is to catch past issues.

State lives in a single process-global tracker instance, kept alive by the
Flask API process running continuously under systemd — same tradeoff as
memory_history's tracker: NOT persisted to disk, so a restart of that
process resets the history and the chart starts collecting again.
"""

from collections import deque

from flask import current_app


class PingHistoryTracker:
    def __init__(self, maxlen):
        self._rtt = deque(maxlen=maxlen)
        self._loss = deque(maxlen=maxlen)

    def record(self, rtt_avg_ms, packet_loss_percent):
        self._rtt.append(round(rtt_avg_ms, 1) if isinstance(rtt_avg_ms, (int, float)) else None)
        self._loss.append(round(packet_loss_percent, 1) if isinstance(packet_loss_percent, (int, float)) else None)
        return {"rtt_avg_ms": list(self._rtt), "packet_loss_percent": list(self._loss)}


def get_tracker():
    if not hasattr(current_app, "_ping_tracker"):
        current_app._ping_tracker = PingHistoryTracker(maxlen=current_app.config["NETWORK_PING_HISTORY_SIZE"])
    return current_app._ping_tracker

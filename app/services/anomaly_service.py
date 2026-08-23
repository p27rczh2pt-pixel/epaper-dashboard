"""
Threshold-based query rate anomaly detection.

Pi-hole's summary endpoint reports a cumulative total, not a rate, so this
tracks the delta between consecutive polls (normalized to queries/minute
using the actual elapsed time, so it's tolerant of the poller running a
bit early/late) and flags when the current rate spikes well above the
rolling average of recent polls.

State lives in a single process-global QueryRateTracker instance, kept
alive by the Flask API process running continuously under systemd — it is
NOT persisted to disk, so a restart of that process resets the baseline.
It also assumes a roughly consistent polling interval (e.g. the poller's
5-minute systemd timer); a burst of unusually close-together requests to
/api/pihole/stats will produce noisy, small-time-window rate readings.
"""

import time
from collections import deque

from flask import current_app


class QueryRateTracker:
    def __init__(self, history_size=12, multiplier=3.0, min_qpm=5.0, min_samples=3):
        self.multiplier = multiplier
        self.min_qpm = min_qpm
        self.min_samples = min_samples
        self._last_sample = None  # (monotonic_time, queries_total)
        self._rate_history = deque(maxlen=history_size)

    def evaluate(self, queries_total, now=None):
        now = time.monotonic() if now is None else now

        if queries_total is None:
            return self._result(None, None, False, None)

        if self._last_sample is None:
            self._last_sample = (now, queries_total)
            return self._result(None, None, False, "collecting baseline")

        last_time, last_total = self._last_sample
        self._last_sample = (now, queries_total)

        elapsed_minutes = (now - last_time) / 60.0
        delta = queries_total - last_total

        if elapsed_minutes <= 0:
            return self._result(None, None, False, "collecting baseline")

        if delta < 0:
            # Pi-hole's counters reset (e.g. daily rollover) — the old
            # history no longer reflects a comparable baseline.
            self._rate_history.clear()
            return self._result(None, None, False, "counter reset")

        current_qpm = delta / elapsed_minutes

        if len(self._rate_history) < self.min_samples:
            self._rate_history.append(current_qpm)
            return self._result(round(current_qpm, 1), None, False, "collecting baseline")

        baseline_qpm = sum(self._rate_history) / len(self._rate_history)
        is_anomaly = current_qpm > max(baseline_qpm * self.multiplier, self.min_qpm)
        self._rate_history.append(current_qpm)

        reason = f"{current_qpm:.1f} qpm vs baseline {baseline_qpm:.1f} qpm" if is_anomaly else None
        return self._result(round(current_qpm, 1), round(baseline_qpm, 1), is_anomaly, reason)

    @staticmethod
    def _result(queries_per_min, baseline_qpm, is_anomaly, reason):
        return {
            "queries_per_min": queries_per_min,
            "baseline_qpm": baseline_qpm,
            "is_anomaly": is_anomaly,
            "reason": reason,
        }


def get_tracker():
    """
    Deliberately NOT scoped to flask.g (unlike the per-request PiholeClient)
    — this needs to survive across requests, so it lives on the app object
    itself, created once on first use.
    """
    if not hasattr(current_app, "_query_rate_tracker"):
        current_app._query_rate_tracker = QueryRateTracker(
            history_size=current_app.config["ANOMALY_HISTORY_SIZE"],
            multiplier=current_app.config["ANOMALY_MULTIPLIER"],
            min_qpm=current_app.config["ANOMALY_MIN_QPM"],
            min_samples=current_app.config["ANOMALY_MIN_SAMPLES"],
        )
    return current_app._query_rate_tracker

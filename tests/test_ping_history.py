from app.services.ping_history import PingHistoryTracker


def test_records_and_returns_growing_history():
    tracker = PingHistoryTracker(maxlen=5)

    assert tracker.record(12.34, 0.0) == {"rtt_avg_ms": [12.3], "packet_loss_percent": [0.0]}
    assert tracker.record(15.0, 20.0) == {
        "rtt_avg_ms": [12.3, 15.0],
        "packet_loss_percent": [0.0, 20.0],
    }


def test_drops_oldest_once_maxlen_exceeded():
    tracker = PingHistoryTracker(maxlen=3)
    for v in [1.0, 2.0, 3.0, 4.0]:
        result = tracker.record(v, 0.0)

    assert result["rtt_avg_ms"] == [2.0, 3.0, 4.0]


def test_non_numeric_value_is_recorded_as_a_gap_not_skipped():
    tracker = PingHistoryTracker(maxlen=3)
    tracker.record(1.0, 0.0)

    result = tracker.record(None, 100.0)

    assert result == {"rtt_avg_ms": [1.0, None], "packet_loss_percent": [0.0, 100.0]}

from app.services.disk_history import DiskHistoryTracker


def test_records_and_returns_growing_history():
    tracker = DiskHistoryTracker(maxlen=5)

    assert tracker.record(6.28) == [6.3]
    assert tracker.record(7.0) == [6.3, 7.0]


def test_drops_oldest_once_maxlen_exceeded():
    tracker = DiskHistoryTracker(maxlen=3)
    for v in [1.0, 2.0, 3.0, 4.0]:
        result = tracker.record(v)

    assert result == [2.0, 3.0, 4.0]


def test_non_numeric_value_is_a_no_op():
    tracker = DiskHistoryTracker(maxlen=3)
    tracker.record(1.0)

    assert tracker.record(None) == [1.0]

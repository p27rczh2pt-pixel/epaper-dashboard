from app.services.memory_history import MemoryHistoryTracker


def test_records_and_returns_growing_history():
    tracker = MemoryHistoryTracker(maxlen=5)

    assert tracker.record(3.14) == [3.1]
    assert tracker.record(4.0) == [3.1, 4.0]


def test_drops_oldest_once_maxlen_exceeded():
    tracker = MemoryHistoryTracker(maxlen=3)
    for v in [1.0, 2.0, 3.0, 4.0]:
        result = tracker.record(v)

    assert result == [2.0, 3.0, 4.0]


def test_non_numeric_value_is_a_no_op():
    tracker = MemoryHistoryTracker(maxlen=3)
    tracker.record(1.0)

    assert tracker.record(None) == [1.0]

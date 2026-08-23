from app.services.anomaly_service import QueryRateTracker


def test_first_call_just_seeds_baseline():
    tracker = QueryRateTracker()
    result = tracker.evaluate(1000, now=0)

    assert result["is_anomaly"] is False
    assert result["queries_per_min"] is None
    assert result["reason"] == "collecting baseline"


def test_reports_collecting_baseline_until_min_samples_reached():
    tracker = QueryRateTracker(min_samples=3)
    tracker.evaluate(1000, now=0)
    r1 = tracker.evaluate(1050, now=60)  # +50 queries in 1 min = 50 qpm
    r2 = tracker.evaluate(1100, now=120)

    assert r1["reason"] == "collecting baseline"
    assert r2["reason"] == "collecting baseline"
    assert r1["queries_per_min"] == 50.0


def test_steady_rate_is_not_flagged():
    tracker = QueryRateTracker(min_samples=2, multiplier=3.0, min_qpm=5.0)
    t = 0
    total = 1000
    for _ in range(6):
        t += 60
        total += 50  # steady 50 qpm throughout
        result = tracker.evaluate(total, now=t)

    assert result["is_anomaly"] is False
    assert result["baseline_qpm"] == 50.0


def test_sudden_spike_is_flagged():
    tracker = QueryRateTracker(min_samples=2, multiplier=3.0, min_qpm=5.0)
    t = 0
    total = 1000
    for _ in range(4):
        t += 60
        total += 50  # establish a ~50 qpm baseline
        tracker.evaluate(total, now=t)

    t += 60
    total += 2000  # huge spike: 2000 qpm vs ~50 baseline
    result = tracker.evaluate(total, now=t)

    assert result["is_anomaly"] is True
    assert "vs baseline" in result["reason"]


def test_min_qpm_floor_prevents_noise_flagging_near_zero_baseline():
    tracker = QueryRateTracker(min_samples=2, multiplier=3.0, min_qpm=5.0)
    t = 0
    total = 1000
    for _ in range(4):
        t += 60
        total += 1  # near-zero baseline (~1 qpm)
        tracker.evaluate(total, now=t)

    t += 60
    total += 4  # 4 qpm: >> 3x baseline but below the 5 qpm absolute floor
    result = tracker.evaluate(total, now=t)

    assert result["is_anomaly"] is False


def test_counter_reset_clears_history_instead_of_reporting_negative_rate():
    tracker = QueryRateTracker(min_samples=2)
    tracker.evaluate(1000, now=0)
    tracker.evaluate(1100, now=60)

    result = tracker.evaluate(10, now=120)  # counter rolled over / reset

    assert result["is_anomaly"] is False
    assert result["reason"] == "counter reset"
    assert len(tracker._rate_history) == 0


def test_none_total_is_a_no_op():
    tracker = QueryRateTracker()
    result = tracker.evaluate(None, now=0)

    assert result == {"queries_per_min": None, "baseline_qpm": None, "is_anomaly": False, "reason": None}

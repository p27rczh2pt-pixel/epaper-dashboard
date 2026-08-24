import copy

from display.render import HEIGHT, WIDTH, render_dashboard

FULL_DATA = {
    "pihole_stats": {
        "queries_total": 80486,
        "queries_blocked": 12742,
        "percent_blocked": 15.8,
        "unique_clients": 42,
        "top_blocked_domains": [
            {"domain": "scribe.logs.roku.com", "count": 7423},
            {"domain": "smetrics.aem.playstation.com", "count": 2973},
            {"domain": "mask.icloud.com", "count": 1248},
            {"domain": "device-metrics-us.amazon.com", "count": 294},
        ],
        "top_clients": [{"client": "192.168.1.50", "count": 43868}],
        "traffic_anomaly": {"queries_per_min": 12.0, "baseline_qpm": 10.0, "is_anomaly": False, "reason": None},
        "new_devices": {"new_count": 0, "new_devices": [], "known_count": 12, "baseline_seeded": False},
    },
    "pihole_health": {"cpu_load_percent": [1.1, 1.04, 0.1], "memory_percent_used": 3.1, "uptime_seconds": 1326137},
    "network_health": {
        "ping": {
            "host": "1.1.1.1",
            "packets_transmitted": 5,
            "packets_received": 5,
            "packet_loss_percent": 0.0,
            "rtt_avg_ms": 10.6,
        },
        "external_ip": {"ip": "1.2.3.4", "isp": "Example ISP", "city": "Nowhere", "region": "NA", "country": "US"},
        "time_sync": {"synced": True, "offset_ms": 1.3},
    },
    "system_health": {
        "cpu_temp_celsius": 20.0,
        "uptime_seconds": 405002,
        "disk": {"total_bytes": 1000, "used_bytes": 60, "free_bytes": 940, "percent_used": 6.0},
    },
}

DEGRADED_DATA = {
    "pihole_stats": {"error": "pihole_unreachable", "message": "401 Client Error"},
    "pihole_health": {"error": "pihole_unreachable", "message": "timed out"},
    "network_health": {
        "ping": {"error": "ping to 1.1.1.1 timed out"},
        "external_ip": {"error": "429 rate limited"},
        "time_sync": {"error": "timedatectl not found on this system"},
    },
    "system_health": {"cpu_temp_celsius": None, "uptime_seconds": None, "disk": None},
}


def test_render_dashboard_with_full_data():
    image = render_dashboard(FULL_DATA)
    assert image.size == (WIDTH, HEIGHT)
    assert image.mode == "1"


def test_render_dashboard_with_degraded_data_does_not_raise():
    image = render_dashboard(DEGRADED_DATA)
    assert image.size == (WIDTH, HEIGHT)


def test_render_dashboard_with_empty_data_does_not_raise():
    image = render_dashboard({})
    assert image.size == (WIDTH, HEIGHT)


def test_render_dashboard_with_traffic_anomaly_does_not_overflow():
    data = copy.deepcopy(FULL_DATA)
    data["pihole_stats"]["traffic_anomaly"] = {
        "queries_per_min": 842.3,
        "baseline_qpm": 41.2,
        "is_anomaly": True,
        "reason": "842.3 qpm vs baseline 41.2 qpm",
    }
    image = render_dashboard(data)
    assert image.size == (WIDTH, HEIGHT)


def test_render_dashboard_with_new_device_badge_does_not_overflow():
    data = copy.deepcopy(FULL_DATA)
    data["pihole_stats"]["new_devices"] = {
        "new_count": 2,
        "new_devices": [
            {"mac": "aa:aa:aa:aa:aa:aa", "vendor": "Roku, Inc", "ips": ["192.168.1.50"], "hostname": None},
            {"mac": "bb:bb:bb:bb:bb:bb", "vendor": None, "ips": ["192.168.1.51"], "hostname": None},
        ],
        "known_count": 14,
        "baseline_seeded": False,
    }
    image = render_dashboard(data)
    assert image.size == (WIDTH, HEIGHT)


def test_render_dashboard_with_time_not_synced_does_not_overflow():
    data = copy.deepcopy(FULL_DATA)
    data["network_health"]["time_sync"] = {"synced": False, "offset_ms": None}
    image = render_dashboard(data)
    assert image.size == (WIDTH, HEIGHT)


def test_render_dashboard_missing_new_devices_shows_unknown_not_crash():
    data = copy.deepcopy(FULL_DATA)
    del data["pihole_stats"]["new_devices"]
    image = render_dashboard(data)
    assert image.size == (WIDTH, HEIGHT)

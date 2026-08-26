from app import create_app
from app.services import system_service


def test_get_cpu_temp_celsius_parses_millidegrees(tmp_path):
    thermal_file = tmp_path / "temp"
    thermal_file.write_text("45231\n")

    assert system_service.get_cpu_temp_celsius(path=str(thermal_file)) == 45.2


def test_get_cpu_temp_celsius_missing_file_returns_none(tmp_path):
    missing = tmp_path / "does_not_exist"

    assert system_service.get_cpu_temp_celsius(path=str(missing)) is None


def test_get_uptime_seconds_parses_proc_uptime(tmp_path):
    uptime_file = tmp_path / "uptime"
    uptime_file.write_text("12345.67 54321.00\n")

    assert system_service.get_uptime_seconds(path=str(uptime_file)) == 12345.67


def test_get_disk_usage_returns_percent(tmp_path):
    usage = system_service.get_disk_usage(str(tmp_path))

    assert usage["total_bytes"] > 0
    assert 0 <= usage["percent_used"] <= 100


def test_get_disk_usage_bad_path_returns_none():
    assert system_service.get_disk_usage("/definitely/not/a/real/path") is None


def test_get_memory_percent_used_parses_meminfo(tmp_path):
    meminfo_file = tmp_path / "meminfo"
    meminfo_file.write_text("MemTotal:        8000000 kB\nMemAvailable:    6000000 kB\nMemFree:  100 kB\n")

    assert system_service.get_memory_percent_used(path=str(meminfo_file)) == 25.0


def test_get_memory_percent_used_missing_file_returns_none(tmp_path):
    missing = tmp_path / "does_not_exist"

    assert system_service.get_memory_percent_used(path=str(missing)) is None


def test_get_system_health_shape(tmp_path):
    # get_system_health() records disk usage into disk_history's tracker,
    # which is scoped to the Flask app object (see app/services/disk_history.py).
    with create_app().app_context():
        health = system_service.get_system_health(disk_path=str(tmp_path))

    assert set(health.keys()) == {"cpu_temp_celsius", "memory_percent_used", "uptime_seconds", "disk"}
    assert health["uptime_seconds"] is not None  # /proc/uptime exists on any Linux box
    assert health["disk"]["history"] == [health["disk"]["percent_used"]]

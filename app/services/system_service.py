import shutil

_THERMAL_ZONE_PATH = "/sys/class/thermal/thermal_zone0/temp"
_UPTIME_PATH = "/proc/uptime"
_MEMINFO_PATH = "/proc/meminfo"


def get_cpu_temp_celsius(path=_THERMAL_ZONE_PATH):
    try:
        with open(path) as f:
            millidegrees = int(f.read().strip())
        return round(millidegrees / 1000.0, 1)
    except (OSError, ValueError):
        return None


def get_uptime_seconds(path=_UPTIME_PATH):
    try:
        with open(path) as f:
            return float(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def get_memory_percent_used(path=_MEMINFO_PATH):
    try:
        values = {}
        with open(path) as f:
            for line in f:
                key, _, rest = line.partition(":")
                if key in ("MemTotal", "MemAvailable"):
                    values[key] = int(rest.strip().split()[0])  # kB

        total = values.get("MemTotal")
        available = values.get("MemAvailable")
        if not total or available is None:
            return None
        return round((total - available) / total * 100.0, 1)
    except (OSError, ValueError, IndexError):
        return None


def get_disk_usage(path="/"):
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    return {
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "percent_used": round(usage.used / usage.total * 100, 1) if usage.total else None,
    }


def get_system_health(disk_path="/"):
    return {
        "cpu_temp_celsius": get_cpu_temp_celsius(),
        "memory_percent_used": get_memory_percent_used(),
        "uptime_seconds": get_uptime_seconds(),
        "disk": get_disk_usage(disk_path),
    }
